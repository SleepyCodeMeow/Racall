# Apps, models and appearance

[Русская инструкция](WORKBENCH.ru.md) · [Provider setup](PROVIDERS.md) · [Code map](CODE_MAP.md)

Racall keeps a compact sidebar and a quiet chat canvas, with the orange raccoon brand. Settings offers **Light**, **Dark** and **System** appearance. The choice is saved in the knowledge profile's `appearance.json`, independent of language and provider credentials. System mode follows device appearance changes; Electron keeps its native window frame.

## Models beside the message box

Open the model button beside Send. Choose a saved connection, search its available models, and select one. This changes the answer model only; embeddings and other connection profiles stay separate. Connection settings remains available for URLs and credentials. A manual model ID is supported when a server cannot list models.

The catalog comes from the selected provider, not a bundled list of names: Ollama's native `/api/tags`, Claude's native `/models`, or an OpenAI-compatible `/models` endpoint. Opening or selecting a model does not start inference. Cloud access still requires the relevant account, key and provider permissions.

For **local Ollama**, expand **Enter model ID**, enter the exact library name, choose **Download with Ollama**, then confirm. This is a real streamed `/api/pull` request to the saved loopback Ollama connection. Progress shows the **current layer**, not a claimed percentage for the entire model. Downloading does not run or automatically select the model. After success, the catalog refreshes so it can be selected explicitly.

Cancel closes Racall's download request. Ollama may keep cached partial files; another client may still be downloading the same blob. Racall does not kill the daemon or delete model files. Restarting Racall marks unfinished work as interrupted and waits for another explicit download request. Cloud models run remotely; Racall does not download their weights.

## Apps

Apps contains fixed Ollama launch commands for Claude Code, Codex CLI, OpenCode, Cline, Copilot CLI, Qwen Code, Droid and Pi. Clicking an entry **copies** a command such as `ollama launch claude` and shows it in a notification at the top right. Paste it into a terminal to run it. The command may initiate the tool's own setup and sign-in; Ollama and the selected tool are prerequisites. Racall does not silently execute commands or install software.

If copying fails, Racall displays the command in a selectable, read-only field. Copy it manually and paste it into your terminal. A failed attempt clears the previous success notification.

These external coding tools are distinct from the model providers used for Racall answers, and from notebook-scoped MCP access under Connect.

## Verification

`npm run test:workbench` exercises the interface against its own isolated loopback fixture. It must never contact a user's Ollama service or cloud account. `npm run test:packaged` includes it along with provider, persistence, language, maintenance and frozen-service checks. See [the current verification report](WORKBENCH_2026-10-17.md) for the tested build and remaining boundaries.

Primary protocol/command references: [Ollama launch](https://docs.ollama.com/cli), [Claude Code](https://docs.ollama.com/integrations/claude-code), [Codex](https://docs.ollama.com/integrations/codex), [model tags](https://docs.ollama.com/api/tags), [model pull](https://docs.ollama.com/api/pull), [Ollama Cloud](https://docs.ollama.com/cloud), [Claude models](https://platform.claude.com/docs/en/api/models/list), [OpenAI models](https://developers.openai.com/api/reference/resources/models/methods/list).
