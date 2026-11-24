#!/usr/bin/python3
"""Collect a repeatable NovaOS Wayland guest benchmark and startup audit."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import tempfile
import time


def read_command(*args, timeout=30):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return {"status": result.returncode, "output": result.stdout.strip(),
                "error": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": None, "output": "", "error": str(error)}


def cpu():
    counters = [int(field) for field in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
    return sum(counters), sum(counters[3:5])


def memory():
    mem = {line.split(":")[0]: int(line.split()[1])
           for line in Path("/proc/meminfo").read_text().splitlines()}
    return mem["MemTotal"] - mem["MemAvailable"]


def launch_terminal():
    with tempfile.TemporaryDirectory(prefix="nova-benchmark-") as work:
        marker = Path(work) / "ready"
        start = time.monotonic()
        try:
            process = subprocess.Popen([
                "konsole", "--separate", "-e", "python3", "-c",
                "from pathlib import Path; import sys,time; Path(sys.argv[1]).write_text(str(time.monotonic()))",
                str(marker),
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as error:
            return {"milliseconds": None, "error": str(error)}
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return {"milliseconds": None, "error": "Terminal launch timed out"}
        if process.returncode != 0 or not marker.exists():
            return {"milliseconds": None, "error": "Terminal child did not become ready"}
        return {"milliseconds": round((float(marker.read_text()) - start) * 1000, 1)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=("baseline", "optimized"), required=True)
    parser.add_argument("--idle-seconds", type=int, default=10, choices=range(3, 61), metavar="3-60")
    parser.add_argument("--iso-sha256", help="SHA-256 of the booted ISO")
    args = parser.parse_args()
    if args.iso_sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", args.iso_sha256):
        parser.error("--iso-sha256 requires 64 hexadecimal digits")
    if platform.system() != "Linux" or platform.freedesktop_os_release().get("ID") != "novaos":
        parser.error("run this benchmark inside a booted NovaOS Linux system")
    if os.environ.get("XDG_SESSION_TYPE") != "wayland" or os.getuid() == 0:
        parser.error("run as the desktop user in a Plasma Wayland session")
    os.environ["LC_ALL"] = "C"

    first_total, first_idle = cpu()
    first_memory = memory()
    time.sleep(args.idle_seconds)
    last_total, last_idle = cpu()
    used_memory = round((first_memory + memory()) / 2)
    units = read_command("systemctl", "list-unit-files", "--type=service", "--state=enabled",
                         "--no-legend", "--no-pager")
    user_units = read_command("systemctl", "--user", "list-unit-files", "--type=service",
                              "--state=enabled", "--no-legend", "--no-pager")
    print(json.dumps({
        "label": args.label, "kernel": platform.release(), "idle_seconds": args.idle_seconds,
        "iso_sha256": args.iso_sha256.lower() if args.iso_sha256 else None,
        "idle_ram_kib": used_memory,
        "idle_cpu_percent": round(100 * (1 - (last_idle - first_idle) / (last_total - first_total)), 2)
        if last_total > first_total else None,
        "process_count": sum(item.name.isdecimal() for item in Path("/proc").iterdir()),
        "enabled_system_service_count": len(units["output"].splitlines()) if units["status"] == 0 else None,
        "enabled_user_service_count": len(user_units["output"].splitlines()) if user_units["status"] == 0 else None,
        "enabled_system_services": units, "enabled_user_services": user_units,
        "boot_duration": read_command("systemd-analyze", "time"),
        "boot_blame": read_command("systemd-analyze", "blame", "--no-pager"),
        "boot_critical_chain": read_command("systemd-analyze", "critical-chain", "--no-pager"),
        "installed_tree_kib": read_command("du", "-skx", "/usr", "/etc", "/var/lib/dpkg", timeout=120),
        "terminal_child_startup": [launch_terminal() for _ in range(3)],
        "swaps": read_command("swapon", "--show"),
        "guest_health": {
            "display_manager": read_command("systemctl", "is-active", "display-manager.service"),
            "network_manager": read_command("systemctl", "is-active", "NetworkManager.service"),
            "network_devices": read_command("nmcli", "-t", "-f", "TYPE,STATE", "device", "status"),
            "audio_pipewire": read_command("systemctl", "--user", "is-active", "pipewire.service"),
            "audio_wireplumber": read_command("systemctl", "--user", "is-active", "wireplumber.service"),
            "apt_sources": read_command("apt-cache", "policy"),
        },
    }, indent=2))


if __name__ == "__main__":
    main()
