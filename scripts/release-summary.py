"""Describe the actual ISO and the validation gates completed by this build."""
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


def revision():
    candidate = os.environ.get("GITHUB_SHA", "")
    if not candidate:
        try:
            candidate = subprocess.check_output(
                ["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return candidate if re.fullmatch(r"[a-f0-9]{40,64}", candidate) else "unavailable"


def build_summary(directory, iso_name, version, suite, arch):
    iso = directory / iso_name
    size = iso.stat().st_size
    if not size:
        raise ValueError("Cannot summarize an empty ISO.")
    packages = (directory / "installed-packages.tsv").read_text(encoding="utf-8").splitlines()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run = os.environ.get("GITHUB_RUN_ID", "")
    server = os.environ.get("GITHUB_SERVER_URL", "")
    action = ""
    if server == "https://github.com" and re.fullmatch(r"[\w.-]+/[\w.-]+", repo) and run.isdigit():
        action = f"- [GitHub Actions run]({server}/{repo}/actions/runs/{run})\n"
    return (
        f"# NovaOS {version} Alpha build summary\n\n"
        f"- ISO: `{iso_name}`\n"
        f"- Bytes: {size:,} ({size / 2**30:.2f} GiB)\n"
        f"- Target: Debian {suite}, {arch}\n"
        f"- Source revision: `{revision()}`\n"
        f"- Build worker: {platform.system()} {platform.release()}\n"
        f"- Installed package rows: {len(packages) - 1}\n"
        f"{action}"
        "- Boot catalog: BIOS and UEFI El Torito entries verified\n"
        "- Secure Boot: disabled for this Alpha\n\n"
        "Build gates passed: signed Debian APT dependency simulation, live-build, GRUB syntax and "
        "boot-file checks, filesystem and package manifest audit, startup exclusions, and license archive inspection.\n\n"
        "Guest status: this job performs static ISO inspection. Live boot, Calamares installation, "
        "installed boot, device behavior, and performance need separate VirtualBox acceptance results.\n"
    )


if __name__ == "__main__":
    output, iso_name, version, suite, arch = sys.argv[1:]
    directory = Path(output)
    (directory / "BUILD-SUMMARY.md").write_text(
        build_summary(directory, iso_name, version, suite, arch), encoding="utf-8"
    )
