# Build and versioning

[VERSION](../VERSION) drives the ISO name and GRUB and OS labels. This repository targets the Alpha channel. Commit version and changelog updates together. Build a candidate with the Actions workflow, then use `v<version>-alpha` for a tagged build. Record the tagged artifact's workflow URL, ISO digest, and VM test results before calling it a tested release.

## Package reproducibility

The repository fixes the Debian suite, architecture, archive components, explicitly requested package names, and recommendation policy. APT resolves transitive dependencies from signed Trixie, Trixie Updates, and Trixie Security archives. Publish the resolved package manifest and build-tool versions with the ISO. Package versions and ISO hashes can change as Debian ships security and point updates. Identical inputs here specify the same package selection policy, with archive contents resolved at build time.

APT security updates remain enabled. Nova Store adds the Flathub remote only when the user chooses to install LibreOffice.

## Validation gates

- Source checks validate version, package lists, SVG XML, wallpaper metadata, color scheme syntax, shell syntax when `sh` is available, and GRUB tokens. CI also checks the Plasma JavaScript syntax.
- A chroot hook verifies the Wayland session and required applications, enables NetworkManager and SDDM, and verifies that the build has access to the Debian security archive.
- Post-build inspection checks BIOS and EFI El Torito boot catalog entries, GRUB syntax and references, the squashfs release identity, final security repository, and the package manifest.
- The ISO gate rejects excluded packages and startup entries. The artifact includes the full inventory and a Linux build-worker benchmark. See [architecture requirements](ARCHITECTURE.md).
- The VirtualBox test confirms the graphical boot and exercises the runtime services.

The workflow streams live-build diagnostics to an uploaded log. The build entry point requires root inside Debian 13 and keeps its temporary build directory for diagnosis until the disposable container exits. For reruns use a fresh Action job. On the Windows host use only the source checks available locally and the optional ISO checksum verification.
