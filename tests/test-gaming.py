"""Verify Steam discovery and managed launch arguments with local fixtures."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gaming", ROOT / "apps/nova-gaming.py")
gaming = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gaming)


class Gaming(unittest.TestCase):
    def test_nested_vdf_and_installed_game_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stock = root / "steamapps"
            external = root / "Second Library"
            common = external / "steamapps/common/Test Game"
            common.mkdir(parents=True)
            stock.mkdir()
            (stock / "libraryfolders.vdf").write_text(
                '"libraryfolders" { "0" { "path" "' + external.as_posix() + '" } }'
            )
            manifest = '"AppState" { "appid" "42" "name" "A \\"Game\\"" "installdir" "Test Game" '
            (external / "steamapps/appmanifest_42.acf").write_text(
                manifest + '"StateFlags" "4" "LastPlayed" "12" "SizeOnDisk" "30" }'
            )
            (external / "steamapps/appmanifest_55.acf").write_text(
                manifest.replace('"42"', '"55"') + '"StateFlags" "2" }'
            )
            files = root / "userdata/123/config"
            files.mkdir(parents=True)
            (files / "localconfig.vdf").write_text(
                '"UserLocalConfigStore" { "Software" { "Valve" { "Steam" { "apps" '
                '{ "42" { "Playtime" "15" } } } } } }'
            )
            games = gaming.steam_games([(root, "native"), (root, "native")])
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["name"], 'A "Game"')
        self.assertEqual((games[0]["id"], games[0]["minutes"], games[0]["last"]),
                         ("steam:42", 15, 12))

    def test_profile_and_arguments_remain_separate(self):
        with patch.object(gaming, "state", return_value={"settings": {"steam:42": {"profile": "eco"}}}):
            self.assertEqual(gaming.managed("steam:42", ["a game", "a; b"]),
                             ["nova-run", "--profile", "eco", "--game", "--", "a game", "a; b"])
        with self.assertRaises(ValueError):
            gaming.settings_for({"hotkey": "Super_L+g;malformed"})

    def test_effects_restored_when_game_fails(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(gaming, "CONFIG", Path(tmp)), \
                patch.dict(gaming.os.environ, {"XDG_SESSION_TYPE": "wayland"}), \
                patch.dict("sys.modules", {"fcntl": Mock()}), \
                patch.object(gaming.subprocess, "check_output", return_value="true false 0.8"), \
                patch.object(gaming.subprocess, "run") as command:
            with self.assertRaises(RuntimeError):
                with gaming.lowered_effects(True):
                    raise RuntimeError("game failed")
            self.assertEqual(command.call_args.args[0],
                             ["nova-appearance", "restore", "true", "false", "0.8"])


if __name__ == "__main__":
    unittest.main()
