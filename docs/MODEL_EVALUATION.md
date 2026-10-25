# Real-model acceptance checks

[Russian instructions](MODEL_EVALUATION.ru.md) · [0.3 checklist](RELEASE_03_CHECKLIST.md) · [Synthetic fixture](../evals/release02)

## Isolated 0.3 workflow evaluation

Full 0.3 model acceptance requires its own review; the historical 0.2 result below
does not certify the new workflow. Publication remains on hold. The
[0.3 fixture and review rubric](../evals/release03/cases.json) cover the original
ten questions plus selected sources/notes, follow-up history, Research, three
Studio formats, export/copy, cancellation, service restart, explicit retry and
source versions.

From the repository root, validate the fixture without contacting Ollama:

```powershell
uv run python scripts/evaluate_release03.py
uv run python scripts/evaluate_release03.py --help
```

Live requests require **all three explicit arguments**: `--run`, `--model` and a
new `--output` directory. Prepare a separate temporary Ollama alias beforehand;
the runner uses existing models and never downloads or creates one. Identify its
original tag with `--source-model` so both digests can be checked for drift:

```powershell
uv run python scripts/evaluate_release03.py --run --model "YOUR_PREPARED_ALIAS:latest" --source-model "YOUR_SOURCE_MODEL:TAG" --output "test-results/live03-my-run" --phase all
```

For the October 25 RTX 3080 10 GB exercise, the operator prepared an alias with
`num_gpu=40` and `num_ctx=4096`. These are that machine's test settings, not an
automatic recommendation for other hardware. The runner leaves alias settings,
thinking, temperature and generation limits unchanged.

Available phases are `core` (ten baseline questions), `context` (selection,
history and saved-note revisions), `studio` (Research, all three Studio formats
and material retention), `lifecycle` (queued/running cancellation, restart,
retry and source replacement), or `all` in that order. Each invocation creates a
fresh isolated vault; an output directory is never reused.

The endpoint defaults to `http://127.0.0.1:11434/v1` and must remain loopback HTTP
(`--endpoint` also accepts `localhost` or `::1`). No personal vault or application
settings are opened, embeddings are disabled in the isolated vault, and the
process uses a null keyring. This exercise makes no cloud calls. Run one instance
only, without other inference clients using the test model. It permits at most
80 serial completion calls and 45 minutes; `--max-calls` and `--minutes` can lower
those bounds. Before and after successful calls, guards check available RAM
(at least 1.5 GB), NVIDIA free VRAM (at least 1,024 MiB when available), model/tag
digests and whether another model is loaded. Provider/resource failures stop the
run. RAM sampling is implemented for Windows and Linux.

To stop an active run after reviewing a bad answer, create `STOP` in its output
directory:

```powershell
New-Item -ItemType File "test-results/live03-my-run/STOP"
```

The transport checks this stop condition during completion. Cancellation closes
the local HTTP operation and prevents a late material from being saved; it does
not establish that Ollama immediately stopped GPU computation.

Review the incrementally written `results.json`, `provider-trace.json` (synthetic
prompts, responses and runtime samples), `environment.json` (source-file manifest,
digests and rubric), exported `.md` files and `isolated-knowledge/`. Every result
starts with `quality_verdict: manual_pending`. A `validated` answer, correct JSON,
matching quote offsets or passing pattern checks does **not** prove that every
claim follows from the evidence. Review complete claims, conjunctions, causes,
section titles and question premises, preserving the difference between missing
reports and missing events, and between plans and observations. Record factual
verdicts separately from contract/provenance checks. API/service reopening here
also remains separate from the owner's interactive desktop acceptance.

Alias cleanup is a separate operator step after preserving evidence: unload and
remove only the temporary alias created for this exercise, keeping original
model tags intact. The runner does not unload or delete models.

Observed results and limitations: [October 25 report](MODEL_EVALUATION_03_2026-10-25.md).

## Historical 0.2 acceptance

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
