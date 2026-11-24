"""Exercise streaming adapters, action approval, credential plumbing and cancellation."""
from contextlib import closing
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "apps/ai"
sys.path.insert(0, str(AI))
spec = importlib.util.spec_from_file_location("nova_ai", AI / "nova-ai.py")
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)


class TestAI(unittest.TestCase):
    def test_provider_transport_and_streaming(self):
        with self.assertRaises(ValueError):
            ai.providers.endpoint("ollama", "https://example.com")
        with self.assertRaises(ValueError):
            ai.providers.endpoint("compatible", "http://example.com")
        self.assertEqual(ai.providers.endpoint("compatible", "http://127.0.0.1:9988/v1")[1], True)
        cases = {
            "ollama": {"message": {"content": "Hi"}, "eval_count": 3},
            "compatible": {"choices": [{"delta": {"content": "Hi"}}]},
            "openai": {"choices": [{"delta": {"content": "Hi"}}], "usage": {"total_tokens": 7}},
            "anthropic": {"delta": {"type": "text_delta", "text": "Hi"}},
            "gemini": {"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]},
        }
        for provider, body in cases.items():
            prefix = b"" if provider == "ollama" else b"data: "
            stream = io.BytesIO(prefix + json.dumps(body).encode() + b"\n")
            with self.subTest(provider=provider), patch.object(ai.providers, "request", return_value=stream):
                self.assertEqual(list(ai.providers.stream({"provider": provider}, "", []))[0][0], "Hi")
        with self.assertRaises(ValueError):
            ai.providers.decode("openai", {"error": {"message": "secret response"}})

    def test_action_requires_single_use_grant(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ai, "DATA", Path(directory)), \
                closing(ai.db_open()) as db, patch.object(ai.actions, "execute", return_value="done") as execute:
            with self.assertRaises(ValueError):
                ai.ui(db, "apply", "no-grant")
            with self.assertRaises(ValueError):
                ai.ui(db, "preview", {"id": "volume", "argument": "10; shell"})
            with self.assertRaises(ValueError):
                ai.ui(db, "preview", {"id": "shell", "argument": "ls"})
            pending = ai.ui(db, "preview", {"id": "volume", "argument": "25"})
            execute.assert_not_called()
            self.assertEqual(ai.ui(db, "apply", pending["token"]), "done")
            execute.assert_called_once_with("volume", "25")
            with self.assertRaises(ValueError):
                ai.ui(db, "apply", pending["token"])

    def test_cancellation_and_cloud_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(ai, "DATA", path / "data"), patch.object(ai, "session", return_value=path), \
                    closing(ai.db_open()) as db, patch.object(ai.subprocess, "Popen") as launch:
                config = {"provider": "openai", "endpoint": "", "model": "model", "text": "Hello"}
                with self.assertRaisesRegex(ValueError, "Confirm sending"):
                    ai.generation(db, config)
                launch.assert_not_called()
                local = config | {"provider": "ollama"}
                with self.assertRaisesRegex(ValueError, "Confirm the selected attachment"):
                    ai.generation(db, local | {"attachment": "file:///private"})
                started = ai.generation(db, local)
                self.assertTrue(ai.cancel(started["job"]))
                with patch.object(ai.signal, "signal"), patch.object(ai.providers, "stream") as stream:
                    ai.worker(started["job"])
                stream.assert_not_called()
                result = ai.ui(db, "progress", started["job"])
                self.assertTrue(result["done"])
                self.assertEqual(result["error"], "Generation stopped.")

    def test_key_goes_to_secret_service_over_stdin(self):
        config = {"provider": "openai", "endpoint": "", "model": "model"}
        prompt = subprocess.CompletedProcess([], 0, "secret-fixture\n", "")
        wallet = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(ai.shutil, "which", return_value="/usr/bin/secret-tool"), \
                patch.object(ai.subprocess, "run", side_effect=[prompt, wallet]) as command:
            self.assertTrue(ai.key_for(config, "store"))
            call = command.call_args
            self.assertNotIn("secret-fixture", call.args[0])
            self.assertEqual(call.kwargs["input"], "secret-fixture")

    def test_official_installer_checks_digest_before_downloading(self):
        release = io.BytesIO(json.dumps({"assets": [{"name": "ollama-linux-amd64.tar.zst"}]}).encode())
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(ai.ollama_install.platform, "system", return_value="Linux"), \
                patch.object(ai.ollama_install.platform, "machine", return_value="x86_64"), \
                patch.object(ai.ollama_install, "urlopen", return_value=release) as request, \
                patch.object(ai.ollama_install.shutil, "which", return_value="/usr/bin/zstd"):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                ai.ollama_install.install(Path(directory) / "runtime")
            request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
