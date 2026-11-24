"""Exercise Music and Store without running a package transaction or network request."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "apps" / f"nova-{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


music = load("music")
store = load("store")


class Music(unittest.TestCase):
    def test_metadata_search_playlist_and_history(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(music, "DATA", Path(tmp) / "data"):
            track = Path(tmp) / "track.wav"
            track.write_bytes(b"fixture")
            probe = subprocess.CompletedProcess([], 0, json.dumps({
                "format": {"tags": {"title": "Song 100%", "artist": "Artist", "album": "Album"}}
            }), "")
            with patch.object(music.subprocess, "run", return_value=probe):
                db = music.library()
                try:
                    identifier = music.track_file(db, track)
                    self.assertEqual(music.track_file(db, track), identifier)
                    self.assertEqual(len(music.browse(db, {"query": "Album"})["rows"]), 1)
                    self.assertEqual(music.browse(db, {"query": "_"})["rows"], [])
                    music.run(db, "like", identifier)
                    self.assertEqual(len(music.browse(db, {"mode": "Liked"})["rows"]), 1)
                    music.run(db, "played", str(track.resolve()))
                    self.assertTrue(music.browse(db, {"mode": "Recent"})["rows"][0]["played"])
                    playlist = music.run(db, "playlist", "A mix")
                    music.run(db, "playlist-add", {"list": playlist, "track": identifier})
                    exported = Path(tmp) / "mix.m3u8"
                    music.run(db, "playlist-export", {"id": playlist, "file": str(exported)})
                    # The importer accepts file URLs and ignores untrusted remote playlists.
                    exported.write_text(exported.read_text() + "https://example.invalid/track.mp3\n")
                    second = music.run(db, "playlist-import", {"file": str(exported), "name": "Copy"})
                    self.assertEqual(len(music.browse(db, {"mode": "Playlist", "playlist": second})["rows"]), 1)
                    with self.assertRaises(ValueError):
                        music.run(db, "stream", "file:///private")
                finally:
                    db.close()

    def test_queue_uses_native_player_and_eq_is_bounded(self):
        with patch.object(music, "mpv", return_value=[{"error": "success"}]) as ipc, \
                patch.object(music, "active", return_value={"path": "song", "queue": []}):
            music.run(None, "eq", [50, 0, -25])
            audio_filter = ipc.call_args.args[0][0][2]
            self.assertIn("g=12", audio_filter)
            self.assertIn("g=-12", audio_filter)
            music.start_playback(None, "/local/song", "append-play")
            self.assertEqual(ipc.call_args.args[0], [["loadfile", "/local/song", "append-play"]])


class Store(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(store, "CATALOG", ROOT / "apps/store-catalog.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_catalog_filters_and_paginates(self):
        first = store.browse({})
        self.assertTrue(first["more"])
        second = store.browse({"page": 1})
        self.assertTrue(second["rows"])
        matches = store.browse({"query": "gimp", "source": "apt", "category": "Graphics"})
        self.assertEqual([app["id"] for app in matches["rows"]], ["gimp"])
        with self.assertRaises(ValueError):
            store.lookup("apt", "systemd")

    def test_official_screenshot_and_consent(self):
        with patch.object(store, "command", return_value=subprocess.CompletedProcess([], 1, "", "")), \
                patch.object(store, "flathub_metadata", return_value={"screenshots": [{
                    "caption": "Publisher caption",
                    "sizes": [
                        {"width": "640", "src": "http://dl.flathub.org/unsafe.png"},
                        {"width": "624", "src": "https://dl.flathub.org/example.png"},
                    ],
                }]}):
            details = store.details("flatpak", "org.gimp.GIMP")
        self.assertEqual(details["screenshot"], "https://dl.flathub.org/example.png")
        self.assertEqual(details["caption"], "Publisher caption")
        with patch("builtins.input", return_value="n"), patch.object(store.subprocess, "run") as runner:
            self.assertEqual(store.transaction("install", "flatpak", "org.gimp.GIMP"), 0)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
