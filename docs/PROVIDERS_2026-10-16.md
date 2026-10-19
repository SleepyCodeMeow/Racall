# Provider connections — October 16, 2026

**Implemented and locally verified for the unpublished 0.2 Beta worktree.** Four primary choices are OpenAI, Claude, Ollama and llama.cpp. Ollama has separate Local/Cloud API profiles. The existing custom OpenAI-compatible connection remains accessible. Version and publication policy are unchanged.

## Behavior

- Answer URL/model profiles survive provider switches and full application restarts. Unsaved API-key drafts stay with their connection; only the active answer/embedding keys are saved, with a notice for other pending drafts.
- Claude uses native Anthropic Messages with top-level system instructions, `x-api-key`, API version `2023-06-01` and a 4,096-token output budget. Other choices use the shared OpenAI-compatible Chat Completions transport.
- Both protocols retain 300-second total, 120-second idle and 15-second connection bounds. Only a complete JSON object from a normally finished response reaches the existing writer/verifier/citation workflow. Tool calls, refusals, token-limit interruptions and truncated responses fail safely. Reasoning is not answer content.
- Embeddings have an independent HTTP provider/URL/model. They can remain local while Claude answers remotely. Switching only the answer provider preserves compatible vectors; a blank embedding model uses keyword search.
- Legacy flat settings are projected in memory without rewriting the original file. Saving upgrades to profiles and preserves the old custom connection. Historical embedding identities and canonical keychain lookups, including legacy trailing-slash behavior, remain compatible.
- New cloud environment keys are provider-scoped; local Ollama/llama.cpp do not inherit them. Keys use OS secret storage keyed by the canonical URL, never the settings JSON or GET response. Different explicitly supplied keys for one shared URL are rejected before any write.

Modules are separate: `provider_settings.py`, `provider_factory.py`, the native Claude adapter/parser and individual UI provider/embedding components. [Code map](CODE_MAP.md) · [English setup](PROVIDERS.md) · [Russian setup](PROVIDERS.ru.md).

## Executed checks

| Check | Result |
| --- | --- |
| Backend suite | **287 passed**, one existing Starlette deprecation warning |
| Ruff, TypeScript, release metadata, fixture validation | Passed |
| EN/RU catalog | **299 keys**, parity, placeholders and new diagnostics passed |
| Production web and frozen Python builds | Passed |
| New Windows x64 unpacked app | Built with Electron 44.4.5, publication disabled |
| Full packaged suite | Desktop, languages/installer seed, provider settings, persistence, maintenance, PDF/FTS/citation/original/authentication and both provider protocols passed |
| Provider settings UI | Four choices, isolated key drafts, Local/Cloud persistence, independent embeddings, full restart, EN/RU and old settings migration passed; no model requests or keychain writes |
| Frozen native protocol exercise | All five explicit profiles performed planner/writer/critic through owned loopback HTTP fixtures; exact source/version citations, saved Research/Markdown/memory and restart reopening passed |
| Broken Claude stream | Missing terminal event produced a safe HTTP 400; no partial answer, secret echo or automatic verifier request |
| Visual inspection | Fresh EN/RU settings screenshots inspected; no live model or user knowledge used |

The protocol exercise made 15 successful deterministic completion calls and one intentionally truncated call. Child processes used synthetic provider-scoped keys and the null keyring backend. Header checks distinguish Anthropic from Bearer-authenticated Chat Completions and verify that the desktop session token is not forwarded. Reopening saved sessions after a frozen-process restart made no additional completion request.

Independent reviews found three issues that were fixed before final verification: conflicting keys for one URL, legacy trailing-slash credential lookup and explicit OpenAI refusals accompanying otherwise valid JSON. Regression tests cover each. The initial desktop-provider harness also expected the wrong Russian word (`Облако` instead of `Облачное подключение`); its expectation was corrected and the complete packaged suite reran successfully. Initial evidence is retained.

Raw logs, final source hashes and snapshots are in ignored `test-results/providers-20261016/`; provider desktop artifacts are in `test-results/providers-desktop-1792180103618/`, and the frozen protocol results in `test-results/provider-bundle-5c9e663ee16b/`. The fresh executable is `test-results/providers-20261016/windows/win-unpacked/Racall.exe`. No installer was installed.

## Limits and release gates

No live OpenAI, Anthropic or Ollama Cloud account was used, and no actual llama.cpp server/model was installed or started. Deterministic protocol tests prove transport/routing behavior, not provider account access, availability or answer quality. The [earlier real Ollama run](RESEARCH_TIMEOUT_2026-10-16.md) predates this profile update; final provider/model acceptance remains separate.

OpenAI/Anthropic connections use each user's API key, not a Claude Code/Codex CLI login or a bundled account. API usage may incur provider charges. Local Ollama can itself proxy cloud model requests; its localhost address alone is not an offline guarantee. Racall does not automatically download weights, start servers or fall back to cloud inference.

The new profiles format is not readable by older application versions. Back up the knowledge directory before upgrading. Saved keys are shared by connections with the same API URL; keys for different accounts at one endpoint are not separate profiles in the keychain.

Fresh native CI for Windows/Linux/macOS on the final source revision, live provider/model checks and owner interactive review remain open. The older four-platform CI covers the earlier committed application. HEAD remains `e708fe4121b55ca0d6f83789a13f319cd200ff41` on `development/0.2`, with uncommitted local changes. No commit, push, tag, release, model download or personal settings migration was performed. `publication` remains **hold**.
