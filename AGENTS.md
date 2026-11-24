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

## Phase workflow

- Initially read only AGENTS.md and PROGRESS.md, then run `git status --short`.
- Use `rg --files` and targeted `rg -n` searches. Read only files relevant to the phase.
- Reuse working code, dependencies, and design tokens. Make incremental edits.
- Keep logs concise, avoid duplicate builds and tool calls, and run targeted tests before final validation.
- Report changes, tests, blockers and the next command in at most 150 words unless the user sets another limit.
