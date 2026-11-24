# NovaOS progress

## Phase 4 · Performance

- Configured bounded ZRAM swap and size-ranked installed package reports. Moved the dedicated 7-Zip CLI out of the direct package list and retained Ark's libarchive backend.
- Added an on-demand QML Performance Center, hardware power holds, reversible low-effects profiles, and optional GameMode integration. Existing essential services and package gates remain in place.
- Added Linux guest benchmarking and a baseline table in PERFORMANCE.md. Actual boot, memory, application startup, hardware metrics, and guest profile restoration remain pending ISO builds and VirtualBox tests.
- Local source, profile and restoration fixtures, launcher tests, desktop tests, Python compilation and workflow lint passed. No guest metrics were collected.

## Phase 3 · System applications

- Integrated the ten Nova launchers, MIME defaults, terminal palettes, editor autosave for named files, and on-demand signed APT updates. Upstream desktop IDs and package attribution are retained.
- Added nine direct packages for editing, media, calculation, archives, Bluetooth and power settings. Kate is the sole text editor, Ark is a file handler, and Haruna's optional download helper is excluded by the existing no-recommends policy.
- Local source, launcher, update failure-path, Zero Bloat, desktop fixture and workflow checks passed. Debian package metadata was inspected. ISO resolution, real launcher activation, GPU sensors/decoding, screen recording and hardware-dependent settings still need guest verification.

## Phase 2 · Desktop experience

- Implemented the native Nova Quick Settings applet, exact dark palette, light scheme, Breeze-based symbolic icons and rounded decorations, and new-user desktop shortcuts.
- Local source, shell syntax, workflow lint, mocked layout, and Zero Bloat regression checks passed. Spectacle and Plasma System Monitor are the two new direct packages, both used by requested shortcuts.
- Pending a Linux ISO build and a fresh VirtualBox login. Verify QML loading, keyboard capture, effects, panel persistence, and Phase 1 runtime checks using the VM guide.

## 0.1.0 Alpha · Phase 1

The source repository, GitHub Actions workflow, desktop branding, package lists, and VirtualBox procedure are implemented. The image targets live boot only on amd64.

The Zero Bloat update keeps 46 direct packages, adds the package and startup gates and report collection, and provides Nova Performance and Nova Store. The local audit and profile fixture tests pass. The Linux release artifacts, startup state, application installs, profile effects, and non-indexed Dolphin search still require a real ISO and guest run.

| Check | Status |
| --- | --- |
| Source and package validation | Passed on Windows using portable Python, POSIX shell syntax checks, Node, and actionlint. Explicit packages checked against the Debian amd64 archive indexes. |
| GitHub Linux ISO build | Pending workflow run. This repository has no configured GitHub remote. |
| ISO, checksum, and resolved package manifest | Pending successful Linux build. |
| BIOS and UEFI boot | Pending ISO artifact and diskless VM test. |
| Wayland, desktop appearance, network, audio, and apps | Pending VM acceptance test. |

The Windows workspace contains the repository. No Windows settings were changed. The existing paused NovaOS VM was inspected read-only and remains outside this test plan.

Start the first build through Actions once the repository is published to an authorized GitHub destination. Record the workflow URL, artifact checksum, and BIOS and UEFI results here. The build uses Debian archive updates rather than a frozen snapshot to preserve security fixes.
