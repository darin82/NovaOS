#!/usr/bin/python3
"""Optional desktop assistant with local history, streaming and explicit action grants."""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import actions
import ollama_install
import providers


DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "nova-ai"
ID = re.compile(r"[0-9a-f]{32}")
FIRST_SETTINGS = {"provider": "ollama", "endpoint": "", "model": "", "retention": 30}
BASE = Path(__file__).resolve()


def db_open():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(DATA / "history.sqlite3", timeout=8)
    db.row_factory = sqlite3.Row
    db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY, title TEXT, updated INTEGER);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY, chat TEXT REFERENCES chats(id) ON DELETE CASCADE,
            role TEXT, content TEXT, usage TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS grants(token TEXT PRIMARY KEY, action TEXT, argument TEXT, expires INTEGER);
    """)
    return db


def settings():
    file = DATA / "settings.json"
    return FIRST_SETTINGS | (json.loads(file.read_text()) if file.is_file() else {})


def atomic_json(path, payload):
    temporary = path.with_name(f".{path.name}.{uuid4().hex}")
    try:
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def checked_config(payload, require_model=True):
    config = {name: str(payload.get(name, "")) for name in ("provider", "endpoint", "model")}
    if len(config["endpoint"]) > 2048:
        raise ValueError("Endpoint too long.")
    base, local = providers.endpoint(config["provider"], config["endpoint"])
    if require_model and not providers.MODEL.fullmatch(config["model"]):
        raise ValueError("Choose or enter a model ID.")
    return config, base, local


def key_for(config, operation):
    provider = config["provider"]
    base, _ = providers.endpoint(provider, config["endpoint"])
    if provider == "ollama":
        if operation != "lookup":
            raise ValueError("Ollama does not use an API key in Nova AI.")
        return ""
    if not shutil.which("secret-tool"):
        if operation == "lookup" and provider == "compatible":
            return ""
        raise ValueError("Install libsecret-tools and unlock a desktop Secret Service wallet.")
    attributes = ["application", "nova-ai", "provider", provider, "endpoint", base]
    if operation == "store":
        entry = subprocess.run(["kdialog", "--password", "API key for " + provider],
                               capture_output=True, text=True, timeout=120)
        if entry.returncode:
            return False
        secret = entry.stdout.rstrip("\r\n")
        if not secret or "\n" in secret or len(secret) > 8192:
            raise ValueError("Enter a valid single-line API key.")
        result = subprocess.run(["secret-tool", "store", "--label=Nova AI " + provider, *attributes],
                                input=secret, capture_output=True, text=True, timeout=30)
    else:
        result = subprocess.run(["secret-tool", operation, *attributes], capture_output=True,
                                text=True, timeout=30)
    if operation == "lookup":
        if result.returncode and provider != "compatible":
            raise ValueError("No API key was found in the unlocked desktop wallet.")
        return result.stdout.rstrip("\r\n") if result.returncode == 0 else ""
    if result.returncode:
        raise ValueError("The desktop credential manager could not complete that operation.")
    return True


def session():
    path = Path(os.environ["NOVA_AI_SESSION"])
    if path.parent != Path(os.environ["XDG_RUNTIME_DIR"]) or not path.name.startswith("nova-ai."):
        raise ValueError("Invalid Nova AI desktop session.")
    return path


def job_path(identifier):
    if not isinstance(identifier, str) or not ID.fullmatch(identifier):
        raise ValueError("Invalid generation ID.")
    return session() / identifier


def send_signal(pid, expected):
    """Signal an identified same-user process without a PID-reuse race."""
    try:
        descriptor = os.pidfd_open(pid)
        try:
            root = Path(f"/proc/{pid}")
            command = root.joinpath("cmdline").read_bytes().split(b"\0")
            environment = root.joinpath("environ").read_bytes().split(b"\0")
            if root.stat().st_uid == os.getuid() and expected(command, environment):
                signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                return True
        finally:
            os.close(descriptor)
    except (OSError, ValueError):
        pass
    return False


def cancel(identifier):
    job = job_path(identifier)
    (job / "cancel").touch()
    if (job / "pid").is_file():
        pid = int((job / "pid").read_text())
        return send_signal(pid, lambda cmd, env: cmd[1:4] == [
            os.fsencode(BASE), b"worker", identifier.encode()])
    return True


def safe_attachment(url):
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
        raise ValueError("Select a local text file.")
    path = Path(unquote(parsed.path))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("The selected attachment is not a regular file.")
        content = source.read(32769)
    if len(content) > 32768 or b"\0" in content:
        raise ValueError("Attachments are limited to 32 KiB of UTF-8 text.")
    try:
        return path.name, content.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("The selected file is not UTF-8 text.") from error


def generation(db, payload):
    config, base, local = checked_config(payload)
    if not local and payload.get("cloud") is not True:
        raise ValueError("Confirm sending the conversation context to the cloud endpoint.")
    if payload.get("attachment") and payload.get("attachmentApproved") is not True:
        raise ValueError("Confirm the selected attachment before Nova AI reads it.")
    for existing in session().iterdir():
        if existing.is_dir() and ID.fullmatch(existing.name):
            if not json.loads((existing / "result.json").read_text())["done"]:
                raise ValueError("Stop or finish the current generation first.")
            shutil.rmtree(existing)
    text = str(payload.get("text", "")).strip()
    regenerate = payload.get("regenerate") is True
    chat = payload.get("chat") or uuid4().hex
    if not ID.fullmatch(chat) or len(text) > 10000 or (not text and not regenerate):
        raise ValueError("Enter a prompt of at most 10,000 characters.")
    exists = db.execute("SELECT 1 FROM chats WHERE id=?", (chat,)).fetchone()
    if regenerate and not exists:
        raise ValueError("This conversation has no response to regenerate.")
    attachment = safe_attachment(payload.get("attachment"))
    if not exists:
        db.execute("INSERT INTO chats VALUES(?,?,?)", (chat, text[:65], int(time.time())))
    if not regenerate:
        db.execute("INSERT INTO messages(chat,role,content) VALUES(?,?,?)", (chat, "user", text))
    db.execute("UPDATE chats SET updated=? WHERE id=?", (int(time.time()), chat))
    messages = [dict(row) for row in reversed(db.execute(
        "SELECT role,content FROM messages WHERE chat=? ORDER BY id DESC LIMIT 20", (chat,)).fetchall())]
    while regenerate and messages and messages[-1]["role"] == "assistant":
        messages.pop()
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("No prompt is available to regenerate.")
    remaining = 64000
    context = []
    for message in reversed(messages):
        if remaining <= 0:
            break
        content = message["content"][:min(remaining, 16000)]
        context.append({"role": message["role"], "content": content})
        remaining -= len(content)
    messages = list(reversed(context))
    if attachment:
        messages[-1]["content"] += f"\n\nUser-approved attachment {attachment[0]}:\n{attachment[1]}"
    identifier = uuid4().hex
    job = job_path(identifier)
    job.mkdir(mode=0o700)
    atomic_json(job / "request.json", {"config": config, "messages": messages, "chat": chat})
    atomic_json(job / "result.json", {"text": "", "done": False, "error": "", "usage": {}})
    db.commit()
    subprocess.Popen([sys.executable, str(BASE), "worker", identifier], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"job": identifier, "chat": chat, "endpoint": base, "local": local}


class Cancelled(Exception):
    pass


def interrupted(_signal, _frame):
    raise Cancelled


def worker(identifier):
    signal.signal(signal.SIGTERM, interrupted)
    job = job_path(identifier)
    result = {"text": "", "done": False, "error": "", "usage": {}}
    payload = json.loads((job / "request.json").read_text())
    (job / "request.json").unlink()
    (job / "pid").write_text(str(os.getpid()))
    try:
        if (job / "cancel").exists():
            raise Cancelled
        config = payload["config"]
        key = key_for(config, "lookup")
        flush = 0
        for text, usage in providers.stream(config, key, payload["messages"]):
            if (job / "cancel").exists():
                raise Cancelled
            result["text"] += text
            result["usage"].update(usage)
            if time.monotonic() - flush >= 0.18:
                atomic_json(job / "result.json", result)
                flush = time.monotonic()
            if len(result["text"]) > 120_000:
                raise ValueError("Response exceeded the local display limit.")
        if not result["text"]:
            result["error"] = "The provider returned no text."
    except Cancelled:
        result["error"] = "Generation stopped."
    except HTTPError as error:
        result["error"] = f"The provider returned HTTP {error.code}. Check your credentials, model and endpoint."
    except (OSError, ValueError, subprocess.SubprocessError, KeyError) as error:
        result["error"] = str(error)
    finally:
        # Cancellation can race with flushing the final result.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if result["text"]:
            try:
                with closing(db_open()) as db, db:
                    if db.execute("SELECT 1 FROM chats WHERE id=?", (payload["chat"],)).fetchone():
                        db.execute("INSERT INTO messages(chat,role,content,usage) VALUES(?,?,?,?)", (
                            payload["chat"], "assistant", result["text"], json.dumps(result["usage"])))
            except sqlite3.Error:
                result["error"] = "The response could not be saved to local history."
        result["done"] = True
        atomic_json(job / "result.json", result)


def server_process(stop=False):
    marker = session() / "ollama.pid"
    if stop:
        if marker.is_file():
            send_signal(int(marker.read_text()), lambda cmd, env: b"serve" in cmd
                        and any(value == os.fsencode("NOVA_AI_SESSION=" + str(session())) for value in env)
                        and Path(os.fsdecode(cmd[0])).name == "ollama")
            marker.unlink(missing_ok=True)
        return "Managed local server stopped."
    if marker.exists():
        return "A managed local server was already started for this window."
    executable = ollama_binary()
    if not executable:
        raise ValueError("Install Ollama from its official Linux instructions, then restart Nova AI.")
    with (session() / "ollama.log").open("wb") as log:
        child = subprocess.Popen([executable, "serve"], stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                 env=os.environ | {"OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_KEEP_ALIVE": "0"},
                                 start_new_session=True)
    time.sleep(0.2)
    if child.poll() is not None:
        raise ValueError("Ollama could not start. An external instance may already own port 11434.")
    marker.write_text(str(child.pid))
    return "Managed Ollama started on loopback. Models unload after a short idle hold."


def ollama_binary():
    installed = DATA / "ollama/bin/ollama"
    return str(installed) if os.access(installed, os.X_OK) else shutil.which("ollama")


def terminal(*args):
    subprocess.Popen(["konsole", "--hold", "-e", *args], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def hardware():
    ram = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                   if line.startswith("MemAvailable:"))) / 1048576
    data = shutil.disk_usage(DATA).free / 2**30
    vendors = {"0x1002": "AMD", "0x8086": "Intel", "0x10de": "NVIDIA"}
    gpus = []
    for path in Path("/sys/class/drm").glob("card*/device/vendor"):
        value = path.read_text().strip()
        if value in vendors:
            gpus.append(vendors[value])
    if ram >= 6 and data >= 4:
        recommendation = "Start with qwen2.5:1.5b or the smaller qwen2.5:0.5b."
    elif ram >= 2 and data >= 2:
        recommendation = "Start with qwen2.5:0.5b."
    else:
        recommendation = "Free RAM or storage before running a local model."
    return f"{ram:.1f} GiB available RAM · {os.cpu_count()} logical CPUs · {data:.1f} GiB free.\n" \
           f"Display GPUs: {', '.join(sorted(set(gpus))) or 'unavailable'}. Ollama selects supported acceleration.\n{recommendation}"


def ui(db, action, payload):
    if action == "settings":
        return settings()
    if action == "save-settings":
        config, _, _ = checked_config(payload, require_model=False)
        retention = int(payload["retention"])
        if not 0 <= retention <= 365:
            raise ValueError("Retention must be 0–365 days.")
        config["retention"] = retention
        atomic_json(DATA / "settings.json", config)
        return config
    if action in {"key", "clear-key"}:
        config, _, _ = checked_config(payload, require_model=False)
        return key_for(config, "store" if action == "key" else "clear")
    if action == "connect":
        config, base, local = checked_config(payload, require_model=False)
        providers.validate(config, key_for(config, "lookup"))
        return ("Local" if local else "Cloud") + " connection verified: " + base
    if action == "chats":
        retention = settings()["retention"]
        if retention:
            db.execute("DELETE FROM chats WHERE updated < ?", (int(time.time()) - retention * 86400,))
        query = "%" + str(payload)[:200] + "%"
        return [dict(row) for row in db.execute("""
            SELECT id,title FROM chats WHERE title LIKE ? OR EXISTS (
                SELECT 1 FROM messages WHERE chat=chats.id AND content LIKE ?)
            ORDER BY updated DESC LIMIT 50
        """, (query, query))]
    if action == "history":
        return [dict(row) for row in reversed(db.execute(
            "SELECT role,content,usage FROM messages WHERE chat=? ORDER BY id DESC LIMIT 100",
            (str(payload),)).fetchall())]
    if action == "delete":
        db.execute("DELETE FROM chats WHERE id=?", (str(payload),))
        return True
    if action == "export":
        parsed = urlsplit(payload["url"])
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            raise ValueError("Choose a local export destination.")
        rows = db.execute("SELECT role,content FROM messages WHERE chat=? ORDER BY id",
                          (payload["chat"],)).fetchall()
        with Path(unquote(parsed.path)).open("x", encoding="utf-8") as output:
            for row in rows:
                output.write(f"## {row['role'].title()}\n\n{row['content']}\n\n")
        return True
    if action == "generate":
        return generation(db, payload)
    if action == "progress":
        return json.loads((job_path(payload) / "result.json").read_text())
    if action == "cancel":
        return cancel(payload)
    if action == "actions":
        return [{"id": name, "title": title, "hint": hint} for name, (title, hint) in actions.ACTIONS.items()]
    if action == "preview":
        argument = actions.preview(payload["id"], payload.get("argument", ""))
        token = uuid4().hex
        db.execute("DELETE FROM grants WHERE expires < ?", (int(time.time()),))
        db.execute("INSERT INTO grants VALUES(?,?,?,?)", (token, payload["id"], argument, int(time.time()) + 120))
        return {"token": token, "text": actions.ACTIONS[payload["id"]][0] + (f"\n{argument}" if argument else "")}
    if action == "apply":
        grant = db.execute("DELETE FROM grants WHERE token=? AND expires>=? RETURNING action,argument",
                           (str(payload), int(time.time()))).fetchone()
        db.commit()
        if not grant:
            raise ValueError("This action approval expired or was already used.")
        return actions.execute(grant["action"], grant["argument"])
    if action == "performance":
        actions.launch("env", "QT_QUICK_CONTROLS_STYLE=org.kde.desktop", "qml6", "/usr/lib/novaos/Performance.qml")
        return True
    if action == "hardware":
        return hardware()
    if action in {"start-local", "stop-local"}:
        return server_process(action == "stop-local")
    if action == "models":
        config, _, _ = checked_config(payload, require_model=False)
        if config["provider"] != "ollama":
            raise ValueError("Enter a provider-supplied model ID for cloud APIs.")
        models = providers.ollama(config, "/api/tags").get("models", [])
        return [{"name": model["name"], "size": model.get("size", 0)} for model in models[:100]]
    if action == "pull":
        config, base, _ = checked_config(payload)
        binary = ollama_binary()
        if config["provider"] != "ollama" or not binary:
            raise ValueError("The local Ollama executable is required.")
        terminal("env", "OLLAMA_HOST=" + base, binary, "pull", config["model"])
        return True
    if action == "install-ollama-console":
        terminal(str(BASE), "install-ollama", "null")
        return True
    if action == "remove-model":
        config, _, _ = checked_config(payload)
        if config["provider"] != "ollama" or payload.get("confirmed") is not True:
            raise ValueError("Confirm deleting the selected local model.")
        providers.ollama(config, "/api/delete", {"model": config["model"]}, method="DELETE")
        return True
    raise ValueError("Unknown Nova AI operation.")


def main():
    os.umask(0o077)
    if os.geteuid() == 0:
        raise SystemExit("Run Nova AI as the desktop user.")
    try:
        action, value = sys.argv[1:]
        if action == "install-ollama":
            ollama_install.install(DATA / "ollama")
            return
        if action == "worker":
            worker(value)
            return
        if action == "cleanup":
            server_process(stop=True)
            directory = session()
            jobs = [path for path in directory.iterdir() if path.is_dir() and ID.fullmatch(path.name)]
            for job in jobs:
                cancel(job.name)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and any(
                    not json.loads((job / "result.json").read_text())["done"] for job in jobs):
                time.sleep(0.1)
            shutil.rmtree(directory)
            return
        with closing(db_open()) as db, db:
            result = ui(db, action, json.loads(unquote(value)))
        print(json.dumps(result))
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
