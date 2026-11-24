"""Check installer integration and recovery behavior without touching a disk."""
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Installer(unittest.TestCase):
    def test_confirmation_order_and_profile_ids(self):
        settings = (ROOT / "installer/settings.conf").read_text()
        self.assertRegex(settings, r"(?m)^prompt-install: true$")
        self.assertRegex(settings, r"(?m)^disable-cancel-during-exec: true$")
        ui, execute = settings.split("  - exec:", 1)
        for step in ("locale", "keyboard", "partition", "users", "summary"):
            self.assertIn(f"- {step}", ui)
        positions = [execute.index(f"- {step}") for step in (
            "unpackfs", "nova-prepare", "bootloader", "initramfs", "nova-install", "umount")]
        self.assertEqual(positions, sorted(positions))
        profile = (ROOT / "installer/modules/profile.conf").read_text()
        self.assertEqual(set(re.findall(r"(?m)^  - id: (\w+)$", profile)),
                         {"minimal", "standard", "gaming", "developer"})

    def test_profile_refuses_host_root(self):
        library = Mock()
        library.globalstorage.value.return_value = "/"
        with patch.dict("sys.modules", {"libcalamares": library}):
            module = load("profile", ROOT / "installer/modules/nova-install/main.py")
        with patch.object(module.subprocess, "run") as command:
            self.assertEqual(module.run()[0], "Invalid target")
            command.assert_not_called()

    def test_recovery_copy_never_overwrites(self):
        recovery = load("recovery", ROOT / "installer/nova-recovery")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            original = folder / "source"
            original.write_bytes(b"data")
            copy = folder / "copy"
            recovery.copy_files(original, copy)
            self.assertEqual(copy.read_bytes(), b"data")
            with self.assertRaises(ValueError):
                recovery.copy_files(original, copy)
            with self.assertRaises(ValueError):
                recovery.copy_files(folder, folder / "nested")

    def test_minimal_target_drops_music_launcher(self):
        library = Mock()
        with patch.dict("sys.modules", {"libcalamares": library}):
            module = load("profile_minimal", ROOT / "installer/modules/nova-install/main.py")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            launcher = target / "usr/share/applications/org.novaos.Music.desktop"
            for path in (target / "usr/lib/novaos/os-release", launcher):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            (target / "var/log").mkdir(parents=True)
            library.globalstorage.value.side_effect = {
                "rootMountPoint": str(target), "packagechooser_profile": "minimal",
                "packagechooser_extras": "",
            }.get
            result = subprocess.CompletedProcess([], 0, "", "")
            with patch.object(Path, "is_mount", return_value=True), \
                    patch.object(module.subprocess, "run", return_value=result) as command:
                self.assertIsNone(module.run())
            self.assertFalse(launcher.exists())
            self.assertIn("mpv", command.call_args.args[0])

    def test_boot_uses_native_password_prompt_plugin(self):
        descriptor = (ROOT / "desktop/plymouth/novaos.plymouth").read_text()
        self.assertIn("ModuleName=two-step", descriptor)
        self.assertIn("DialogVerticalAlignment", descriptor)
        self.assertIn("QtVersion=6", (ROOT / "desktop/sddm/metadata.desktop").read_text())
        greeter = (ROOT / "desktop/sddm/Main.qml").read_text()
        self.assertIn("sddm.login(", greeter)
        self.assertIn("TextInput.Password", greeter)


if __name__ == "__main__":
    unittest.main()
