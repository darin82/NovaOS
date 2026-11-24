# NovaOS

NovaOS 0.1.0 Alpha is the first live-media release target for a Debian 13 (Trixie) amd64 distribution. The image configuration uses the Debian Linux kernel, systemd, KDE Plasma 6 on Wayland, and SDDM live-session login. Nova Midnight is the default color scheme. Nova Daybreak is available in System Settings under Colors.

The live image targets BIOS and UEFI with Secure Boot disabled. It runs from virtual optical media and includes the NovaOS Calamares installer. Live-session changes are temporary. See [installation tests](docs/VIRTUALBOX.md).

The default desktop includes Firefox ESR, Konsole, and Dolphin. **Nova Performance** selects one of five workload profiles. **Nova Store** offers LibreOffice as an optional per-user Flatpak. See the [architecture requirements](docs/ARCHITECTURE.md) for package policy, startup rules, and profile behavior.

## Build on GitHub

1. Push this repository to a GitHub repository with Actions enabled.
2. Open **Actions → NovaOS ISO → Run workflow**. A tag matching `v0.1.0-alpha` also triggers the build.
3. Download **novaos-amd64** from the successful run. It contains the ISO, checksums, package manifests, background-service report, build-worker performance benchmark, and build-tool inventory. On failure, download **novaos-build-log**.

The ISO job builds in a fresh Debian 13 container on a disposable Linux runner. The job uses a privileged container to let live-build mount its chroot and create the boot image. Windows needs no WSL, Docker, or administrator access for this workflow.

## Boot and verify

Follow the [VirtualBox test guide](docs/VIRTUALBOX.md) to verify the download and boot a separate diskless VM. Open [PROGRESS.md](PROGRESS.md) for current verification status.

## Source layout

| Path | Contents |
| --- | --- |
| `build/` | Debian build environment and suite settings |
| `branding/` | Original vector logo and wallpaper |
| `desktop/` | Plasma defaults, panel setup, and color schemes |
| `packages/` | Explicit live-image package lists |
| `scripts/` | ISO build entry point |
| `tests/` | Source validation and ISO inspection |
| `docs/` | VirtualBox and build documentation |
| `apps/` | Default application associations |
| `config/` | live-build overlays, GRUB template, and hooks |
| `.github/workflows/` | GitHub Actions jobs |

Run `python3 tests/validate-source.py` and `node --check desktop/nova-layout.js` where Python and Node are available. See [Build and versioning](docs/BUILD.md) for package resolution, release procedure, and artifact checks.

### Upstream references

- [Debian Live Manual](https://live-team.pages.debian.net/live-manual/html/live-manual.en.html)
- [Debian Trixie live-build options](https://manpages.debian.org/trixie/live-build/lb_config.1.en.html)
- [KDE Plasma scripting API](https://develop.kde.org/docs/plasma/scripting/api/)
