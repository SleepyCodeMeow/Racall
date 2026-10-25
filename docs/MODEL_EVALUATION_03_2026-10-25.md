# 0.3 local-model evaluation — October 25, 2026

Publication remains on hold. These checks use a synthetic knowledge vault and
the owner's local Ollama, not personal documents or cloud credentials.

**Model reliability is not certified:** recorded unsupported claims passed the
critic, including a repeat under the extended policy. Functional workflow
completion and later successful examples do not erase those false positives.

## Runtime and limits

- Ollama 0.40.5; Gemma `gemma4:12b`, 11.9B Q4_K_M, original digest
  `6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b`.
- Windows, RTX 3080 with 10,240 MiB VRAM. A temporary alias uses the existing
  weights with `num_gpu=40`, `num_ctx=4096`; no weights were downloaded and the
  original model was not changed. These are this machine's tested limits, not a
  default for all hardware.
- Production completion parameters and model thinking behavior are retained.
  The initial eight-token warm-up alone disabled thinking; it is not an
  acceptance result.
- One completion at a time, at most 80 attempts / 45 minutes per full run,
  loopback endpoints only, an explicit STOP file, digest checks and sampled RAM
  and NVIDIA free-memory checks. Resource snapshots are not continuous peak
  monitoring, and closing a request does not establish immediate GPU work stoppage.
- Real application API, keyword retrieval, saved-note context, production
  writer/critic and Research/Studio workers. Embeddings are disabled. The
  credential store is disabled and each run owns a new isolated vault.

## Observed failure and correction

The first run was stopped after an independent review found a semantic failure
in `core-unknown-results`. The writer asserted:

> No actual temperatures have been measured by the Лис station yet as the results of its work have not been received.

The cited passages establish only that measured temperatures were not reported
and that results had not been received. They do not prove that measurements never
occurred or explain why. The critic incorrectly accepted that compound claim.
Correct quotation hashes and offsets did not make the inference valid.

Nine of the first ten core questions passed independent semantic review; this
case failed. The stopped run retains 30 attempted completions: 29 completed and
one blocked before transport by the STOP file. It is not a successful full run.
Evidence: ignored local directory
`test-results/live03-20261025T173136Z/acceptance/`.

Source `6c1a59da070d50637c34cb170c48d8653aa76a77` adds shared evidence-scope
instructions to chat and Studio writers, the critic and its malformed-response
repair. They preserve time, certainty and reporting scope, reject unsupported
clauses, causal links and question premises, and distinguish missing reports
from events that did not occur. The JSON protocol is unchanged.

The [recorded failure](../evals/release03/regressions/absence-versus-event.json)
preserves the original synthetic passages and responses. Deterministic
workflow regressions check policy propagation, filtering, supported negative
facts and a review question's unsupported premise; they do not simulate a
model's semantic judgment. That revision's backend suite passed **496 tests**.

A separate real-model probe completed four production calls. It rejected the
original unsupported claim while accepting the accurate absence-of-report
claim, accepted an explicit supported negative fact, and generated/verified:

> No measured temperatures were reported for the Лис station.

An independent review checked the statement and its exact source bytes, version
hash, paragraph, offsets and line span. This is a focused regression pass, not
full model acceptance. Evidence: `policy-probe/` beside the first run.

## Repeat and a second semantic failure

The fresh `acceptance-r2/` run used source
`6c1a59da070d50637c34cb170c48d8653aa76a77`. Independent review passed all ten
core questions, six context cases, Research and the Studio summary. It failed
the Study Guide: the writer translated the station plan's approval on September
21 into finalization on that date. The source does not establish when the plan
was finalized. The critic accepted the entire compound claim, including its
otherwise correct scheduled opening date.

The [second recorded failure](../evals/release03/regressions/approval-versus-finalization.json)
retains all seven Study Guide records and the exact mixed critic batch. At STOP,
18 cases had passed semantic review, one failed, one had no final material and
five were not run. The trace contains 37 attempts; the final background critic
was still marked running when the old evaluator exited. Its outcome is unknown,
not a completed or successful call. This stopped run is not full acceptance.

Source `50e1a65a80f86c2f66c6132289904057ec89bbb2` makes event/predicate identity
and date binding explicit, retains that regression fixture and adds a bounded
evaluator shutdown drain. Two offline tests exercise an actual Studio worker
stopped during transport and an explicit cleanup timeout. The helper now waits
for local completion cleanup before restoring hooks; it never fabricates a
terminal trace when cleanup times out. The full backend suite passes **499 tests**.

The first live probe of the extended instructions (`event-probe/`) immediately
accepted the old unsupported no-measurements claim again. This is a semantic
false positive with valid JSON, not an evidence-offset or parser failure. A
single earlier successful probe therefore did not establish stable verification.

A separate bounded characterization retained the same critic prompt, model and
production sampling: bad claims alone, safe claims alone and reversed mixed
pairs for both failure domains, plus an explicit supported negative fact. All
seven calls matched their expected verdicts, independently reviewed. This does
not identify batch ordering as the cause: the previous mixed pair failed while
this reversed pair passed. It does not erase earlier false positives or justify
20 critic calls per answer, extra retry-until-pass loops or a quality guarantee.
Evidence: `critic-characterization/`, including its separate manual-review file.

## Complete functional run

The fresh `acceptance-r3/` run uses source
`50e1a65a80f86c2f66c6132289904057ec89bbb2`. All **25 workflow contracts passed**
in 720.5 seconds. There were **43 sequential completion attempts**: 41 completed
and two intentionally cancelled during lifecycle checks. No attempts overlap;
shutdown drained with no unfinished calls. No provider/resource/deadline failure
occurred. Completed-call times ranged from 4.4 to 76.5 seconds (median 10.7);
these are observations from this run, not a performance benchmark.

| Scenario group   | Cases | Completed behavior                                                                                                                   |
| ---------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Baseline answers | 10    | EN/RU facts, units, dates, absent facts and document-instruction resistance                                                          |
| Context          | 6     | Selected-source follow-up, empty/excluded/notebook isolation, Nia → Omar saved-note revisions, selection/history restart             |
| Research/Studio  | 5     | Research, summary, study guide, Russian questions with answers, export/editable copy/library reopening                               |
| Lifecycle        | 4     | Queued/running cancel, interrupted restart without replay, explicit retry on source v2, current answer with old r1 citation retained |

The outputs include real Markdown exports for all four generation jobs.
The independent final review is stored separately from raw runner verdicts in
`acceptance-r3/manual-review.json`: **24 pass, one pass with a naming note, zero
new unsupported final factual claims found in this run**. It checked persisted
jobs/materials/chats, source and note revisions, unchanged export quotations,
cancellation attempts 38/39, explicit source-v2 retry, the new November 22 answer
and the retained October 18 historical citation/original. In the English Study
Guide, the proper name «Лис» was translated as “Fox”; the cited source remains
unambiguous, but literal name fidelity is reduced. This is assistant review,
not the owner's hands-on desktop acceptance.

The combined semantic gate remains **failed / not certified**, because the
recorded false positives include the same final critic policy. R3's successful
answers do not establish that the critic reliably rejects unsupported claims.

The smallest sampled available RAM was 12,016,533,504 bytes and NVIDIA free VRAM
1,955 MiB. Original and alias model digests stayed unchanged. The critic prompt
SHA256 was identical in the failed extended-policy probe, the seven controls and
this full run:
`a9f8f74ee9ed3da4321bbbb39d8835a92cfc6c47dc0a6c2add4a6f3bf2aecaeb`.
Later accurate outputs therefore cannot make the earlier same-policy false
positive irrelevant.

After the run, only the exact owned temporary alias was unloaded and deleted.
All other tags/digests were compared before/after; `gemma4:12b` remained unchanged,
Ollama 0.40.5 remained running and no models remained loaded. Free NVIDIA VRAM
returned to 9,138 MiB. Cleanup evidence is `cleanup.json` beside the run directories.

## Scope of the verdict

`validated=true` means that the production verification contract accepted an
answer. A separate review must inspect every factual clause, question premise,
section title, source association and requested fact. Safe abstention passes an
unknown question; omission on an answerable question is a coverage failure.

This API evaluation does not establish owner hands-on desktop acceptance,
embeddings quality, other model weights, llama.cpp, cloud OpenAI/Anthropic or
Ollama Cloud behavior, model downloads, signing, notarization or release approval.
Native packages and the installed 0.2-to-0.3 upgrade have separate evidence.
