# AI connections in 0.2 Beta

[Russian instructions](PROVIDERS.ru.md) · [Model evaluation](MODEL_EVALUATION.md) · [Code map](CODE_MAP.md)

Open **Settings → AI connection**, choose a provider, enter its exact model ID and save. Racall keeps a separate answer URL/model profile for each provider, including separate Ollama Local/Cloud profiles. Switching providers does not erase those profiles. The [model picker beside the message box](WORKBENCH.md) lists models from these saved connections and offers explicitly confirmed local Ollama downloads. Racall does not start inference or switch to cloud automatically.

| Choice | Default API base URL | Setup |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | Your OpenAI API key and a model supporting Chat Completions JSON output |
| Claude | `https://api.anthropic.com/v1` | Your Anthropic API key and a Messages API model ID |
| Ollama → Local | `http://127.0.0.1:11434/v1` | Start Ollama and enter a downloaded model's name from `ollama list` |
| Ollama → Cloud API | `https://ollama.com/v1` | Your Ollama API key and the exact cloud model ID from Ollama's catalog |
| llama.cpp | `http://127.0.0.1:8080/v1` | Start `llama-server` with a GGUF model and enter its served model name/alias |

Ollama's Local option connects to the installed server. That server can also forward cloud-enabled model requests after Ollama sign-in; a localhost address alone does not prove offline inference. Choose a genuinely downloaded local model for offline work. The separate Cloud API option connects directly without requiring a local Ollama installation. See [Ollama authentication](https://docs.ollama.com/api/authentication) and [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

Claude uses the native [Messages API](https://platform.claude.com/docs/en/api/messages/create), with a 4,096-token output budget. OpenAI, Ollama and llama.cpp use the shared Chat Completions transport. The selected model must return complete JSON; unsupported models, refusals, token-limit interruptions and broken streams produce an error rather than an accepted partial answer. Thinking metadata is not displayed as a cited answer. Each completion has a 300-second total deadline and 120-second read-idle timeout; Research can make multiple completions.

These are API connections. The [Apps section](WORKBENCH.md#apps) separately copies Ollama launch commands for external coding tools, including Claude Code and Codex CLI; their login is handled in the terminal by those tools. Their subscriptions do not become API credentials for Racall. OpenAI API usage has separate billing from included ChatGPT subscription usage; see [OpenAI pricing](https://learn.chatgpt.com/docs/pricing). Each user supplies their own provider access; keys are not bundled with Racall.

## Keys and privacy

Entered keys are saved in the operating system keychain, keyed by the canonical API base URL. Connections using the same URL share one saved key. Conflicting answer/embedding keys for one URL are rejected before writing settings. A blank key field keeps the existing saved key; keys are never returned by the settings API or written into `settings.json`.

Unsaved key drafts remain associated with the provider for which they were entered. Saving writes the active answer key and selected embedding key only; the interface identifies drafts belonging to another connection. Save those connections separately before leaving Settings. The availability label can also reflect a provider-scoped environment key, not only a stored key.

For development, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `OLLAMA_API_KEY` apply to their explicit cloud profiles. Saved keys take precedence. Local Ollama/llama.cpp do not inherit these cloud keys. The older `OPENNOTEBOOK_API_KEY` override remains available only to the custom/legacy OpenAI-compatible connection. Never include keys in terminal arguments, screenshots or bug reports.

Questions and retrieved passages go to the chosen answer server. Cloud inference processes them remotely. Cloud embeddings also send imported document text to the configured embedding server. Saved knowledge remains local; this does not make a cloud request local.

## Optional semantic search

Expand **Semantic search** to configure an independent HTTP embedding connection. Supported choices are OpenAI, Ollama, llama.cpp or a custom OpenAI-compatible endpoint. Claude remains available as the answer model while embeddings run elsewhere. Only the selected embedding connection is persisted; leave its model blank to keep keyword search without any embedding requests.

After changing the embedding endpoint/model, rebuild the affected notebook's index. Existing vectors are used only when their endpoint/model identity matches the active embedding connection. Switching the answer provider alone does not invalidate them.

## Existing installations and verification

Old flat URL/model/embedding settings appear as **Custom OpenAI-compatible** with their exact values. Reading them does not rewrite the file, originals, chats or citation snapshots. Saving upgrades the settings structure while retaining the old profile and embedding identity. Back up the full knowledge directory before upgrading; an older application version does not understand the new profile format.

`npm run test:providers` checks the real Electron settings screen, key-draft isolation, Local/Cloud profiles, independent embeddings, EN/RU, full restart and legacy configuration. Deterministic HTTP tests cover both native protocols; they do not establish live cloud-model quality or account access. See the [provider verification report](PROVIDERS_2026-10-16.md) for executed checks and remaining release gates.
