# Optional Nova AI

Open Nova Store → **Nova AI → Enable**. The ISO includes the dormant launcher payload. Enabling adds a desktop entry for the current user. Disabling removes that entry. Close any open AI windows first. History stays local until its configured retention expires or the user deletes it. Pin the app through Plasma if desired. **Super+Space** is registered when available. **Ctrl+K** opens the action palette inside the window.

## Providers

Ollama uses a loopback endpoint. Start a managed instance on demand, connect to an existing localhost server, or install the official amd64 runtime per user. The optional installer previews its size, uses the published release SHA-256, and requires Zstandard tools. It downloads no models. Refresh the local model list for actual sizes, or explicitly download or remove a selected model. The client asks Ollama to unload idle models after a short hold. External model servers retain their own service policies.

For an OpenAI-compatible service set its API base URL, normally ending in `/v1`. OpenAI, Anthropic and Gemini use their official endpoints. Choose a valid model ID for your provider. Install Secret Service tools through Nova Store and unlock a desktop credential wallet before adding a key. Nova stores credentials through Secret Service and scopes them to the selected provider and endpoint. It sends cloud context only after confirmation. A selected attachment is limited to 32 KiB of UTF-8 text and must be approved separately. Nova does not crawl directories or repositories for model context.

## System actions

Use the action palette for operational commands. Every action has a preview and a short-lived approval. The model cannot apply actions or run terminal commands. Ask the assistant to explain an error, format code, or draft a command, then review the answer before copying it. Network diagnostics read local state and remain out of the conversation unless you copy them there. Brightness changes require a compatible device, permissions, and the optional brightness utility.

- [Ollama Linux installation](https://docs.ollama.com/linux)
- [Desktop Secret Service CLI](https://manpages.debian.org/trixie/libsecret-tools/secret-tool.1.en.html)
- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [Anthropic streaming](https://platform.claude.com/docs/en/build-with-claude/streaming)
- [Gemini Generate Content](https://ai.google.dev/api/generate-content)
