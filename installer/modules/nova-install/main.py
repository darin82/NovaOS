"""Apply the selected profile without installing anything on the live system."""
import os
from pathlib import Path
import subprocess

import libcalamares

BASE_REMOVALS = ("calamares", "calamares-settings-debian", "live-boot", "live-config", "live-config-systemd")
MINIMAL = {
    "media": ("haruna", "mpv", "mpv-mpris", "ffmpeg"),
    "notes": ("kate",), "calculator": ("kcalc",), "capture": ("kde-spectacle",),
}
SUGGESTED = {
    "gaming": {"gamemode", "mangohud", "vulkan-tools"},
    "developer": {"git", "build-essential", "python3-venv"},
}
APT = ["apt-get", "-o", "APT::Get::AllowUnauthenticated=false",
       "-o", "Acquire::AllowInsecureRepositories=false", "--no-install-recommends"]


def run():
    root = Path(libcalamares.globalstorage.value("rootMountPoint")).resolve()
    if root == Path("/") or not root.is_mount() or not (root / "usr/lib/novaos/os-release").is_file():
        return ("Invalid target", "Installer package changes were refused.")
    profile = libcalamares.globalstorage.value("packagechooser_profile") or "standard"
    extras = set((libcalamares.globalstorage.value("packagechooser_extras") or "").split(","))
    if profile not in {"minimal", "standard", "gaming", "developer"}:
        return ("Invalid install profile", "Please select a valid install profile.")
    removals = list(BASE_REMOVALS)
    if profile == "minimal":
        for key, packages in MINIMAL.items():
            if key not in extras:
                removals.extend(packages)
    log = root / "var/log/nova-install-profile.log"
    with log.open("w", encoding="utf-8") as output:
        output.write(f"Profile: {profile}\n")
        output.flush()
        plan = subprocess.run(["chroot", str(root), *APT, "-s", "purge", *removals],
                              capture_output=True, text=True, timeout=90)
        planned = {line.split()[1].split(":")[0] for line in plan.stdout.splitlines()
                   if line.startswith(("Remv ", "Purg "))}
        if plan.returncode or not planned <= set(removals):
            output.write(plan.stdout + plan.stderr)
            return ("Cannot apply installation profile", "APT did not produce a safe removal plan.")
        environment = os.environ | {"DEBIAN_FRONTEND": "noninteractive"}
        result = subprocess.run(["chroot", str(root), *APT, "-y", "purge", *removals],
                                stdout=output, stderr=subprocess.STDOUT, env=environment)
        if result.returncode:
            return ("Cannot apply installation profile", "See /var/log/nova-install-profile.log.")
        optional = SUGGESTED.get(profile, set()) | (extras & {"git", "gamemode", "mangohud"})
        if optional:
            try:
                refresh = subprocess.run(["chroot", str(root), *APT, "-o", "APT::Update::Error-Mode=any", "update"],
                                         stdout=output, stderr=subprocess.STDOUT, timeout=120)
                if refresh.returncode == 0:
                    extra_result = subprocess.run(
                        ["chroot", str(root), *APT, "--no-remove", "-y", "install", *sorted(optional)],
                        stdout=output, stderr=subprocess.STDOUT, env=environment,
                    )
                    if extra_result.returncode:
                        output.write("Optional package installation failed. Review this log after boot.\n")
                else:
                    output.write("Optional packages skipped because signed package lists were unavailable.\n")
            except subprocess.TimeoutExpired:
                output.write("Optional package setup timed out. Review APT state after boot.\n")
    for relative in ("usr/share/applications/org.novaos.Install.desktop", "etc/xdg/autostart/nova-live-installer.desktop",
                     "usr/share/novaos/desktop/Install NovaOS.desktop", "etc/sddm.conf.d/90-nova-live.conf"):
        (root / relative).unlink(missing_ok=True)
    if profile == "minimal" and "media" not in extras:
        (root / "usr/share/applications/org.novaos.Music.desktop").unlink(missing_ok=True)
    return None
