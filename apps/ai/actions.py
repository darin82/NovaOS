"""Fixed action registry. Provider output never reaches this module."""
import os
from pathlib import Path
import shutil
import subprocess


ACTIONS = {
    "steam": ("Open Steam", ""),
    "gaming": ("Set the Nova workload profile to Gaming", ""),
    "wallpaper": ("Apply the selected local wallpaper", "Absolute image path"),
    "file": ("Search one chosen directory for a filename", "Directory | name fragment"),
    "ram": ("Read memory usage from procfs", ""),
    "apps": ("Find installed application desktop IDs", "Name fragment"),
    "disk": ("Check available storage on the root filesystem", ""),
    "volume": ("Set the default audio output volume", "Percent (0–100)"),
    "brightness": ("Set screen brightness if the installed driver permits it", "Percent (1–100)"),
    "settings": ("Open a Nova Settings module", "display, sound, network, accessibility"),
    "network": ("Inspect local networking without contacting the internet", ""),
}
MODULES = {
    "display": "kcm_kscreen", "sound": "kcm_pulseaudio",
    "network": "kcm_networkmanagement", "accessibility": "kcm_access",
}


def preview(action, argument):
    argument = str(argument).strip()
    if action not in ACTIONS or len(argument) > 5000 or "\0" in argument:
        raise ValueError("That action or argument is unavailable.")
    if action in {"brightness", "volume"}:
        if not argument.isascii() or not argument.isdecimal():
            raise ValueError("Enter a percentage.")
        value = int(argument)
        if not (1 if action == "brightness" else 0) <= value <= 100:
            raise ValueError("Percentage is outside the supported range.")
    elif action == "wallpaper":
        path = Path(argument).expanduser()
        if not path.is_absolute() or not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Choose an existing PNG, JPEG or WebP file.")
        argument = str(path.resolve())
    elif action == "file":
        folder, separator, needle = argument.partition("|")
        if not separator or not needle.strip() or not Path(folder.strip()).expanduser().is_dir():
            raise ValueError("Use an existing directory followed by | and a name fragment.")
    elif action == "settings" and argument not in MODULES:
        raise ValueError("Select display, sound, network or accessibility.")
    return argument


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError("The system tool could not complete that action.")
    return result.stdout.strip() or "Completed."


def launch(*args):
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return "Opened."


def execute(action, argument):
    argument = preview(action, argument)
    if action == "steam":
        if shutil.which("steam"):
            return launch("steam")
        command("flatpak", "info", "com.valvesoftware.Steam")
        return launch("flatpak", "run", "com.valvesoftware.Steam")
    if action == "gaming":
        return command("nova-profile", "set", "gaming")
    if action == "wallpaper":
        return command("plasma-apply-wallpaperimage", argument)
    if action == "ram":
        values = {row.split(":")[0]: int(row.split()[1]) for row in Path("/proc/meminfo").read_text().splitlines()}
        return f"{(values['MemTotal']-values['MemAvailable']) // 1024} MiB used of {values['MemTotal'] // 1024} MiB."
    if action == "disk":
        return f"{shutil.disk_usage('/').free / 2**30:.1f} GiB free on /."
    if action == "volume":
        return command("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{int(argument)}%")
    if action == "brightness":
        if not shutil.which("brightnessctl"):
            raise ValueError("Brightness control requires the optional brightnessctl utility and supported hardware.")
        return command("brightnessctl", "set", f"{int(argument)}%")
    if action == "settings":
        return launch("systemsettings", MODULES[argument])
    if action == "network":
        return command("nmcli", "device", "status") + "\n\n" + command("ip", "-brief", "address")
    if action == "file":
        folder, _, needle = argument.partition("|")
        matches = []
        with os.scandir(Path(folder.strip()).expanduser()) as entries:
            for index, entry in enumerate(entries):
                if index >= 2000 or len(matches) >= 40:
                    break
                if needle.strip().casefold() in entry.name.casefold():
                    matches.append(entry.path)
        return "\n".join(matches) or "No matches in the first 2,000 names."
    names = {entry.name for location in ("/usr/share/applications", "/usr/local/share/applications",
                                         str(Path.home() / ".local/share/applications"),
                                         str(Path.home() / ".local/share/flatpak/exports/share/applications"))
             for entry in Path(location).glob("*.desktop") if argument.casefold() in entry.stem.casefold()}
    return "\n".join(sorted(names)[:40]) or "No matching application IDs."
