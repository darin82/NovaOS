# NovaOS architecture and required defaults

NovaOS targets gamers, developers, enthusiasts, and users who want direct control of a lean amd64 system. Phase 1 continued on Debian stable, systemd, and a minimal KDE Plasma Wayland session.

## Package and service policy

- The four lists in `packages/` are the allowlist for directly requested packages. Install essential hardware and session stacks and give every new direct package a rationale. Use signed Debian archives, keep security updates available, and leave automatic dependency recommendations disabled.
- Exclude Microsoft Edge, Teams, Facebook, PowerPoint, Microsoft Office, Outlook, OneDrive, LinkedIn, LibreOffice, corporate suites, advertising and sponsored apps, news feeds, shopping services, trial antivirus, promotional games, and social media apps. The image audit rejects the known package names and prefixes in `packages/exclusions.regex`. Review the complete package and startup inventories for new products or renamed packages.
- Use Firefox ESR as the supported browser. Disable sponsored content, news recommendations, and telemetry by default. Use mature browser engines.
- Keep one default browser, terminal, and file manager. Avoid KDE bundles, Electron, and background work by optional apps. Nova Store offers optional office software on demand. Keep AI model and gaming-service packages out of the base image.
- Keep Baloo indexing off. Retain Debian's `kio-extras` package for Dolphin's non-indexed filename search. Review dependencies before removing them. Preserve graphics, networking, audio, security updates, and the desktop during every trim.
- Keep the black, white, and purple visual identity and a small, focused launcher and taskbar.

## Audit and release evidence

The chroot records all installed packages plus system and user unit-file states, wanted units, and XDG autostarts. The ISO gate reads these inventories from the built squashfs, compares the package inventory against the ISO manifest, and rejects excluded packages or prohibited enabled startup entries. Disabled and masked entries remain visible in the startup report for review. The report describes on-disk startup configuration. The guest checks below cover runtime behavior.

Each successful ISO build publishes `installed-packages.tsv`, `background-services.tsv`, and `performance-benchmark.json`, with checksums. The benchmark measures single-thread SHA-256 throughput on the Linux build worker and records ISO and compressed rootfs size. Compare like-for-like runners. Record guest boot time and hardware and profile checks separately before claiming release performance. See [VirtualBox acceptance tests](VIRTUALBOX.md).

## Workload profiles

Open **Nova Performance** from the application launcher or run `nova-profile set PROFILE`. The selection applies to subsequent launches from NovaOS's Firefox ESR, Dolphin, and Konsole entries and to explicit `nova-run` commands. Applications that forward to an existing process continue in that process's original scope. KDE services keep their normal systemd settings.

| Profile | CLI value | Settings for a new managed launch |
| --- | --- | --- |
| Balanced | `balanced` | Default CPU weight of 100 |
| Nova Turbo | `turbo` | CPU weight 250 under contention |
| Nova Gaming | `gaming` | Weight 800 for explicitly launched games, 100 for normal apps |
| Nova Eco | `eco` | Weight 60 and nice increment 5 |
| Nova Ultra Lite | `ultra-lite` | Weight 25 and nice increment 12 |

Launch an installed game with `nova-run --game -- GAME [ARGS...]`. In Nova Gaming, the game and subprocesses in its user scope get a greater share of CPU time under contention. The transient scope ends with its processes. Launch opt-in tasks with `nova-run --background -- COMMAND` for weight 15 and nice increment 10. `nova-run --maintenance -- COMMAND` uses the same limits and returns exit 75 if a gaming scope is active, allowing the caller to retry later. APT and critical system services run outside this mechanism.

Profiles use relative user cgroup CPU weights and process niceness. Their effect depends on CPU contention and placement in the cgroup hierarchy. They leave GPU clocks, CPU governors, and power limits under kernel control.

## Optional applications

Start Nova Store from the application launcher. LibreOffice can be installed or removed as a per-user Flatpak. The install action sets up the signed Flathub remote on demand and hands off to the Flatpak confirmation prompt. Nothing starts in the background. In the live session installations are temporary.

- [systemd resource control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
- [Flatpak command reference](https://docs.flatpak.org/en/latest/flatpak-command-reference.html)
- [Firefox enterprise policy reference](https://mozilla.github.io/enterprise-admin-reference/reference/policies/)
