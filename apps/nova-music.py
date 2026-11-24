#!/usr/bin/python3
"""SQLite music library and private mpv JSON IPC client."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname


DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "nova-music"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "nova-music"
AUDIO = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".aiff", ".wma", ".oga"}
RADIO = {
    "Groove Salad": "https://ice5.somafm.com/groovesalad-128-mp3",
    "Drone Zone": "https://ice.somafm.com/dronezone",
}
PAGE = 40


def library():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(DATA / "library.sqlite3", timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
            artist TEXT NOT NULL, album TEXT NOT NULL, liked INTEGER NOT NULL DEFAULT 0,
            played INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS membership (
            playlist INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
            track INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
            UNIQUE(playlist, track));
        CREATE INDEX IF NOT EXISTS tracks_played ON tracks(played DESC);
        CREATE INDEX IF NOT EXISTS tracks_title ON tracks(title COLLATE NOCASE);
    """)
    return db


def path_of(value):
    if value.startswith("file:"):
        parsed = urlsplit(value)
        if parsed.netloc not in {"", "localhost"}:
            raise ValueError("Select a local file.")
        return Path(url2pathname(parsed.path))
    return Path(value).expanduser()


def track_file(db, path):
    path = path.resolve()
    if not path.is_file() or path.suffix.lower() not in AUDIO:
        return None
    found = db.execute("SELECT id FROM tracks WHERE path=?", (str(path),)).fetchone()
    if found:
        return found["id"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,crypto,data", "-show_entries",
                            "format_tags=title,artist,album", "-of", "json", str(path)],
                           capture_output=True, text=True, timeout=8)
    tags = json.loads(probe.stdout).get("format", {}).get("tags", {}) if probe.returncode == 0 else {}
    tags = {name.lower(): value for name, value in tags.items()}
    return db.execute("INSERT INTO tracks(path,title,artist,album) VALUES(?,?,?,?)",
                      (str(path), tags.get("title", path.stem), tags.get("artist", ""),
                       tags.get("album", ""))).lastrowid


def browse(db, payload):
    mode = payload.get("mode", "Library")
    page = max(0, int(payload.get("page", 0)))
    search = str(payload.get("query", ""))[:200]
    filters = []
    args = []
    join = ""
    order = "tracks.title COLLATE NOCASE, tracks.id"
    if search:
        literal = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        filters.append("(title LIKE ? ESCAPE '\\' OR artist LIKE ? ESCAPE '\\' OR album LIKE ? ESCAPE '\\')")
        args.extend([literal] * 3)
    if mode == "Liked":
        filters.append("liked=1")
    if mode in {"Home", "Recent"}:
        order = "played DESC, tracks.id DESC"
        if mode == "Recent":
            filters.append("played>0")
    if mode == "Playlist":
        join = " JOIN membership ON tracks.id=membership.track"
        filters.append("membership.playlist=?")
        args.append(int(payload["playlist"]))
        order = "membership.rowid"
    where = " WHERE " + " AND ".join(filters) if filters else ""
    rows = db.execute(f"SELECT tracks.* FROM tracks{join}{where} ORDER BY {order} LIMIT ? OFFSET ?",
                      (*args, PAGE + 1, page * PAGE)).fetchall()
    return {"rows": [dict(row) for row in rows[:PAGE]], "more": len(rows) > PAGE,
            "lists": [dict(row) for row in db.execute("SELECT * FROM playlists ORDER BY name LIMIT 200")],
            "radio": list(RADIO)}


def playlist_import(db, file, name):
    target = Path(file)
    if target.stat().st_size > 2_000_000:
        raise ValueError("Playlist is too large.")
    playlist = db.execute("INSERT INTO playlists(name) VALUES(?)", (name,)).lastrowid
    for line in target.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if urlsplit(line).scheme not in {"", "file"}:
            continue
        path = path_of(line)
        track = track_file(db, path if path.is_absolute() else target.parent / path)
        if track:
            db.execute("INSERT OR IGNORE INTO membership VALUES(?,?)", (playlist, track))
    return playlist


def artwork(path):
    source = Path(path)
    if not source.is_file():
        return ""
    CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = hashlib.sha256(f"{path}:{source.stat().st_mtime_ns}".encode()).hexdigest()
    cover = CACHE / f"{key}.jpg"
    absent = CACHE / f"{key}.none"
    if not cover.is_file() and not absent.exists():
        result = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y",
                                 "-protocol_whitelist", "file,crypto,data", "-i", str(source),
                                 "-map", "0:v:0", "-frames:v", "1", "-vf", "scale=320:-2",
                                 str(cover)], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=12)
        if result.returncode != 0:
            cover.unlink(missing_ok=True)
            absent.touch()
        entries = sorted(CACHE.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in entries[512:]:
            old.unlink(missing_ok=True)
    if cover.is_file():
        cover.touch()
        return cover.as_uri()
    return ""


def ipc_path():
    return Path(os.environ["NOVA_MUSIC_SESSION"]) / "player.sock"


def mpv(commands):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(3)
        connection.connect(str(ipc_path()))
        for index, command in enumerate(commands):
            connection.sendall((json.dumps({"command": command, "request_id": index}) + "\n").encode())
        results = {}
        with connection.makefile("rb") as stream:
            while len(results) < len(commands):
                line = stream.readline()
                if not line:
                    break
                data = json.loads(line)
                if "request_id" in data:
                    results[data["request_id"]] = data
        return [results.get(index, {}) for index in range(len(commands))]


def play(path, action):
    try:
        reply = mpv([["loadfile", path, action]])[0]
        if reply.get("error") != "success":
            raise ValueError("mpv could not queue the selected file.")
    except (ConnectionError, FileNotFoundError):
        folder = ipc_path().parent
        with (folder / "player.log").open("wb") as log:
            process = subprocess.Popen([
                "mpv", "--no-config", "--no-video", "--idle=no", "--no-terminal",
                "--tls-verify=yes", "--ytdl=no", "--title=Nova Music",
                "--script=/usr/lib/mpv-mpris/mpris.so", f"--input-ipc-server={ipc_path()}",
                "--", path,
            ], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        deadline = time.monotonic() + 3
        while not ipc_path().exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.04)
        if process.poll() not in (None, 0):
            raise ValueError("mpv could not play the selected item. Check its format and availability.")


def active(db):
    names = ("path", "media-title", "pause", "time-pos", "duration", "playlist", "volume", "loop-playlist")
    try:
        values = mpv([["get_property", name] for name in names])
    except (ConnectionError, FileNotFoundError, TimeoutError):
        return {"path": "", "queue": []}
    status = dict(zip(names, (item.get("data") for item in values)))
    path = status["path"]
    row = db.execute("SELECT * FROM tracks WHERE path=?", (path,)).fetchone()
    status["title"] = row["title"] if row else status["media-title"]
    status["queue"] = (status.pop("playlist") or [])[:100]
    return status


def start_playback(db, path, action):
    play(path, action)
    # The player may expose the IPC socket before decoding the first packet.
    status = active(db)
    if not status.get("path"):
        status.update(path=path, title=Path(path).name)
    return status


def run(db, action, data):
    if action == "browse":
        return browse(db, data)
    if action in {"status", "quit"}:
        if action == "quit":
            try:
                mpv([["quit"]])
            except OSError:
                pass
            return None
        return active(db)
    if action == "import":
        count = 0
        for value in data:
            path = path_of(value)
            paths = path.rglob("*") if path.is_dir() else (path,)
            for item in paths:
                if item.suffix.lower() in AUDIO and track_file(db, item):
                    count += 1
        return count
    if action == "playlist":
        name = str(data).strip()
        if not name:
            raise ValueError("Enter a playlist name.")
        return db.execute("INSERT INTO playlists(name) VALUES(?)", (name,)).lastrowid
    if action == "playlist-import":
        return playlist_import(db, path_of(data["file"]), data["name"])
    if action == "playlist-export":
        rows = db.execute("SELECT path FROM tracks JOIN membership ON id=track WHERE playlist=? "
                          "ORDER BY membership.rowid", (int(data["id"]),))
        with path_of(data["file"]).open("w", encoding="utf-8") as output:
            output.write("#EXTM3U\n")
            for row in rows:
                output.write(Path(row["path"]).as_uri() + "\n")
        return True
    if action == "playlist-add":
        db.execute("INSERT OR IGNORE INTO membership VALUES(?,?)", (int(data["list"]), int(data["track"])))
        return True
    if action == "playlist-remove":
        db.execute("DELETE FROM membership WHERE playlist=? AND track=?",
                   (int(data["list"]), int(data["track"])))
        return True
    if action in {"play", "queue", "like", "details"}:
        row = db.execute("SELECT * FROM tracks WHERE id=?", (int(data),)).fetchone()
        if row is None:
            raise ValueError("Track not found.")
        if action == "like":
            db.execute("UPDATE tracks SET liked=1-liked WHERE id=?", (row["id"],))
            return None
        if action == "details":
            lyrics = ""
            for extension in (".lrc", ".lyrics.txt"):
                sidecar = Path(row["path"]).with_suffix(extension)
                if sidecar.is_file():
                    with sidecar.open(encoding="utf-8", errors="replace") as source:
                        lyrics = source.read(60_000)
                    break
            return {"art": artwork(row["path"]), "lyrics": lyrics}
        return start_playback(db, row["path"], "replace" if action == "play" else "append-play")
    if action == "played":
        db.execute("UPDATE tracks SET played=? WHERE path=?", (int(time.time()), str(data)))
        return None
    if action == "radio" or action == "stream":
        url = RADIO.get(data, data) if isinstance(data, str) else ""
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None:
            raise ValueError("Enter a direct, authorized HTTPS audio stream.")
        return start_playback(db, url, "replace")
    controls = {
        "pause": ["cycle", "pause"], "next": ["playlist-next"], "previous": ["playlist-prev"],
        "shuffle": ["playlist-shuffle"], "repeat": ["cycle-values", "loop-playlist", "inf", "no"],
        "stop": ["stop"],
    }
    if action == "volume":
        command = ["set_property", "volume", min(100, max(0, float(data)))]
    elif action == "seek":
        command = ["seek", max(0, float(data)), "absolute"]
    elif action == "select-queue":
        command = ["set_property", "playlist-pos", max(0, int(data))]
    elif action == "remove-queue":
        command = ["playlist-remove", max(0, int(data))]
    elif action == "eq":
        gains = [min(12, max(-12, float(gain))) for gain in data]
        if len(gains) != 3:
            raise ValueError("Expected three EQ gains.")
        filters = ",".join(f"equalizer=f={hz}:width_type=o:w=2:g={gain}"
                           for hz, gain in zip((100, 1000, 8000), gains))
        command = ["set_property", "af", f"lavfi=[{filters}]" if any(gains) else ""]
    else:
        command = controls.get(action)
    if command is None:
        raise ValueError("Unknown music action.")
    reply = mpv([command])[0]
    if reply.get("error") not in {"success", "property unavailable"}:
        raise ValueError("Playback control failed: " + str(reply.get("error", "player closed")))
    return active(db)


def main():
    if os.geteuid() == 0:
        raise SystemExit("Run as the desktop user.")
    try:
        action, encoded = sys.argv[1:]
        with closing(library()) as db, db:
            result = run(db, action, json.loads(unquote(encoded)))
        print(json.dumps(result))
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError, KeyError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
