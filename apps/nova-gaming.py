#!/usr/bin/python3
"""Read local game libraries and run opt-in gaming actions as the desktop user."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote
from uuid import uuid4


PROFILES = {"balanced", "turbo", "gaming", "eco", "ultra-lite"}
FLATPAKS = {
    "steam": "com.valvesoftware.Steam",
    "bottles": "com.usebottles.bottles",
    "lutris": "net.lutris.Lutris",
    "heroic": "com.heroicgameslauncher.hgl",
    "minecraft": "org.prismlauncher.PrismLauncher",
    "emulation": "org.libretro.RetroArch",
    "development": "org.godotengine.Godot",
    "recording": "com.obsproject.Studio",
    "flatpak-overlay": "org.freedesktop.Platform.VulkanLayer.MangoHud",
    "flatpak-gamescope": "org.freedesktop.Platform.VulkanLayer.gamescope",
}
APT = {
    "wine": ["wine", "wine64"],
    "gamemode": ["gamemode"],
    "overlay": ["mangohud"],
    "gamescope": ["gamescope"],
    "vulkan": ["vulkan-tools"],
    "nvidia-detect": ["nvidia-detect"],
    "nvidia-driver": ["nvidia-driver"],
    "controller": ["joystick"],
    "native-steam": ["steam-installer"],
}
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "nova-gaming"
STATE = DATA / "library.json"
KEYSYM = re.compile(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+){0,3}")
VDF_TOKEN = re.compile(r'"((?:\\.|[^"\\])*)"|([{}])|//[^\n]*')


def parse_vdf(text):
    root = {}
    stack = [root]
    key = None
    for token in VDF_TOKEN.finditer(text):
        value, brace = token.groups()
        if brace == "{":
            if key is None:
                raise ValueError("Unexpected VDF object")
            child = {}
            stack[-1][key.casefold()] = child
            stack.append(child)
            key = None
        elif brace == "}":
            if len(stack) <= 1 or key is not None:
                raise ValueError("Unexpected VDF closing brace")
            stack.pop()
        elif value is not None:
            item = re.sub(r'\\(["\\])', r'\1', value)
            if key is None:
                key = item
            else:
                stack[-1][key.casefold()] = item
                key = None
    if len(stack) != 1 or key is not None:
        raise ValueError("Incomplete VDF data")
    return root


def read_vdf(path):
    try:
        return parse_vdf(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, ValueError):
        return {}


def number(value):
    return int(value) if isinstance(value, str) and value.isascii() and value.isdecimal() else 0


def steam_games(roots):
    games = {}
    for root, client in roots:
        if not root.is_dir():
            continue
        libraries = {root}
        folder_data = read_vdf(root / "steamapps/libraryfolders.vdf").get("libraryfolders", {})
        if isinstance(folder_data, dict):
            for index, entry in folder_data.items():
                location = entry.get("path") if isinstance(entry, dict) else entry
                if index.isdecimal() and isinstance(location, str) and Path(location).is_absolute():
                    libraries.add(Path(location))
        playtime = {}
        for userdata in root.glob("userdata/*/config/localconfig.vdf"):
            profiles = read_vdf(userdata).get("userlocalconfigstore", {})
            for key in ("software", "valve", "steam", "apps"):
                profiles = profiles.get(key, {}) if isinstance(profiles, dict) else {}
            if isinstance(profiles, dict):
                for app_id, metadata in profiles.items():
                    if isinstance(metadata, dict):
                        playtime[app_id] = max(playtime.get(app_id, 0), number(metadata.get("playtime")))
        for library in sorted(libraries):
            for manifest in sorted((library / "steamapps").glob("appmanifest_*.acf")):
                game = read_vdf(manifest).get("appstate")
                if not isinstance(game, dict):
                    continue
                app_id, directory = game.get("appid", ""), game.get("installdir", "")
                if (not number(app_id) or not isinstance(directory, str)
                        or directory in {"", ".", ".."} or Path(directory).name != directory):
                    continue
                if re.match(r"^(?:SteamLinuxRuntime(?:_|$)|Steamworks Shared$|Proton(?: [0-9]| Experimental$| Hotfix$))",
                            directory, re.IGNORECASE):
                    continue
                installed = library / "steamapps/common" / directory
                if not number(game.get("stateflags")) & 4 or not installed.is_dir():
                    continue
                artwork = root / "appcache/librarycache"
                candidates = [artwork / f"{app_id}_library_600x900.jpg",
                              artwork / app_id / "library_600x900.jpg",
                              artwork / f"{app_id}_header.jpg"]
                art = next((file.resolve().as_uri() for file in candidates if file.is_file()), "")
                games.setdefault(f"steam:{app_id}", {
                    "id": f"steam:{app_id}", "name": str(game.get("name", directory)),
                    "kind": "steam", "client": client, "path": str(installed),
                    "art": art, "bytes": number(game.get("sizeondisk")),
                    "last": number(game.get("lastplayed")), "minutes": playtime.get(app_id),
                })
    return list(games.values())


def state():
    if not STATE.exists():
        return {"games": {}, "settings": {}}
    return json.loads(STATE.read_text(encoding="utf-8"))


@contextmanager
def edit_state():
    import fcntl

    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (DATA / "library.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        library = state()
        yield library
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA, delete=False) as output:
            filename = output.name
            json.dump(library, output)
        Path(filename).replace(STATE)


def roots():
    home = Path.home()
    return [(home / ".local/share/Steam", "native"),
            (home / ".steam/steam", "native"),
            (home / ".var/app/com.valvesoftware.Steam/.local/share/Steam", "flatpak"),
            (home / ".var/app/com.valvesoftware.Steam/.steam/steam", "flatpak")]


def inventory():
    library = state()
    games = steam_games(roots()) + list(library["games"].values())
    for game in games:
        game.update(library["settings"].get(game["id"], {}))
        if game["kind"] == "steam":
            game["protondb"] = "https://www.protondb.com/app/" + game["id"].split(":")[1]
    return sorted(games, key=lambda game: (not game.get("favorite", False),
                                          -game.get("last", 0), game["name"].casefold()))


def detach(*argv, cwd=None):
    subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def settings_for(payload):
    profile = payload.get("profile", "gaming")
    hotkey = payload.get("hotkey", "Super_L+g")
    if profile not in PROFILES or not isinstance(hotkey, str) or not KEYSYM.fullmatch(hotkey):
        raise ValueError("Invalid workload profile or MangoHud shortcut.")
    return {"profile": profile, "hotkey": hotkey, **{
        key: payload.get(key) is True for key in ("favorite", "overlay", "effects", "gamescope")
    }}


def game_command(game):
    executable = Path(game["path"]).expanduser()
    if not executable.is_file():
        raise ValueError("The selected game executable is missing.")
    arguments = game.get("args", [])
    if game["kind"] == "wine":
        runtime = game.get("runtime") or "wine"
        if not shutil.which(runtime):
            raise ValueError("The selected Wine runtime is unavailable.")
        prefix = DATA / "wine" / game["id"]
        prefix.mkdir(parents=True, exist_ok=True)
        return ["env", f"WINEPREFIX={prefix}", runtime, str(executable), *arguments]
    if not os.access(executable, os.X_OK):
        raise ValueError("The selected native game file is not executable.")
    return [str(executable), *arguments]


def managed(game_id, argv):
    settings = settings_for(state()["settings"].get(game_id, {}))
    if settings["overlay"]:
        if not shutil.which("mangohud"):
            raise ValueError("Install MangoHud or disable the overlay for this game.")
        DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
        config = DATA / f"overlay-{game_id.replace(':', '-')}.conf"
        # Use a Nova-owned file, avoiding changes to the user's global MangoHud configuration.
        default_config = Path("/usr/share/novaos/mangohud.conf").read_text(encoding="utf-8")
        config.write_text(default_config.replace("Super_L+g", settings["hotkey"]), encoding="utf-8")
        argv = ["env", f"MANGOHUD_CONFIGFILE={config}", "mangohud", *argv]
    if settings["gamescope"]:
        if not shutil.which("gamescope"):
            raise ValueError("Install Gamescope or disable it for this game.")
        argv = ["gamescope", "--", *argv]
    return ["nova-run", "--profile", settings["profile"], "--game", "--", *argv]


@contextmanager
def lowered_effects(enabled):
    if not enabled or os.environ.get("XDG_SESSION_TYPE") != "wayland":
        yield
        return
    import fcntl

    config = CONFIG / "novaos"
    config.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (config / "profile.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        snapshot = subprocess.check_output(["nova-appearance", "snapshot"], text=True).split()
        try:
            subprocess.run(["nova-appearance", "ultra-lite"], check=True, stdout=subprocess.DEVNULL)
            yield
        finally:
            subprocess.run(["nova-appearance", "restore", *snapshot],
                           check=True, stdout=subprocess.DEVNULL)


def run_session(game_id, argv):
    settings = settings_for(state()["settings"].get(game_id, {}))
    command = managed(game_id, argv)
    started = int(time.time())
    previous = time.monotonic()
    with lowered_effects(settings["effects"]):
        with subprocess.Popen(command) as launch:
            status = launch.wait()
            scope = f"nova-game-{launch.pid}.scope"
            # A game launcher can exit while its descendants still own the scope.
            while subprocess.run(["systemctl", "--user", "is-active", "--quiet", scope],
                                 check=False).returncode == 0:
                time.sleep(1)
    elapsed = int(time.monotonic() - previous)
    if not game_id.startswith("steam:") and (status == 0 or elapsed >= 5):
        with edit_state() as library:
            if game_id in library["games"]:
                record = library["games"][game_id]
                record["seconds"] = record.get("seconds", 0) + elapsed
                record["last"] = started
    return status


def gpu_recommendations():
    recommendations = []
    vendors = {"0x1002": "AMD: retain the kernel driver and Mesa RADV.",
               "0x8086": "Intel: retain the kernel driver and Mesa ANV.",
               "0x10de": "NVIDIA: use nvidia-detect before selecting a driver from signed Debian repositories."}
    for node in sorted(Path("/sys/class/drm").glob("card*/device/vendor")):
        try:
            vendor = node.read_text().strip()
        except OSError:
            continue
        driver = node.parent / "driver"
        module = driver.resolve().name if driver.is_symlink() else "no bound driver"
        recommendations.append(f"{node.parents[1].name} ({module}): {vendors.get(vendor, 'No driver recommendation.')}")
    return recommendations or ["No supported GPU was identified. No driver installation recommended."]


def install(tool):
    if tool not in FLATPAKS and tool not in APT:
        raise ValueError("Unknown setup option.")
    if tool in FLATPAKS:
        print(f"Install {FLATPAKS[tool]} and its required Flatpak runtime from Flathub?")
    else:
        print("Review package changes for " + ", ".join(APT[tool]))
    if input("Continue [y/N]? ").strip().lower() != "y":
        return 0
    if tool in FLATPAKS:
        subprocess.run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
                        "https://dl.flathub.org/repo/flathub.flatpakrepo"], check=True)
        return subprocess.run(["flatpak", "install", "--user", "flathub", FLATPAKS[tool]]).returncode
    if tool == "nvidia-driver":
        if not any("NVIDIA:" in gpu for gpu in gpu_recommendations()) or not shutil.which("nvidia-detect"):
            raise ValueError("An NVIDIA GPU and the Debian nvidia-detect tool are required.")
        result = subprocess.run(["nvidia-detect"], capture_output=True, text=True, check=True)
        print(result.stdout)
        if not re.search(r"^\s*nvidia-driver\s*$", result.stdout, re.MULTILINE):
            raise ValueError("Debian did not recommend nvidia-driver for this hardware.")
        if input("Install the recommended Debian driver [y/N]? ").strip().lower() != "y":
            return 0
    return subprocess.run(["sudo", "apt-get", "--no-install-recommends", "--no-remove",
                           "-o", "APT::Get::AllowUnauthenticated=false",
                           "-o", "Acquire::AllowInsecureRepositories=false", "install", *APT[tool]]).returncode


def flatpak_client(ref):
    if subprocess.run(["flatpak", "info", ref], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        raise ValueError(f"{ref} is unavailable. Install it from Gaming Setup.")
    return ["flatpak", "run", ref]


def ui(action, payload):
    if action == "library":
        return inventory()
    if action == "add":
        path = Path(payload["path"]).expanduser()
        name = payload["name"].strip()
        kind = payload.get("kind", "native")
        args = json.loads(payload.get("args") or "[]")
        if not name or not path.is_absolute() or not path.is_file() or kind not in {"native", "wine"}:
            raise ValueError("Enter a title and an existing absolute executable path.")
        if not isinstance(args, list) or not all(isinstance(arg, str) and "\0" not in arg for arg in args):
            raise ValueError("Launch arguments must be a JSON array of strings.")
        game_id = payload.get("id") or str(uuid4())
        picture = Path(payload.get("art") or ".").expanduser()
        art = picture.resolve().as_uri() if picture.is_file() else ""
        with edit_state() as library:
            if payload.get("id") and game_id not in library["games"]:
                raise ValueError("Only manually added games can be edited here.")
            record = library["games"].setdefault(game_id, {})
            record.update({"id": game_id, "name": name, "kind": kind,
                           "path": str(path), "runtime": payload.get("runtime", ""),
                           "args": args, "art": art})
        return inventory()
    if action == "setup" and payload in {*FLATPAKS, *APT}:
        if payload in {"nvidia-detect", "nvidia-driver"} and not any(
                "NVIDIA:" in gpu for gpu in gpu_recommendations()):
            raise ValueError("No NVIDIA graphics hardware was detected.")
        detach("konsole", "--hold", "-e", "/usr/bin/nova-gaming", "install", payload)
        return None
    if action == "graphics":
        return gpu_recommendations()
    if action == "shortcut" and payload in {"spectacle", "controller", "obs"}:
        if payload == "spectacle":
            detach("spectacle")
        elif payload == "controller":
            detach("systemsettings", "kcm_gamecontroller")
        else:
            detach(*flatpak_client(FLATPAKS["recording"]))
        return None

    game_id = payload.get("id") if isinstance(payload, dict) else payload
    game = next((item for item in inventory() if item["id"] == game_id), None)
    if game is None:
        raise ValueError("Game not found. Refresh the library.")
    if action == "save":
        with edit_state() as library:
            library["settings"][game_id] = settings_for(payload)
        return inventory()
    if action == "launch":
        if game["kind"] == "steam":
            app_id = game_id.split(":")[1]
            client = flatpak_client(FLATPAKS["steam"]) if game["client"] == "flatpak" else ["steam"]
            detach(*client, f"steam://rungameid/{app_id}")
        else:
            detach("konsole", "--hold", "-e", "/usr/bin/nova-gaming", "session", game_id,
                   cwd=Path(game["path"]).parent)
    elif action == "storage":
        location = Path(game["path"])
        disk = shutil.disk_usage(location if location.is_dir() else location.parent)
        return [str(location), f"Volume free: {disk.free / 2**30:.1f} GiB",
                f"Steam installed size: {game['bytes'] / 2**30:.2f} GiB" if game.get("bytes") else ""]
    elif action == "folder":
        location = Path(game["path"])
        detach("dolphin", str(location if location.is_dir() else location.parent))
    elif action == "remove" and game["kind"] != "steam":
        with edit_state() as library:
            library["games"].pop(game_id, None)
            library["settings"].pop(game_id, None)
        return inventory()
    else:
        raise ValueError("Unknown gaming action.")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("ui", "install", "session", "steam"))
    parser.add_argument("value", nargs="?")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as the desktop user.")
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGHUP, interrupt)
    try:
        if args.action == "ui":
            payload = json.loads(unquote(args.arguments[0])) if args.arguments else None
            print(json.dumps(ui(args.value, payload)))
        elif args.action == "install":
            return install(args.value)
        elif args.action == "steam" and args.value and number(args.value) and args.arguments:
            command = args.arguments[1:] if args.arguments[0] == "--" else args.arguments
            if not command:
                parser.error("Missing Steam launch command.")
            return run_session("steam:" + args.value, command)
        elif args.action == "session":
            game = state()["games"][args.value]
            return run_session(args.value, game_command(game))
        else:
            parser.error("Missing game identifier or command.")
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


def interrupt(_signum, _frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    sys.exit(main())
