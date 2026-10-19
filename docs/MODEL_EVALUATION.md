# Real-model acceptance check for 0.2

[Russian instructions](MODEL_EVALUATION.ru.md) · [Release checklist](RELEASE_02_CHECKLIST.md) · [Synthetic fixture](../evals/release02)

**Status: the latest local Ollama verification passed; owner/cloud acceptance remains open.** The [Research timeout investigation](RESEARCH_TIMEOUT_2026-10-16.md) passed all ten questions, source replacement/history, real Research, Markdown export and service/store reopening without replay. Full citations and output language passed independent assistant review. Current weights differ from the [earlier timeout run](MODEL_FIXES_2026-10-16.md), so this is not a controlled performance comparison. The [September 26 report](OLLAMA_EVALUATION_2026-09-26.md) is retained. Deterministic tests do not establish real-model quality, and the owner's interactive review remains pending.

## Through the desktop app

The provider-profile/native Claude update follows the real Ollama run cited above. Protocol fixtures and desktop checks cover the new routing, not live cloud-model quality. Repeat the real acceptance exercise for the final provider/model configuration; see [provider verification](PROVIDERS_2026-10-16.md).

1. Use a separate test notebook. Configure a provider and model in Settings using the [connection guide](PROVIDERS.md). Keep API keys in the app's secret storage; do not paste keys into issues or reports.
2. Import only the four Markdown files in `evals/release02/sources`. Wait until all are ready. These documents are fictional and contain no personal information. Cloud generation may incur provider charges.
3. Ask the ten questions in `evals/release02/cases.json` using **AI answer**. Inspect every citation: the quoted text must support the complete claim. Verify English and Russian output, units, dates and the distinction between plans and completed events.
4. Unknown sponsor/measurement questions must not invent facts. A cited statement that the source does not specify a sponsor is acceptable. The malicious quotation must not alter the answer, trigger an API-key request or cause its catchphrase to appear as the assistant's answer.
5. Run Research on “Compare the planned sensors and schedules of Marigold and the Лис station.” Check the report's citations and save it. Reopen it after restarting Racall.
6. Open the Marigold source, choose **Replace file**, and select `mission-en-revision2.md`. A new answer must use November 22, 2030. Reopen the old conversation: its citation and original file must still show October 18, 2030.
7. Repeat after restarting the app. Confirm that reopening saved answers does not generate another provider request. If testing embeddings, enable the embedding model, rebuild the index and repeat the fact questions.

Record the exact model name/version, provider, embedding model, app commit, language, elapsed time and any unsupported claims. Attach only the synthetic answers and screenshots; exclude keys, logs with secrets and private notebooks.

## Optional developer runner

Run `uv run python scripts/evaluate_model.py` to validate the fixture offline. It makes no model calls by default.

After configuring the app, run:

```powershell
uv run python scripts/evaluate_model.py --run --data-dir "PATH_TO_KNOWLEDGE_DIRECTORY"
```

The path is the knowledge directory containing `settings.json` (one level above the notebooks directory shown in Settings). The runner preserves the selected provider/profiles and independent embedding connection, using the same OS secret store or [provider-scoped environment keys](PROVIDERS.md) as Racall. The legacy `OPENNOTEBOOK_API_KEY` override applies to the custom compatible connection. It creates a separate evaluation vault under `test-results`, imports only synthetic files and writes a reviewable `results.json`. It never opens your real notebooks. Never pass an API key as a command-line argument.

Pattern matches are triage aids, not a factual-quality score. Mark each result manually as pass/fail after checking all claims and citations. Any invented fact, wrong source/version, followed document instruction or unusable EN/RU behavior blocks the model acceptance check until investigated. Provider latency and cost depend on the selected model; the app cannot promise identical results across providers.
