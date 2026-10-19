# Research timeout investigation — October 16, 2026

**Historical verification snapshot:** these checks precede the subsequent [provider-profile update](PROVIDERS_2026-10-16.md). The real-model results below are not live acceptance of the newly added Claude/cloud connections.

**The executed local verification passed. Publication remains on hold.** The current worktree passes 171 backend tests, the fresh Windows packaged suite, all ten real Ollama questions, source replacement/history and real Research save/reopen checks. Owner hands-on acceptance, a real cloud-provider run and a fresh native CI matrix remain open.

This follows the [earlier model-fix run](MODEL_FIXES_2026-10-16.md), where a non-streaming Research writer failed with `httpx.ReadTimeout` after 120.20 seconds. That failed evidence is retained. The current model tag has different weights, so this is not a controlled performance comparison.

## Diagnosis and change

The old completion transport waited for a whole response. A local model could be generating while the client saw no response headers or bytes and exhausted its 120-second read timeout. The trace establishes that failure mode; it does not establish GPU exhaustion, context overflow or a model defect.

`completion_stream.py` now requests OpenAI-compatible SSE and collects only `delta.content`. Role, usage and reasoning metadata are not answer content. SSE must end with `finish_reason: stop` and `[DONE]`; truncated, malformed, tool-call or interrupted output fails without becoming an answer. Compatible servers returning whole JSON instead are supported; an omitted legacy finish reason is accepted, but an explicitly abnormal finish is rejected. Existing citation verification still runs after completion.

Each completion has a **300-second total deadline**, a **120-second idle timeout** and a 15-second connection timeout. Continuous output cannot bypass the total deadline. Wire data is bounded to 1 MiB, answer content to 256 KiB, and individual event/line data to 64 KiB. Responses request identity encoding and fail safely if a server ignores it. The transport does not retry inference. Existing bounded writer/verifier workflow retries are unchanged.

The public provider contract remains synchronous. This is internal transport streaming; the interface still receives the completed, verified result. Closing/aborting a browser request does not promise model cancellation. Thinking, temperature and generation limits were not overridden to make the test pass. EN/RU diagnostics distinguish an idle connection, a total deadline and a broken stream. Embeddings retain their existing transport.

## Verification

| Check | Result |
| --- | --- |
| Backend suite | 171 passed; one existing Starlette deprecation warning |
| New transport/provider regressions | 47 transport tests and 6 public binding/diagnostic tests, included above |
| Ruff, TypeScript, release metadata and 274-key EN/RU catalogs | Passed |
| Production web build and fresh PyInstaller backend | Passed |
| Fresh unpacked Windows x64 app | Built with Electron 44.4.5; packaged suite passed |
| Packaged scenarios | Desktop, live/restart EN/RU and installer language seeding, SSE persistence, source/history maintenance, frozen PDF/FTS/citation/original/authentication checks |
| Real Ollama questions | 10/10 passed independent assistant review; 19 requests, no timeouts |
| Source replacement | New answer uses November 22, 2030 from revision 2; historical October 18 answer and revision 1 original bytes preserved |
| Real Research | Planner 11.22 s, writer 22.95 s, critic 22.11 s; 56.28 s combined |
| Research content | Both schedules and sensor counts correct; exact canonical citations point to revision 2 and the station document |
| Save/reopen | English `Sources`, quotations, Markdown revision, accepted memory citations, chats and active/historical source versions preserved after service/store recreation without model replay |
| Cleanup | Only this run's pinned temporary alias unloaded/removed; original model and other tags preserved |

Transport tests exercise slow active streams, genuine idle timeouts, a total deadline despite arriving bytes, split UTF-8/CRLF, reasoning separation, truncated streams, abnormal finish, duplicate keys, invalid Unicode, size limits and whole-response compatibility. Provider tests cover safe errors, unchanged generation defaults and absence of transport inference retries. Packaged persistence uses the real frozen transport against deterministic SSE; model quality comes from the separate real run.

An independent assistant inspected complete claims/quotations and language, original bytes/version hashes, offsets/line ranges, claim-to-citation sets and canonical evidence hashes. All ten questions and four extended verification groups passed. A safe abstention for an unsupported question is valid. Pattern flags alone were not acceptance verdicts. Human verdicts remain pending.

## Reproducibility and limits

HEAD remained `e708fe4121b55ca0d6f83789a13f319cd200ff41` on `development/0.2`, with existing uncommitted fixes plus this transport change. The application/test/fixture manifest, including new untracked modules, is `fb0557951bc53ce37c0e6e2df868fb4205183ba8c9caefc02d1fda46a2e049e3`. Documentation is outside that manifest. Raw evidence is retained in ignored `test-results/research-timeout-20261016/`; durable findings are recorded here.

This run used Ollama 0.40.5 and existing `gemma4:12b` source digest `6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b`, with temporary alias digest `c9059a4b3435d1e6949939c24f4e746dc58c87a979b0634802082e2c0ba4111e`. Only 40 GPU layers and 4,096-token context were selected for the alias; thinking and the current model's DRAFT defaults were retained. No download, personal-vault access or user AI-setting change was performed.

The original tag changed during the earlier failed run; its prepared alias had older weights. Runtime/model differences prevent attributing a 120-second failure versus a 23-second writer solely to streaming. A replay diagnostic completed on current weights, but its `reasoning_characters: 0` counter measured only `reasoning_content`; Ollama uses `delta.reasoning`. That is a measurement omission, not evidence that thinking was disabled.

Ollama's `size_vram` underreported this DRAFT workload. Guards instead used total GPU free memory from `nvidia-smi` (at least 1 GiB), available system RAM (at least 1.5 GB), one loaded test model and bounded request counts. All 24 production requests finished. After cleanup the GPU reported 9,020 MiB free. One synthetic pass does not prove reliability for every document, hardware configuration or compatible cloud server.

Evidence includes `production/environment.json`, `provider-trace.json`, `results.json`, `extended.json`, `assistant-review.json`, `provenance-review.json`, build/test logs and `cleanup.json`. The new unpacked executable is `test-results/research-timeout-20261016/windows/win-unpacked/Racall.exe`; its backend matches the fresh frozen build. No installer was installed here. Service/store recreation is distinct from the owner's interactive desktop acceptance.

## Remaining release gates

The previous four-platform CI covers the earlier committed app. Windows x64 was rebuilt/tested locally; macOS/Linux and installer checks still need a fresh native matrix for the final source revision. Real cloud-provider acceptance and owner review remain separate gates.

Version remains `0.2.0-beta.1` / **0.2 Beta**, with `publication: hold`. No commit, push, tag, release or global installation was performed. See the [release checklist](RELEASE_02_CHECKLIST.md).
