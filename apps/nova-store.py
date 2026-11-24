#!/usr/bin/python3
"""On-demand trusted application catalog and package transaction frontend."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


CATALOG = Path("/usr/share/novaos/store-catalog.json")
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "nova-store"
MANAGED = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "nova-store"
FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
PAGE = 12
APT = ["sudo", "apt-get", "--no-install-recommends",
       "-o", "APT::Get::AllowUnauthenticated=false",
       "-o", "Acquire::AllowInsecureRepositories=false",
       "-o", "Acquire::AllowDowngradeToInsecureRepositories=false"]


def command(*args, timeout=12):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def catalog():
    return [dict(zip(("name", "category", "source", "id", "description"), row))
            for row in json.loads(CATALOG.read_text(encoding="utf-8"))]


def apt_tracks(ref):
    return MANAGED / ref


def installed_flatpaks():
    result = command("flatpak", "--user", "list", "--app", "--columns=application,name,origin")
    if result.returncode:
        return []
    entries = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) == 3:
            app, name, origin = fields
            if re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+", app):
                entries.append({"id": app, "name": name, "origin": origin, "source": "flatpak",
                                "category": "Installed", "description": ""})
    return entries


def apt_installed(ref):
    result = command("dpkg-query", "-W", "-f=${db:Status-Status}", ref)
    return result.stdout == "installed"


def browse(payload):
    source = payload.get("source", "All")
    category = payload.get("category", "All")
    query = str(payload.get("query", "")).casefold()
    page = max(0, int(payload.get("page", 0)))
    entries = catalog()
    if payload.get("installed"):
        entries = installed_flatpaks() + [
            app for app in entries if app["source"] == "apt" and apt_installed(app["id"])
        ]
    entries = [app for app in entries if (source == "All" or app["source"] == source)
               and (category == "All" or app["category"] == category)
               and query in " ".join((app["name"], app["id"], app["description"])).casefold()]
    return {"rows": entries[page * PAGE:(page + 1) * PAGE], "more": len(entries) > (page + 1) * PAGE}


def lookup(source, ref):
    for item in catalog():
        if (item["source"], item["id"]) == (source, ref):
            return item
    if source == "flatpak":
        for item in installed_flatpaks():
            if item["id"] == ref:
                return item
    raise ValueError("Select a catalog entry or an installed per-user Flatpak.")


def flathub_metadata(ref):
    CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    local = CACHE / (ref + ".json")
    if local.is_file() and time.time() - local.stat().st_mtime < 86_400:
        return json.loads(local.read_text(encoding="utf-8"))
    request = Request(f"https://flathub.org/api/v2/appstream/{ref}",
                      headers={"User-Agent": "NovaOS Store"})
    with urlopen(request, timeout=5) as response:
        data = json.loads(response.read(800_000))
    local.write_text(json.dumps(data), encoding="utf-8")
    return data


def details(source, ref):
    item = lookup(source, ref).copy()
    item["screenshot"] = ""
    item["caption"] = ""
    if source == "apt":
        item["installed"] = apt_installed(ref)
        item["removable"] = item["installed"] and apt_tracks(ref).is_file()
        result = command("apt-cache", "show", "--no-all-versions", ref)
        info = result.stdout.split("\n\n", 1)[0]
        item["size"] = "\n".join(line for line in info.splitlines()
                                 if line.startswith(("Installed-Size:", "Size:")))
        paragraphs = re.search(r"^Description(?:-[a-z]+)?: (.*(?:\n .*)*)", info, re.M)
        if paragraphs:
            item["description"] = paragraphs.group(1)
        item["details"] = "APT packages use system permissions. Installed-Size is in KiB and Size is in bytes."
        return item

    item["installed"] = command("flatpak", "--user", "info", ref).returncode == 0
    item["removable"] = item["installed"]
    if item["installed"]:
        item["size"] = command("flatpak", "--user", "info", "--show-size", ref).stdout.strip()
        item["details"] = command("flatpak", "--user", "info", "--show-permissions", ref).stdout.strip()
    else:
        item["details"] = "Full size and sandbox permissions appear in the Flatpak installation review."
        local = command("flatpak", "--user", "remote-info", "flathub", ref, timeout=6)
        if local.returncode == 0:
            item["size"] = "\n".join(line.strip() for line in local.stdout.splitlines()
                                     if "Download:" in line or "Installed:" in line)
    if any(app["id"] == ref for app in catalog()):
        try:
            metadata = flathub_metadata(ref)
            for shot in metadata.get("screenshots", []):
                images = sorted(shot.get("sizes", []),
                                key=lambda image: abs(int(image.get("width", 0)) - 640))
                for image in images:
                    url = image.get("src", "")
                    parts = urlsplit(url)
                    if parts.scheme == "https" and (parts.hostname or "").endswith(".flathub.org"):
                        item["screenshot"] = url
                        item["caption"] = shot.get("caption") or ""
                        break
                if item["screenshot"]:
                    break
        except (OSError, ValueError, AttributeError):
            pass
    return item


def open_terminal(*args):
    subprocess.Popen(["konsole", "--hold", "-e", "/usr/bin/nova-store", "transaction", *args],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def refresh_flathub():
    subprocess.run(["flatpak", "--user", "remote-add", "--if-not-exists", "flathub", FLATHUB],
                   check=True)


def transaction(action, source="", ref=""):
    if action in {"add-repo", "enable-repo", "disable-repo", "updates", "apply-updates"}:
        if action == "updates":
            checks = [["apt-get", "--simulate", "upgrade"],
                      ["flatpak", "--user", "remote-ls", "--updates", "--app"]]
            return max(subprocess.run(args).returncode for args in checks)
        if input("Apply this repository or update action [y/N]? ").lower() != "y":
            return 0
        if action == "apply-updates":
            apt = subprocess.run(["/usr/bin/nova-update", "apply"]).returncode
            flatpak = subprocess.run(["flatpak", "--user", "update"]).returncode
            return max(apt, flatpak)
        if action == "add-repo":
            refresh_flathub()
            return 0
        return subprocess.run(["flatpak", "--user", "remote-modify",
                               "--enable" if action == "enable-repo" else "--disable",
                               "flathub"]).returncode
    lookup(source, ref)
    if action not in {"install", "remove"}:
        raise ValueError("Unknown package action.")
    if action == "remove" and source == "apt" and not apt_tracks(ref).is_file():
        raise ValueError("This system package was not installed by Nova Store.")
    if input(f"{action.capitalize()} {ref} using {source.upper()} [y/N]? ").lower() != "y":
        return 0
    if source == "flatpak":
        if action == "install":
            refresh_flathub()
            args = ["flatpak", "--user", "install", "flathub", ref]
        else:
            args = ["flatpak", "--user", "uninstall", ref]
        return subprocess.run(args).returncode
    if action == "remove":
        plan = command("apt-get", "--simulate", "remove", ref)
        removals = [line.split()[1].split(":")[0] for line in plan.stdout.splitlines()
                    if line.startswith("Remv ")]
        if plan.returncode or removals != [ref]:
            raise ValueError("APT did not produce a removal plan limited to this package.")
        # APT shows the live transaction and asks for confirmation under its own lock.
        status = subprocess.run([*APT, "remove", ref]).returncode
        if status == 0 and not apt_installed(ref):
            apt_tracks(ref).unlink(missing_ok=True)
        return status
    already = apt_installed(ref)
    status = subprocess.run([*APT, "--no-remove", "install", ref]).returncode
    if status == 0 and not already and apt_installed(ref):
        MANAGED.mkdir(mode=0o700, parents=True, exist_ok=True)
        apt_tracks(ref).touch()
    return status


def ui(action, data):
    if action == "optional-ai":
        launcher = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications/org.novaos.AI.desktop"
        if data == "enable":
            launcher.parent.mkdir(parents=True, exist_ok=True)
            launcher.write_bytes(Path("/usr/lib/novaos/ai/org.novaos.AI.desktop").read_bytes())
        elif data == "disable":
            runtime = os.environ.get("XDG_RUNTIME_DIR")
            if runtime:
                for marker in Path(runtime).glob("nova-ai.*/window.pid"):
                    try:
                        pid = int(marker.read_text())
                        args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
                        if b"/usr/lib/novaos/ai/nova-ai" in args:
                            raise ValueError("Close the open Nova AI window before disabling it.")
                    except FileNotFoundError:
                        continue
            launcher.unlink(missing_ok=True)
        elif data == "open" and launcher.is_file():
            subprocess.Popen(["/usr/lib/novaos/ai/nova-ai"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        elif data != "status":
            raise ValueError("Enable Nova AI before opening it.")
        return launcher.is_file()
    if action == "browse":
        return browse(data)
    if action == "details":
        return details(data["source"], data["id"])
    if action == "repos":
        return {"apt": command("apt-cache", "policy").stdout,
                "flatpak": command("flatpak", "--user", "remotes", "--show-details").stdout}
    if action == "transaction":
        operation = data["operation"]
        source, ref = data.get("source", ""), data.get("id", "")
        if operation in {"install", "remove"}:
            lookup(source, ref)
        elif operation not in {"add-repo", "enable-repo", "disable-repo", "updates", "apply-updates"}:
            raise ValueError("Unknown store action.")
        open_terminal(operation, source, ref)
        return None
    raise ValueError("Unknown store action.")


def main():
    if os.geteuid() == 0:
        raise SystemExit("Run Nova Store as the desktop user.")
    try:
        if len(sys.argv) == 1:
            os.environ["QT_QUICK_CONTROLS_STYLE"] = "org.kde.desktop"
            os.execvp("qml6", ["qml6", "/usr/lib/novaos/Store.qml"])
        if sys.argv[1] == "transaction":
            return transaction(*sys.argv[2:])
        action, encoded = sys.argv[1:]
        print(json.dumps(ui(action, json.loads(unquote(encoded)))))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, EOFError) as error:
        raise SystemExit(str(error))
    return 0


if __name__ == "__main__":
    sys.exit(main())
