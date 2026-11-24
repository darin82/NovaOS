# Working on NovaOS

Read [PROGRESS.md](PROGRESS.md) first. It tracks what actually ran and what evidence remains outstanding.
Use [the architecture requirements](docs/ARCHITECTURE.md) for package policy, startup policy, and performance profiles.

- Keep Windows unchanged. Do not install host tools, enable WSL, change the user's existing VM, or touch physical disks.
- Obtain approval before privileged or destructive operations. The existing ISO workflow defines a privileged build container on a disposable runner. Start it only under the repository owner's authorization.
- Keep the suite on Debian stable until a planned migration. Preserve signed APT metadata and upstream security updates.
- Add explicit package names to the existing functional lists and record the rationale for new dependencies.
- Review the resolved package and background-service inventories for each release. Keep optional apps, games, and AI models out of the base image. Re-run the VirtualBox runtime checks when changing dependencies or startup behavior.
- Keep paths, Bash/POSIX scripts, YAML, and Plasma scripts LF-terminated. Run source validation before handing off.
- Treat a successful source check, ISO inspection, and VM boot as different evidence. Record the exact workflow run and VirtualBox settings once available.
- Update PROGRESS.md whenever build or boot status changes. Update CHANGELOG.md for user-visible changes.
