# Local Ollama evaluation — 26 September 2026

**Acceptance: not passed.** This is one local run on the synthetic 0.2 fixture, not a general benchmark of the model.

- Racall backend code: `7a73788` (unchanged in the installer-style commit `46872d7`).
- Provider: Ollama 0.34.4, local OpenAI-compatible endpoint.
- Model: `gemma4:12b`, 11.9B, Q4_K_M; digest `4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c`.
- Four synthetic Markdown sources; ten questions; keyword retrieval, no embedding model configured. The app's normal writer, evidence-ID validation and critic were exercised.
- No personal notebooks were read and no cloud model was called. Provider settings were isolated from the user's application profile.

| Cases | Outcome |
|---|---|
| English date, lead and budget; Russian lead | Four correct answers. Assistant inspection confirmed the attached quotes support the statements. |
| Russian opening date and power | No supported answer returned although the fact is in the source. Cause not established by the initial run. |
| Sensors across both sources | HTTP 500 from Ollama. |
| Unknown sponsor, unknown measurements, embedded instruction | Provider timeouts; no quality verdict can be drawn. |

The local Ollama log recorded a CUDA unknown error and runner termination during the two-source request, followed by failed GPU discovery. The reloaded model reported zero VRAM usage and a 4,096-token context. The three following calls timed out. These observations establish a provider/runtime failure; they do not establish its hardware or driver root cause. System/driver settings were not changed.

Local diagnostic data lives under the ignored `test-results/ollama-gemma4-evaluation/`: `results.json`, `reviewed-results.json` and `environment.json`. Full server logs and machine-specific diagnostics are not committed. Human review is recorded separately from assistant inspection.

Research generation, source-update answers and embeddings have not passed real-model acceptance. Restore stable local inference first, investigate the two missing Russian answers and then rerun the entire [evaluation guide](MODEL_EVALUATION.md). Keep publication on hold. A single successful request is not sufficient to clear this gate.

## Follow-up: citation identifier copying

A focused request with the correct Russian source returned the correct opening date, but the model omitted a character while copying the 64-character evidence ID (`a96e1dfd…` became `a96e1df…`). Strict validation appropriately rejected it. The diagnostic writer response took 110 seconds on the fallback runtime; a console-encoding error then stopped that diagnostic script before its critic call. The captured JSON preserves the response, and the console invocation was corrected to UTF-8.

The application now sends short request-local labels such as `E1` to both writer and critic. It restores canonical IDs and full provenance before returning/saving the answer. Unknown labels, mixed valid/invalid labels and unrecognized hashes are still rejected, with no fuzzy matching. A regression checks the mapping and source-version/quote preservation. This fixes the observed identifier-copying failure mode; it does not repair Ollama's CUDA failure or establish full model acceptance.
