"""Text-only streaming providers. No automatic tools or model downloads."""
import ipaddress
import json
import re
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


DEFAULTS = {
    "ollama": "http://127.0.0.1:11434",
    "compatible": "",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
}
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def endpoint(provider, custom):
    if provider not in DEFAULTS:
        raise ValueError("Unknown provider.")
    value = (custom if provider in {"ollama", "compatible"} and custom else DEFAULTS[provider]).strip()
    parts = urlsplit(value)
    if not parts.hostname or parts.username is not None or parts.query or parts.fragment:
        raise ValueError("Enter an endpoint without credentials, a query or a fragment.")
    try:
        local = ipaddress.ip_address(parts.hostname).is_loopback
    except ValueError:
        local = parts.hostname == "localhost"
    if provider == "ollama" and not local:
        raise ValueError("Local Ollama requires a loopback address.")
    if parts.scheme != "https" and not (parts.scheme == "http" and local):
        raise ValueError("Use HTTPS for a non-local endpoint.")
    _ = parts.port
    return value.rstrip("/"), local


def opener(local):
    handlers = [NoRedirect()]
    if local:
        handlers.append(ProxyHandler({}))
    return build_opener(*handlers)


def request(config, key, messages):
    provider = config["provider"]
    base, local = endpoint(provider, config["endpoint"])
    model = config["model"]
    if not MODEL.fullmatch(model):
        raise ValueError("Enter a valid model identifier.")
    headers = {"Content-Type": "application/json"}
    if provider == "ollama":
        suffix = "/api/chat"
        body = {"model": model, "messages": messages, "stream": True, "keep_alive": "30s",
                "options": {"num_predict": 2048}}
    elif provider == "anthropic":
        suffix = "/messages"
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        body = {"model": model, "messages": messages, "max_tokens": 2048, "stream": True}
    elif provider == "gemini":
        suffix = f"/models/{quote(model.removeprefix('models/'), safe='')}:streamGenerateContent?alt=sse"
        headers["x-goog-api-key"] = key
        body = {"contents": [{"role": "model" if item["role"] == "assistant" else "user",
                              "parts": [{"text": item["content"]}]} for item in messages],
                "generationConfig": {"maxOutputTokens": 2048}}
    else:
        suffix = "/chat/completions"
        if key:
            headers["Authorization"] = "Bearer " + key
        body = {"model": model, "messages": messages, "stream": True}
        if provider == "openai":
            body["stream_options"] = {"include_usage": True}
    return opener(local).open(Request(base + suffix, json.dumps(body).encode(), headers), timeout=35)


def decode(provider, data):
    if data.get("error") or data.get("type") == "error":
        raise ValueError("The provider reported an error. Check the model and credentials.")
    if provider == "ollama":
        usage = {key: data[key] for key in ("prompt_eval_count", "eval_count") if key in data}
        return data.get("message", {}).get("content", ""), usage
    if provider == "anthropic":
        usage = data.get("usage") or data.get("message", {}).get("usage") or {}
        delta = data.get("delta", {})
        return (delta.get("text", "") if delta.get("type") == "text_delta" else ""), usage
    if provider == "gemini":
        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        return "".join(part.get("text", "") for part in parts if not part.get("thought")), data.get("usageMetadata", {})
    choices = data.get("choices", [])
    return (choices[0].get("delta", {}).get("content") or "" if choices else ""), data.get("usage") or {}


def stream(config, key, messages):
    with request(config, key, messages) as response:
        while raw := response.readline(1_048_577):
            if len(raw) > 1_048_576:
                raise ValueError("Provider returned an oversized stream event.")
            line = raw.decode().strip()
            if config["provider"] != "ollama":
                if not line.startswith("data:"):
                    continue
                line = line[5:].strip()
            if line == "[DONE]":
                return
            if line:
                yield decode(config["provider"], json.loads(line))


def ollama(config, route, payload=None, method=None):
    base, local = endpoint("ollama", config["endpoint"])
    data = None if payload is None else json.dumps(payload).encode()
    with opener(local).open(Request(base + route, data, {"Content-Type": "application/json"},
                                    method=method), timeout=8) as response:
        raw = response.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("Ollama returned an oversized response.")
    return json.loads(raw) if raw else {}


def validate(config, key):
    provider = config["provider"]
    if provider == "ollama":
        ollama(config, "/api/version")
        return
    base, local = endpoint(provider, config["endpoint"])
    headers = {}
    if provider == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    elif provider == "gemini":
        headers["x-goog-api-key"] = key
    elif key:
        headers["Authorization"] = "Bearer " + key
    with opener(local).open(Request(base + "/models", headers=headers), timeout=8) as response:
        response.read(1)
