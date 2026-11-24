#!/usr/bin/python3
"""Unprivileged, bounded Linux metrics for the on-demand desktop dashboard."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def cpu_ticks():
    fields = Path("/proc/stat").read_text().splitlines()[0].split()[1:9]
    values = [int(value) for value in fields]
    return [sum(values), values[3] + values[4]]


def memory():
    return {line.split(":")[0]: int(line.split()[1]) for line in
            Path("/proc/meminfo").read_text().splitlines()}


def disk_bytes():
    total = 0
    for device in Path("/sys/block").iterdir():
        if device.name.startswith(("loop", "ram", "zram", "dm-", "md", "sr")):
            continue
        try:
            counts = (device / "stat").read_text().split()
            total += 512 * (int(counts[2]) + int(counts[6]))
        except (OSError, IndexError, ValueError):
            continue
    return total


def sensor_values(paths, scale):
    values = []
    for sensor in paths:
        try:
            values.append(int(sensor.read_text().strip()) / scale)
        except (OSError, ValueError):
            continue
    return values


def processes():
    rows = []
    for pid in Path("/proc").iterdir():
        if not pid.name.isdecimal():
            continue
        try:
            values = dict(line.split(":", 1) for line in (pid / "status").read_text().splitlines())
            rss = int(values.get("VmRSS", "0").split()[0])
            if rss:
                rows.append((rss, pid.name, values["Name"].strip()))
        except (OSError, ValueError, KeyError):
            continue
    return [f"{pid:>6}  {name:<22}  {rss // 1024:>5} MiB"
            for rss, pid, name in sorted(rows, reverse=True)[:8]]


def sample():
    mem = memory()
    gpu = sensor_values(Path("/sys/class/drm").glob("card*/device/gpu_busy_percent"), 1)
    sensors = sensor_values(Path("/sys/class/hwmon").glob("hwmon*/temp*_input"), 1000)
    sensors = [value for value in sensors if -50 < value < 150]
    return {
        "cpu": cpu_ticks(), "ram": [mem["MemTotal"] - mem["MemAvailable"], mem["MemTotal"]],
        "swap": [mem["SwapTotal"] - mem["SwapFree"], mem["SwapTotal"]],
        "gpu": max(gpu, default=None), "temperature": max(sensors, default=None),
        "disk": disk_bytes(), "timestamp": time.monotonic(), "processes": processes(),
        "profile": command("nova-profile", "get"),
    }


if __name__ == "__main__":
    if sys.platform != "linux" or not Path("/proc/stat").exists():
        raise SystemExit("Nova metrics require Linux procfs.")
    if sys.argv[1:] == ["boot"]:
        print(command("systemd-analyze", "time"))
    else:
        print(json.dumps(sample()))
