#!/usr/bin/python3
import json
import subprocess
import sys
from urllib.parse import unquote


def run(action, data):
    if action == "panel":
        size = int(data["size"])
        alignment = data["alignment"]
        if not 36 <= size <= 72 or alignment not in {"left", "center", "right"}:
            raise ValueError("Invalid taskbar size or alignment.")
        script = ("for (const panel of panels()) { if (panel.location === 'bottom') { "
                  f"panel.height = {size}; panel.alignment = '{alignment}'; }} }}")
        subprocess.run(["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
                        "org.kde.PlasmaShell.evaluateScript", script], check=True)
        return "Taskbar updated."
    foreground = {"dark": ["nova-appearance", "dark"], "light": ["nova-appearance", "light"]}
    if action in foreground:
        subprocess.run(foreground[action], check=True, stdout=subprocess.DEVNULL)
        return "Theme updated."
    tools = {
        "display": ["systemsettings", "kcm_kscreen"],
        "performance": ["qml6", "/usr/lib/novaos/Performance.qml"],
        "gaming": ["qml6", "/usr/lib/novaos/Gaming.qml"],
        "store": ["nova-store"],
        "updates": ["nova-update"],
    }
    if action not in tools:
        raise ValueError("Unknown welcome action.")
    subprocess.Popen(tools[action], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return "Opened."


if __name__ == "__main__":
    try:
        print(json.dumps(run(sys.argv[1], json.loads(unquote(sys.argv[2])))))
    except (OSError, KeyError, IndexError, ValueError, TypeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
