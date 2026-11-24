# NovaOS progress

## Phase 10 · First bootable release

- Prepared the manual Alpha workflow to produce `NovaOS-0.1.0-alpha-amd64.iso`, checksums, build summary, known issues, manifests, and Debian license notices after signed APT preflight and ISO inspection.
- Local fixture suites and workflow lint passed. Verified 29 live-build option names against Debian's implementation, parsed all eight Calamares YAML files, and checked executable modes and direct package availability. Signed dependency resolution and ISO inspection require the Linux run.
- Build and runtime gates remain pending. The repository has no remote or GitHub CLI credentials. The existing VirtualBox VM is paused with no ISO or forwarded SSH endpoint. It was left untouched.

## Phase 9 · Polish

- Added shared QML design components, revised the original wallpaper, and integrated Nova branding across SDDM, lock-screen wallpaper, Plymouth and Calamares.
- Fixed the Minimal install Music launcher mismatch, added native per-effect settings access, and recorded unresolved issues in BUGS.md.
- Pending Linux ISO validation, installation, high-DPI hardware testing, and guest measurements. No runtime improvement has been measured.
- All local fixture suites, workflow lint, Calamares YAML parsing, and the Debian package name audit passed. Reviewed the published Calamares job descriptors and Plymouth assets. The existing paused VM was inspected read-only.

## Phase 8 · Installer and recovery

- Integrated Calamares with Nova branding, explicit partition confirmation, offline base profiles, optional signed package setup, and first-boot Welcome.
- Added live recovery entry, scoped recovery tools, and update history and notifications. Firmware, encryption, installed boot and recovery remain unverified until disposable VM testing.

## Phase 7 · Nova AI

- Added an opt-in native assistant with local conversation history, streaming adapters, credential-wallet integration, selected attachments, explicit cloud consent, and previewed system actions.
- Added on-demand local Ollama installation, model management, hardware suggestions and session cleanup. The ISO package allowlist still contains no Ollama runtime or model.
- Live provider, Secret Service, QML, and hardware action verification remain pending a Linux guest. See [optional Nova AI](docs/AI.md).
- Local provider parsing, credential input, action approval and replay rejection, cancellation, installer checksum and regression fixtures passed.

## Phase 6 · Music and Store

- Implemented native Nova Music with SQLite, on-demand mpv/MPRIS playback, playlists, radio, artwork, local lyrics, a mini-player and a tray control. Added the native Store with an optional APT and Flatpak catalog, lazy metadata, and real package transactions in Konsole.
- Linux guest verification remains pending for QML, playback, media keys, lock-screen controls, store installation and removal, and hardware audio.
- Local SQLite, playlist round-trip, mpv command, catalog, transaction-consent and regression fixtures passed. Verified the mpv MPRIS plugin path against the Debian package and checked Flathub's live screenshot metadata shape.

## Phase 5 · Gaming

- Added the native Gaming Hub, local Steam discovery, editable game records, artwork and history where available, per-game boost and overlay controls, and optional setup and capture paths. Heavy gaming packages remain outside the ISO manifest.
- Local Steam fixture, launch argument, profile restoration, source, desktop, and workflow checks passed. Trixie's main archive did not list a native Gamescope package. The optional Flatpak extension is available separately.
- Pending Linux guest verification of launcher and QML behavior, Steam and Wine processes, Flatpak runtime extension branches, real hardware and overlay shortcuts, and recording. See [gaming and compatibility](docs/GAMING.md).

## Phase 4 · Performance

- Configured bounded ZRAM swap and size-ranked installed package reports. Moved the dedicated 7-Zip CLI out of the direct package list and retained Ark's libarchive backend.
- Added an on-demand QML Performance Center, hardware power holds, reversible low-effects profiles, and optional GameMode integration. Existing essential services and package gates remain in place.
- Added Linux guest benchmarking and a baseline table in PERFORMANCE.md. Actual boot, memory, application startup, hardware metrics, and guest profile restoration remain pending ISO builds and VirtualBox tests.
- Local source, profile and restoration fixtures, launcher tests, desktop tests, Python compilation and workflow lint passed. No guest metrics were collected.
- Added CPU history and guest benchmark evidence for display, networking, audio, and APT source configuration.

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
