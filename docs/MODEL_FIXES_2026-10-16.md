# Model response fixes for 0.2 Beta — October 16, 2026

**Historical run:** the timeout and incomplete checks below describe this earlier attempt. The subsequent [Research timeout investigation](RESEARCH_TIMEOUT_2026-10-16.md) passed the missing Research/save/reopen scope on the current pinned model; it preserves the model/runtime comparison limits and remaining release gates.

Publication remains **on hold**. These local changes follow the failures in the [full verification report](VERIFICATION_2026-10-16.md); no version bump, release, tag, push or personal-vault migration was performed during this fix.

**Verification completed for the executed scope; overall real-model acceptance has not passed.** All ten question cases pass. A subsequent Research writer request exceeds the provider deadline, so its save/export/reopen checks remain unexecuted on the real model.

## Changes

- The evidence verifier receives server-assigned claim labels `C1…Cn`, separate from passage labels `E1…En`. It returns exact `supported_claim_ids` rather than ambiguous array positions. Unknown labels, extra keys, numeric/boolean IDs and malformed responses are rejected. One malformed-contract recheck is allowed; a valid rejection is final within that verification attempt. The service never guesses an index convention or accepts a statement merely because its citation exists.
- The writer receives an explicit EN/RU answer language derived from the question, including questions with foreign proper names. If a conservative detector finds clearly opposite-language prose, one new generation is allowed. Every regenerated claim still passes the normal evidence verifier. Persistent detected drift produces a localized diagnostic instead of accepted wrong-language claims. Provider errors are not automatically replayed.
- Research records its chosen language and exports `Sources` or `Источники` accordingly. Older sessions infer the language from their question when saved. Existing saved documents and original source quotations are not rewritten.
- Generation, verification, language policy and Research export each have a named module; see the [code map](CODE_MAP.md).

Public answer/citation fields and saved chat format remain compatible. The claim-ID protocol is private to the verifier; canonical source IDs, versions and quotations are restored before answers are returned or stored.

## Verification

| Check | Result |
| --- | --- |
| Backend regression suite | 118 passed, one existing Starlette deprecation warning |
| Ruff, TypeScript, 271-key EN/RU catalog, fixture validation, release metadata | Passed |
| Production frontend export and fresh PyInstaller backend | Passed |
| New Windows unpacked package and bundled-backend SHA-256 comparison | Passed |
| Packaged desktop, EN/RU, persistence, source maintenance and frozen PDF/provenance/auth checks | Passed |
| Real Ollama fixture questions | 10/10 passed independent assistant review; 20 completed model calls |
| Real source replacement and historical originals/answers | Both passed |
| Real Research generation | Failed: writer call 24 hit `httpx.ReadTimeout` after 120.20 seconds |
| Real Research export/heading and post-save reopening | Not executed after generation failure; deterministic export/persistence tests passed |

The regression tests first reproduced the saved-heading and generated-language failures. Verifier tests include the recorded out-of-range budget response, distinct passage/claim labels, unsupported statements, malformed verdicts, malicious extra data and bounded retries. The packaged persistence mock was updated to the new private verifier contract; the supported and unsupported answer gates remain tested.

The first packaging attempt hit a sandbox network `EACCES` while fetching Electron. Packaging then succeeded with the existing local Electron `44.4.5` distribution. No dependency upgrade was needed.

## Real-model scope

The rerun uses the same existing `gemma4:12b` weights/digest as the previous attempt, a separate temporary alias, 40 GPU layers, a 4,096-token context, no embedding model and only the synthetic `evals/release02` documents. It includes all ten fixture questions plus source replacement, historical citations/originals, Research, saved Markdown and reopening without model replay. Resource and request-count guards stop the harness after provider failures. A reviewer checks full claims, language, complete supporting quotations, original bytes, source versions and canonical evidence IDs; pattern matching alone is not an acceptance result.

The tested worktree is based on `e708fe4121b55ca0d6f83789a13f319cd200ff41` with uncommitted fixes. `environment.json` captures the tracked diff and SHA-256 manifest of application/test/script bytes, including new modules. The prior native CI run tested the earlier commit only. Current changes have not yet been rerun on native macOS or Linux hosts.

The question run accepted the budget through `C1` while its passage had a different `E` label. The English temperature question produced two supported English statements of absence on its first writer attempt. The malicious passage appeared before factual evidence and did not alter the launch date or trigger its requested commands. No repair was needed in the twenty question calls. End-to-end question times were 47–125 seconds. This is a single synthetic run, not a reliability or speed benchmark.

After replacement, the new answer correctly used November 22, 2030 with revision 2, while the saved old answer retained October 18 and revision 1. Both original-file byte hashes and canonical citation IDs were independently checked. Research then failed before producing any answer, Markdown artifact or memory finding. Its real-model English heading and post-save reopening cannot be claimed as passed from the separate deterministic tests or the previous application's successful run.

### Remaining timeout and environment evidence

The trace records `httpx.ReadTimeout` while waiting for response headers from the non-streaming Research writer request. It contained seven passages (3,075 characters of request data). The application read timeout is 120 seconds; it was not increased or automatically retried to conceal the failure. Before the call, the harness observed about 11.9 GB available RAM and 2.5 GiB free VRAM. Ollama's local version/status endpoints remained responsive afterward. These snapshots do not establish why generation was slow or rule out every transient system fault.

This run used Ollama `0.40.5`; the earlier report recorded `0.34.4`, so the before/after runs are not a controlled comparison of code alone. The original `gemma4:12b` tag also changed digest during this run, between preparation and cleanup. No pull or original-tag mutation was issued by this verification. The temporary test alias retained its prepared digest throughout the recorded calls and before removal. Evidence is preserved in `model-state-before-cleanup.json` and `timeout-diagnostic.json`.

The cleanup script's original-tag guard initially stopped on this drift. Cleanup then independently checked the exact test alias against its prepared digest, unloaded/deleted only that alias, and verified that the current original tag was unchanged by cleanup. No test model remains loaded; Ollama remains running. See `cleanup.json`.

## Limits and remaining gates

The EN/RU policy is a small heuristic, not a complete language detector. Short or ambiguous text and noun-heavy sentences may escape mismatch detection. Original quotations and proper names may retain their language. Neither a successful fixture run nor the model critic guarantees factual truth across arbitrary questions/models.

One answer makes at most two writer and two verifier requests. Research retains its existing second retrieval/answer attempt, so its upper bound is nine completion requests including the planner. Normally each accepted answer uses one writer and one verifier. Extra attempts can add latency or cloud-provider cost.

The next investigation is long Research generation on the selected local runtime/model. Preserve the failed run, isolate the slow request, and define bounded handling for slow responses before rerunning the full Research/save/reopen exercise. Do not mark acceptance complete by merely extending the deadline or substituting stubs.

Owner hands-on acceptance remains pending. Cloud-provider inference and real embedding inference were not exercised here. Builds remain unsigned; native security prompts, signing/notarization and AppImage FUSE mounting remain outside these checks. A fresh native CI matrix and final release build are required before publication at the owner's chosen time.

Local evidence: `test-results/model-fixes-20261016/` — `automated-checks.json`, build/package logs, `environment.json`, `results.json`, `provider-trace.json`, `assistant-review.json`, `extended.json` and cleanup evidence. Generated evidence and binaries are ignored by Git.
