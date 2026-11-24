"""Validate the Calamares target and prepare its boot configuration."""
from pathlib import Path

import libcalamares


def run():
    value = libcalamares.globalstorage.value("rootMountPoint")
    if not isinstance(value, str):
        return ("Target missing", "Calamares has not mounted the target system.")
    root = Path(value).resolve()
    if root == Path("/") or not root.is_mount() or not (root / "usr/lib/novaos/os-release").is_file():
        return ("Invalid target", "The mounted target is not the NovaOS installation.")
    (root / "etc/default/grub.d").mkdir(parents=True, exist_ok=True)
    (root / "etc/default/grub.d/60-novaos.cfg").write_text(
        'GRUB_DISTRIBUTOR="NovaOS"\nGRUB_DISABLE_OS_PROBER=true\n'
        'GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT} splash"\n'
    )
    crypttab = root / "etc/crypttab"
    if crypttab.is_file() and any(line.strip() and not line.startswith("#") for line in crypttab.read_text().splitlines()):
        directory = root / "etc/initramfs-tools/conf.d"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "novaos-encryption").write_text("UMASK=0077\n")
    return None
