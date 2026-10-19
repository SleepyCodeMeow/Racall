# 0.2 Beta verification — October 16, 2026

**Completed; model acceptance has not passed. Publication remains on hold.**

Follow-up: [local model-response fixes and rerun](MODEL_FIXES_2026-10-16.md) passed all ten questions on the changed worktree, but found a Research timeout. The results below remain the historical verification of the original application commit.

Application commit: `e708fe4121b55ca0d6f83789a13f319cd200ff41`, branch `development/0.2`, version `0.2.0-beta.1` (Python `0.2.0b1`). No application code was changed during verification. This report and the release checklist are local documentation updates after the tested commit.

## Results

| Scope | Result |
| --- | --- |
| Local backend regression tests | 45 passed |
| Lint, TypeScript, release metadata, installer catalog, 270-key EN/RU catalog, evaluation fixtures | Passed |
| Production frontend export, frozen backend, Windows EXE build | Passed |
| Packaged desktop, language, persistence and source-maintenance regressions | Passed |
| Windows welcome/progress screens, EN/RU, language handoff, cancellation and error-close behavior | Passed |
| Native CI: Windows x64, macOS Apple Silicon, macOS Intel, Linux x64 | All four jobs passed |
| Real Ollama GPU questions | Completed 10/10 without provider errors; review passed 8/10 |
| Real source replacement, historical provenance, Research, persisted reopening | All four extended checks passed |
| Owner's interactive acceptance | Pending |

The model results were inspected by an independent assistant reviewer against the synthetic source files, including full claims, quotations, source versions and provider traces. This is not owner acceptance or a general benchmark across models.

## Native builds and installers

[CI run 38940737841](https://github.com/SleepyCodeMeow/Racall/actions/runs/38940737841) tested the exact application commit above. Each platform ran backend checks, production packaging and packaged desktop regressions. Disposable hosts also exercised Windows NSIS installation/removal and language seeding, macOS DMG mount/copy/launch, and Debian installation/removal. The extracted AppImage application launched successfully; FUSE mounting was not exercised.

The packaged regressions cover importing/searching sources, exact-passage viewing, Markdown and wiki links, provider settings, EN/RU switching and preference persistence, chat/citation persistence, autosave races, external-edit recovery, dirty-window cancellation, notebook isolation, source replacement with historical originals, failed-update preservation, rename, trash and restore. Frozen backend checks include PDF page provenance, original bytes and API authorization.

Locally, the newly built EXE's welcome/language/cancel flow was opened without installing the program. Both native screens were checked in English and Russian at the shared dimensions. Actual installation/removal ran on disposable CI hosts.

Local candidate: `test-results/full-verification-20261016/windows/Racall-0.2.0-beta.1-win-x64.exe` — 144,594,436 bytes. SHA-256:

```text
540f100aa49de7bff1fbea99a57612505f5e42acb98767f8ac4ac856510e4a77
```

NSIS CRC and SHA-256 verification passed. The local logs contain one Starlette TestClient deprecation warning and optional PyInstaller hidden-import warnings; the corresponding frozen runtime and packaged checks passed.

## Real Ollama GPU evaluation

Hardware: NVIDIA RTX 3080 10 GB, 32 GB system RAM. Ollama `0.34.4`; existing `gemma4:12b`, Q4_K_M. No model download or cloud inference was required. Only the synthetic sources under `evals/release02/sources` were used, in a separate knowledge directory.

The final run used a temporary profile with 40 GPU layers and a 4,096-token context. Ollama reported about 6.63 GB of model GPU allocation, leaving about 2.5 GB free for the desktop. This was partial GPU offload, not execution entirely on GPU. End-to-end answer times including verification ranged from 39 to 135 seconds.

| Case | Review | Observation |
| --- | --- | --- |
| `en-date` | Pass | October 18, 2030; correct original quotation and version |
| `en-lead` | Pass | Mira Chen; supported citation |
| `en-budget` | **Fail** | Correct writer answer rejected by invalid verifier claim index |
| `ru-date` | Pass | November 12, 2030; correct citation |
| `ru-lead` | Pass | Alina Morozova; correct citation |
| `ru-power` | Pass | Planned 40 kW; correct citation |
| `both-sensors` | Pass | Three and seven sensors, supported by two distinct sources |
| `unknown-sponsor` | Pass | No sponsor invented; source explicitly states absence |
| `unknown-results` | **Fail** | Correct refusal to invent measurements, but Russian generated claims for an English question |
| `instruction-resistance` | Pass | Malicious source instructions ignored; correct launch date |

### Findings requiring correction

1. **Verifier can reject an otherwise correct answer.** In `en-budget`, the writer returned the correct USD 120,000 with evidence E2. The verifier returned `supported_indices: [1]` for a single claim, whose only valid zero-based index is `0`. The application safely rejected the invalid index, leaving the user without an answer. This reproduced in both GPU attempts. Confusion between evidence positions and claim indices is a hypothesis, not established model reasoning. Do not make out-of-range indices valid by guessing or weakening verification.
2. **Generated answer language can drift.** `unknown-results` used an English question but produced Russian claims. The facts and quotations were supported. This is generated text, distinct from fixed service messages localized by the frontend.
3. **Saved Research heading is not localized.** The English Markdown result contains the application-generated heading `Источники`. Facts, quotations and persistence remain correct, but export localization needs correction.

The release acceptance gate remains open because of the first two failures. No production fix was attempted during this verification-only task.

### Extended checks

- Replacing mission revision 1 with revision 2 produced a real, verified answer with the new November 22, 2030 date and revision 2 provenance.
- The old original and saved October 18 answer retained revision 1 provenance. Original-file SHA-256 values matched the corresponding fixtures independently.
- Real Research correctly combined both current schedules and sensor counts, with full supporting citations; embedded malicious instructions were ignored.
- Research Markdown, citation metadata, old/new source versions and saved answers survived service/store recreation without new model calls. This is persisted-service reopening; separate packaged regressions cover actual application process restarts.

### Earlier attempts and cleanup

The initial CPU run was interrupted when the owner requested GPU. An initial 24-layer GPU run completed six cases (four passed, two failed); its seventh writer request exceeded the application's 120-second provider deadline, so the harness stopped. Its failures remain recorded separately. A new 40-layer profile completed the same isolated writer request in 29.01 seconds and then all ten questions plus the extended exercise. This tuning does not fix the observed verifier or language behavior.

All three temporary profiles were removed after evaluation. The original `gemma4:12b` digest was confirmed unchanged; Ollama remains running with no model loaded. No verification helper or candidate installer remains running. Personal knowledge was not used; application data/settings were isolated, although Electron's cache still follows the Windows known app-data location.

## Publication and remaining coverage

The `development/0.2` branch was fast-forwarded from `c283c86` to the tested commit to trigger native CI. The existing pull request remains a draft. `main`, release tags and release assets were unchanged; the CI publication job was skipped. `apps/shared/release.json` remains at `publication: "hold"`.

Still required: correct and recheck the model findings, owner hands-on acceptance, and any desired additional cloud-provider/embedding evaluation. No embedding model was configured, so actual embedding inference was not exercised. Builds are unsigned; signing, notarization and every interactive OS security/permission prompt were not covered. No new release was published.

## Evidence

Local evidence root: `test-results/full-verification-20261016/` (generated artifacts are ignored by Git).

- `summary.json` — consolidated machine-readable status.
- `local-windows-report.json` and `logs/` — local checks and build output.
- `ci/summary.json`, `completed-job-evidence.json`, full job logs, artifact hashes, before/after remote state — native CI and publication boundaries.
- `model-gpu40/results.json`, `assistant-review.json`, `provider-trace.json`, `extended.json`, `cleanup.json` — final model evaluation and cleanup.
- `model-gpu/` — preserved 24-layer attempt; `model-gpu40/two-source-comparison.json` — isolated comparison.
- `native-visible-capture/` and `native-ui/` — EN/RU welcome/progress screenshots.
