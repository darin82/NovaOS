"""Exercise the image-policy gate and user workload selection without a Linux guest."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SH = shutil.which("sh")


class ImagePolicy(unittest.TestCase):
    def test_clean_and_blocked_inventory(self):
        names = sorted({
            package for path in (ROOT / "packages").glob("*.list.chroot")
            for package in path.read_text(encoding="utf-8").splitlines()
        })
        with tempfile.TemporaryDirectory() as temp:
            reports = Path(temp)

            def audit(package_names, state, unit):
                rows = ["package\tversion\tsource\tsection\tinstalled_kib"]
                rows += [f"{name}\t1\t{name}\tutils\t42" for name in package_names]
                (reports / "installed-packages.tsv").write_text("\n".join(rows) + "\n")
                (reports / "live.packages").write_text(
                    "".join(f"{name}\t1\n" for name in package_names)
                )
                (reports / "background-services.tsv").write_text(
                    f"scope\tunit\tstate\tcommand_or_target\nuser\t{unit}\t{state}\t\n"
                )
                return subprocess.run(
                    [sys.executable, ROOT / "scripts/audit-image.py", ROOT, reports],
                    capture_output=True, text=True,
                )

            clean = audit(names, "masked", "kde-baloo.service")
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertIn("allowlist", (reports / "installed-packages.tsv").read_text())
            self.assertIn(f"TOTAL_KNOWN\t{len(names) * 42}", (reports / "package-sizes.tsv").read_text())
            failed = audit(names + ["libreoffice-writer"], "enabled", "gamemoded.service")
            self.assertEqual(failed.returncode, 1, failed.stderr)
            self.assertIn("Excluded package: libreoffice-writer", failed.stderr)
            self.assertIn("Excluded startup entry: user/gamemoded.service", failed.stderr)


@unittest.skipUnless(SH, "POSIX shell unavailable")
class Profiles(unittest.TestCase):
    def test_profiles_and_gaming_deferral(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            shutil.copyfile(ROOT / "apps/nova-profile", work / "nova-profile")
            for name, contents in {
                "systemctl": "#!/bin/sh\nprintf '%s' \"${NOVA_TEST_GAME:-}\"\n",
                "systemd-run": '#!/bin/sh\nprintf "%s\\n" "$@"\n',
                "powerprofilesctl": '#!/bin/sh\nprintf "  performance:\\n* power-saver:\\n"\n',
                "gamemoderun": '#!/bin/sh\nexit 0\n',
                "flock": '#!/bin/sh\nexit 0\n',
                "nova-appearance": ('#!/bin/sh\nif [ "$1" = snapshot ]; then\n'
                                    '  echo "true false 0.8"\nelse\n'
                                    '  echo "$*" >> "$NOVA_TEST_APPEARANCE"\nfi\n'),
            }.items():
                (work / name).write_bytes(contents.encode())
            for path in work.iterdir():
                path.chmod(0o755)
            env = dict(os.environ, XDG_CONFIG_HOME=work.as_posix(),
                       XDG_SESSION_TYPE="", DBUS_SESSION_BUS_ADDRESS="",
                       PATH=f"{temp}{os.pathsep}{os.environ['PATH']}")

            def shell(script, *args, **extra_env):
                return subprocess.run(
                    [SH, ROOT / "apps" / script, *args], check=False,
                    env=dict(env, **extra_env), capture_output=True, text=True,
                )

            self.assertEqual(shell("nova-profile", "get").stdout.strip(), "balanced")
            for profile, weight in (("balanced", 100), ("turbo", 250), ("gaming", 800),
                                    ("eco", 60), ("ultra-lite", 25)):
                selected = shell("nova-profile", "set", profile)
                self.assertEqual(selected.returncode, 0, selected.stderr)
                launched = shell("nova-run", "--game", "--", "test-game")
                self.assertEqual(launched.returncode, 0, launched.stderr)
                self.assertIn(f"CPUWeight={weight}", launched.stdout)
                if profile == "turbo":
                    self.assertIn("performance", launched.stdout)
                if profile == "gaming":
                    self.assertIn("gamemoderun", launched.stdout)
            deferred = shell("nova-run", "--maintenance", "--", "test-task",
                             NOVA_TEST_GAME="nova-game-100.scope")
            self.assertEqual(deferred.returncode, 75, deferred.stderr)
            resumed = shell("nova-run", "--maintenance", "--", "test-task")
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn("CPUWeight=5", resumed.stdout)

            appearance_log = work / "appearance.log"
            session = dict(XDG_SESSION_TYPE="wayland", DBUS_SESSION_BUS_ADDRESS="fixture",
                           NOVA_TEST_APPEARANCE=appearance_log.as_posix())
            for profile in ("eco", "ultra-lite", "balanced"):
                switched = shell("nova-profile", "set", profile, **session)
                self.assertEqual(switched.returncode, 0, switched.stderr)
            self.assertEqual(appearance_log.read_text().splitlines(),
                             ["eco", "ultra-lite", "restore true false 0.8"])
            self.assertFalse((work / "novaos/appearance-before-profile").exists())


if __name__ == "__main__":
    unittest.main()
