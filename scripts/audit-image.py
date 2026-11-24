"""Enforce NovaOS package and startup policies against the live-image reports."""
from pathlib import Path
import re
import sys


def rules(path):
    return [
        re.compile(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]


def main(root, reports):
    selected = {
        name for source in (root / "packages").glob("*.list.chroot")
        for name in source.read_text(encoding="utf-8").splitlines()
    }
    packages = rules(root / "packages/exclusions.regex")
    startup = rules(root / "config/startup-exclusions.regex")
    inventory = reports / "installed-packages.tsv"
    rows = inventory.read_text(encoding="utf-8").splitlines()[1:]
    inventory_names = set()
    sizes = []
    annotated = ["package\tversion\tsource\tsection\tinstalled_kib\tselection"]
    violations = []
    for row in rows:
        package = row.split("\t", 1)[0].split(":", 1)[0]
        inventory_names.add(package)
        selection = "allowlist" if package in selected else "Debian base or dependency"
        annotated.append(f"{row}\t{selection}")
        raw_size = row.rsplit("\t", 1)[-1]
        if raw_size.isdecimal():
            sizes.append((int(raw_size), package))
        if any(rule.search(package) for rule in packages):
            violations.append(f"Excluded package: {package}")
    for package in sorted(selected - inventory_names):
        violations.append(f"Allowlisted package missing: {package}")
    resolved = {
        row.split()[0].split(":", 1)[0]
        for row in (reports / "live.packages").read_text(encoding="utf-8").splitlines()
        if row
    }
    if resolved != inventory_names:
        violations.append(f"Package inventory differs from ISO manifest: {sorted(resolved ^ inventory_names)}")

    services = (reports / "background-services.tsv").read_text(encoding="utf-8").splitlines()[1:]
    if not services:
        violations.append("Startup report is empty")
    for row in services:
        scope, unit, state, command = row.split("\t", 3)
        if state in {"enabled", "enabled-runtime", "wanted", "xdg-autostart"} and any(
            rule.search(f"{unit} {command}") for rule in startup
        ):
            violations.append(f"Excluded startup entry: {scope}/{unit} ({state})")

    inventory.write_text("\n".join(annotated) + "\n", encoding="utf-8")
    (reports / "package-sizes.tsv").write_text(
        "package\tinstalled_kib\n"
        + "".join(f"{name}\t{size}\n" for size, name in sorted(sizes, reverse=True))
        + f"TOTAL_KNOWN\t{sum(size for size, _ in sizes)}\n"
        + f"PACKAGES_WITHOUT_SIZE\t{len(rows) - len(sizes)}\n", encoding="utf-8")
    if violations:
        print("\n".join(violations), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
