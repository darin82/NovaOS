"""Measure an offline Linux build-worker workload and document its context."""
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time


def measure():
    block = bytes(1024 * 1024)
    rates = []
    for _ in range(3):
        digest = hashlib.sha256()
        start = time.perf_counter()
        for _ in range(128):
            digest.update(block)
        rates.append(round(128 / (time.perf_counter() - start), 2))
    return rates


iso, rootfs, report = map(Path, sys.argv[1:])
rates = measure()
report.write_text(json.dumps({
    "scope": "Build-worker CPU throughput and image size",
    "worker_os": platform.system(),
    "kernel": platform.release(),
    "architecture": platform.machine(),
    "available_cpus": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count(),
    "iso_bytes": iso.stat().st_size,
    "compressed_rootfs_bytes": rootfs.stat().st_size,
    "sha256_128_mib_single_thread_runs_mib_s": rates,
    "sha256_median_mib_s": statistics.median(rates),
}, indent=2) + "\n", encoding="utf-8")
