"""Exercise launcher branding and update guards without starting graphical apps or APT."""
from configparser import ConfigParser
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AWK = shutil.which("awk")
SH = shutil.which("sh")


class AppIntegration(unittest.TestCase):
    def test_launcher_inventory(self):
        entries = {}
        for line in (ROOT / "apps/launchers.tsv").read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            desktop_id, name, icon, executable, visibility = line.split("|")
            self.assertNotIn(desktop_id, entries)
            self.assertIn(visibility, {"show", "hide"})
            self.assertTrue(executable)
            if visibility == "show":
                self.assertTrue(name.startswith("Nova "))
                ET.parse(ROOT / f"desktop/icons/{icon}.svg")
            entries[desktop_id] = visibility
        self.assertEqual(list(entries.values()).count("show"), 9)
        ET.parse(ROOT / "desktop/icons/nova-update.svg")
        config = ConfigParser(interpolation=None)
        config.read(ROOT / "apps/mimeapps.list")
        for desktop_id in config["Default Applications"].values():
            self.assertIn(desktop_id.rstrip(";"), entries)

    @unittest.skipUnless(AWK, "awk unavailable")
    def test_preserve_upstream_actions_and_add_startup(self):
        result = subprocess.run([
            AWK, "-v", "name=Nova Monitor", "-v", "icon=nova-monitor",
            "-v", "monitor=1", "-f", ROOT / "apps/brand-launchers.awk",
        ], input="[Desktop Entry.ignored]\nName=Other\n[Desktop Entry]\n"
                 "Name=Original\nName[es]=Original ES\nActions=Details;\n"
                 "Exec=plasma-systemmonitor\n\n[Desktop Action Details]\n"
                 "Name=Details\nExec=plasma-systemmonitor --details\n",
            capture_output=True, text=True, check=True)
        self.assertIn("Name=Nova Monitor", result.stdout)
        self.assertIn("Actions=Details;StartupApps;", result.stdout)
        self.assertNotIn("Name[es]", result.stdout)
        self.assertIn("Exec=plasma-systemmonitor --details", result.stdout)
        self.assertIn("Exec=systemsettings kcm_autostart", result.stdout)

    @unittest.skipUnless(SH, "POSIX shell unavailable")
    def test_package_info_rejects_options(self):
        result = subprocess.run([SH, ROOT / "apps/nova-update", "info", "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Debian package name", result.stderr)

    @unittest.skipUnless(SH, "POSIX shell unavailable")
    def test_update_failure_prevents_upgrade(self):
        with tempfile.TemporaryDirectory() as temporary:
            sudo = Path(temporary) / "sudo"
            sudo.write_bytes(b'#!/bin/sh\nprintf "%s\\n" "$@"\nexit 1\n')
            sudo.chmod(0o755)
            env = dict(os.environ, PATH=temporary + os.pathsep + os.environ["PATH"])
            result = subprocess.run([SH, ROOT / "apps/nova-update", "apply"],
                                    env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("APT::Get::AllowUnauthenticated=false", result.stdout)
        self.assertIn("APT::Update::Error-Mode=any", result.stdout)
        self.assertNotIn("upgrade", result.stdout)
        self.assertIn("No upgrades were started", result.stderr)


if __name__ == "__main__":
    unittest.main()
