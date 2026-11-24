"""Test release metadata without building or claiming a Linux runtime result."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_summary", ROOT / "scripts/release-summary.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class Release(unittest.TestCase):
    def test_apt_dependencies_are_checked_before_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / "resolution.log"
            allowed = "Inst dolphin (1 Debian)\nInst evolution-data-server-common (1 Debian)\n"
            plan.write_text(allowed)
            command = [
                sys.executable, ROOT / "scripts/audit-image.py", "--apt-plan", ROOT, plan,
            ]
            checked = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            plan.write_text(allowed + "Inst evolution (1 Debian)\nInst evolution-data-server:amd64 (1 Debian)\n"
                            "Inst evolution-plugins (1 Debian)\nInst libreoffice-writer:amd64 (1 Debian)\n")
            checked = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("libreoffice-writer", checked.stderr)
        self.assertIn("evolution, evolution-data-server, evolution-plugins", checked.stderr)
        self.assertNotIn("evolution-data-server-common", checked.stderr)

    def test_iso_release_checks_are_wired(self):
        build = (ROOT / "scripts/build-iso.sh").read_text()
        for name in ("BUILD-SUMMARY.md", "LICENSE-NOTICES.md", "KNOWN-ISSUES.md",
                     "package-license-notices.tar.gz", "license-notice-index.tsv"):
            self.assertIn(name, build)
        self.assertIn('ISO_NAME="NovaOS-$VERSION-alpha-$ARCH.iso"', build)
        self.assertLess(build.index("--simulate"), build.index("\nlb build"))
        self.assertLess(build.index("verify-iso.sh"), build.index('mv -T -- "$STAGING" "$DEST"'))
        self.assertIn("sha256sum --check SHA256SUMS", build)

    def test_summary_uses_real_artifact_size_and_scopes_boot_claim(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "GITHUB_SHA": "a" * 40, "GITHUB_REPOSITORY": "owner/NovaOS",
            "GITHUB_RUN_ID": "123", "GITHUB_SERVER_URL": "https://github.com",
        }):
            directory = Path(temporary)
            name = "NovaOS-0.1.0-alpha-amd64.iso"
            (directory / name).write_bytes(b"fixture")
            (directory / "installed-packages.tsv").write_text("package\nbase-files\n")
            text = release.build_summary(directory, name, "0.1.0", "trixie", "amd64")
        self.assertIn(name, text)
        self.assertIn("Bytes: 7", text)
        self.assertIn("Installed package rows: 1", text)
        self.assertIn("/actions/runs/123", text)
        self.assertIn("need separate VirtualBox acceptance", text)


if __name__ == "__main__":
    unittest.main()
