"""Explicit, per-user installation of the official Ollama Linux runtime."""
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def install(destination):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("The optional runtime installer supports NovaOS amd64.")
    if destination.exists():
        raise ValueError("A Nova-managed Ollama runtime is already installed.")
    if not shutil.which("zstd"):
        raise ValueError("Install Zstandard tools from Nova Store first.")
    metadata = Request("https://api.github.com/repos/ollama/ollama/releases/latest",
                       headers={"User-Agent": "NovaOS", "Accept": "application/vnd.github+json"})
    with urlopen(metadata, timeout=15) as response:
        release = json.load(response)
    asset = next((entry for entry in release["assets"]
                  if entry["name"] == "ollama-linux-amd64.tar.zst"), None)
    if not asset or not re.fullmatch(r"sha256:[a-f0-9]{64}", asset.get("digest") or ""):
        raise ValueError("The official asset or its published SHA-256 is unavailable.")
    url = asset["browser_download_url"]
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "github.com" or not parts.path.startswith(
            "/ollama/ollama/releases/download/"):
        raise ValueError("Unexpected Ollama release asset URL.")
    size = int(asset["size"])
    if size <= 0 or size > 5 * 2**30:
        raise ValueError("Unexpected Ollama archive size.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < size * 3:
        raise ValueError("Insufficient free space for download and extraction.")
    print(f"Official Ollama {release['tag_name']} runtime download: {size / 2**30:.2f} GiB.")
    if input("Install for this user [y/N]? ").strip().lower() != "y":
        return
    with tempfile.TemporaryDirectory(prefix="ollama-", dir=destination.parent) as working:
        archive = Path(working) / "runtime.tar.zst"
        digest = hashlib.sha256()
        downloaded = 0
        next_report = 128 * 2**20
        with urlopen(url, timeout=35) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                downloaded += len(chunk)
                if downloaded > size:
                    raise ValueError("Ollama download exceeded its published size.")
                digest.update(chunk)
                output.write(chunk)
                if downloaded >= next_report:
                    print(f"{downloaded / size:.0%} downloaded", flush=True)
                    next_report += 128 * 2**20
        if downloaded != size or "sha256:" + digest.hexdigest() != asset["digest"]:
            raise ValueError("The Ollama download failed the published size or checksum check.")
        stage = Path(working) / "runtime"
        stage.mkdir()
        with subprocess.Popen(["zstd", "-dc", str(archive)], stdout=subprocess.PIPE) as decoder:
            try:
                with tarfile.open(fileobj=decoder.stdout, mode="r|") as packaged:
                    packaged.extractall(stage, filter="data")
            except BaseException:
                decoder.terminate()
                raise
            finally:
                decoder.stdout.close()
            if decoder.wait():
                raise ValueError("Could not decompress the Ollama archive.")
        binary = stage / "bin/ollama"
        if not binary.is_file() or binary.is_symlink():
            raise ValueError("The official archive did not contain the expected executable.")
        stage.rename(destination)
    print("Installed. Start the managed local server from Nova AI.")
