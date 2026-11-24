# NovaOS performance

| Guest metric | Phase 3 baseline | Phase 4 optimized |
| --- | --- | --- |
| Idle RAM and CPU | Pending | Pending |
| Boot duration and critical chain | Pending | Pending |
| System tree disk footprint | Pending | Pending |
| Processes and enabled services | Pending | Pending |
| Konsole startup | Pending | Pending |

No runtime results have been collected. The GitHub runner report measures the build worker and image size. It cannot substitute for a NovaOS guest run.

The 0.1.0 Alpha release gate still has no built image or guest measurements. Record the exact ISO size from `BUILD-SUMMARY.md` after compilation and the idle, boot, storage, and process metrics from the disposable guest. Windows-side fixture tests provide no runtime baseline.

## Repeatable comparison

Build the Phase 3 baseline from `0c060d3` and Phase 4 from the current branch. Boot each ISO with the same VirtualBox hardware and close foreground apps. Wait for the desktop to settle, then run the current benchmark script from Konsole in each guest.

```sh
python3 benchmark-guest.py --label baseline > baseline.json
nova-benchmark --label optimized > optimized.json
```

Use the same idle interval and firmware for each run. Keep the JSON alongside the relevant ISO hash. The script reports systemd timing, blame and critical chain, directory allocation for `/usr`, `/etc`, and `/var/lib/dpkg`, and three launches of a separate Konsole instance. The terminal measurement ends when the terminal child starts and serves as a repeatable startup readiness metric.

The release `package-sizes.tsv` ranks installed packages by Debian's Installed-Size estimate. It includes totals for the full resolved manifest, excluding live-image filesystem compression overhead. Use the startup inventory alongside the guest boot critical chain to identify targets for subsequent changes.

## Phase 4 defaults

ZRAM swap uses at most half of RAM with a 4 GiB cap. The systemd generator owns the RAM device and leaves physical storage untouched. The kernel chooses the compression algorithm. The image retains networking, audio, firmware and accessibility. The dedicated 7-Zip CLI is optional. Ark retains its upstream libarchive backend. Verify common archives in the guest.

Nova Turbo and Eco request temporary hardware power holds for managed workloads when the Power Profiles service lists the corresponding capability. The service owns and releases holds. Eco and Ultra Lite save appearance state on entry and restore it on leaving. Optional GameMode is used only by explicit Nova Gaming launches when its wrapper is installed. Nova Gaming continues to defer managed maintenance and leaves security services active.

- [Debian powerprofilesctl manual](https://manpages.debian.org/trixie/power-profiles-daemon/powerprofilesctl.1.en.html)
- [Debian ZRAM generator manual](https://manpages.debian.org/trixie/systemd-zram-generator/zram-generator.conf.5.en.html)
