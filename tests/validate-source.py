"""Validate NovaOS source inputs without building or modifying the host."""

from configparser import ConfigParser
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read(relative):
    data = (ROOT / relative).read_bytes()
    require(b"\r" not in data and data.endswith(b"\n"), f"Expected LF text: {relative}")
    return data.decode("utf-8")


def ini(relative):
    parser = ConfigParser(interpolation=None)
    parser.read_string(read(relative))
    return parser


def main():
    version = read("VERSION").strip()
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version), "Invalid VERSION")
    settings = dict(token.split("=", 1) for token in shlex.split(read("build/settings.env")))
    require(settings["SUITE"] == "trixie" and settings["ARCH"] == "amd64",
            "Unexpected Debian suite or architecture")

    packages = set()
    lists = sorted((ROOT / "packages").glob("*.list.chroot"))
    require(len(lists) == 4, "Expected four package lists")
    for path in lists:
        for package in read(path.relative_to(ROOT)).splitlines():
            require(re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", package), f"Bad package name: {package}")
            require(package not in packages, f"Duplicate package: {package}")
            packages.add(package)

    required = {
        "live-boot", "live-config-systemd", "user-setup", "systemd-sysv", "plasma-desktop",
        "kwin-wayland", "sddm", "firefox-esr", "konsole", "dolphin", "flatpak",
        "network-manager", "pipewire-audio", "wireplumber",
    }
    require(required <= packages, f"Missing packages: {sorted(required - packages)}")

    for asset in ("branding/novaos.svg", "branding/wallpaper.svg"):
        svg = ET.fromstring(read(asset))
        require(svg.tag == "{http://www.w3.org/2000/svg}svg" and "viewBox" in svg.attrib,
                f"Invalid SVG root: {asset}")

    metadata = json.loads(read("branding/wallpaper.json"))
    require(metadata["KPlugin"]["Id"] == "NovaOS", "Wallpaper ID differs from its install directory")
    theme = ini("desktop/kdeglobals")["General"]["ColorScheme"]
    require(theme == "NovaMidnight", "Nova Midnight must be the default color scheme")
    for name in ("NovaMidnight", "NovaDaybreak"):
        palette = ini(f"desktop/{name}.colors")
        require(palette["General"]["ColorScheme"] == name, f"Invalid scheme ID: {name}")
        for group in ("Window", "View", "Button", "Selection", "Tooltip", "Complementary", "Header"):
            for key, value in palette[f"Colors:{group}"].items():
                channels = value.split(",")
                require(len(channels) == 3 and all(ch.isdecimal() and 0 <= int(ch) <= 255 for ch in channels),
                        f"Invalid RGB color: {name}/{group}/{key}")

    require(ini("apps/mimeapps.list")["Default Applications"]["text/html"] == "firefox-esr.desktop;",
            "Firefox ESR association missing")
    grub = read("config/bootloaders/grub-pc/grub.cfg.in")
    expected = {"NOVA_VERSION", "KERNEL_LIVE", "INITRD_LIVE", "APPEND_LIVE",
                "ENABLE_VERIFY_CHECKSUMS", "APPEND_VERIFY_CHECKSUMS"}
    require(set(re.findall(r"@([A-Z_]+)@", grub)) == expected, "Unexpected GRUB template tokens")

    shell_files = [
        "scripts/build-iso.sh",
        "tests/verify-iso.sh",
        "config/hooks/live/0900-nova-verify.hook.chroot",
        "config/includes.chroot/usr/lib/live/config/0086-nova-sddm",
    ]
    shell = shutil.which("sh")
    for path in shell_files:
        require(read(path).startswith("#!/bin/sh\n"), f"Unexpected interpreter: {path}")
        if shell:
            subprocess.run([shell, "-n", path], cwd=ROOT, check=True)

    if not shell:
        print("POSIX shell unavailable. Shell syntax checks run in GitHub Actions.")
    print(f"NovaOS {version} source validated ({len(packages)} explicitly selected packages).")


if __name__ == "__main__":
    main()
