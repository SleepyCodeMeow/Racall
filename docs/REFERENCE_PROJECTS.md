# Reference projects and implementation priorities

Reviewed 2026-09-26. [Roadmap](ROADMAP.md) · [Architecture decisions](adr) · [Project home](../README.md)

Use comparable projects to learn which workflows matter and how they are implemented. Adapt useful patterns to Racall's desktop application, local files and Python service. This review reads selected source files and documentation; none of the reference applications was installed or tested. Code presence is evidence of an implementation path, not proof of output quality, completeness, security or cross-platform support.

## Reviewed snapshots

Pinned links below keep the findings reproducible even when upstream main changes.

| Project | Reviewed commit | Primary use for Racall |
| --- | --- | --- |
| [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook) | [`3127f14ea9db`](https://github.com/lfnovo/open-notebook/tree/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef) | Persistent conversations, podcast profiles and generation jobs |
| [MODSetter/SurfSense](https://github.com/MODSetter/SurfSense) | [`014e47a7efa1`](https://github.com/MODSetter/SurfSense/tree/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e) | Desktop workers, Studio dispatch and durable output files |
| [Anionex/Open-NotebookLM](https://github.com/Anionex/Open-NotebookLM) | [`36ecc9336eb5`](https://github.com/Anionex/Open-NotebookLM/tree/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a) | Slide generation stages, segmented speech and optional local TTS |

## Findings and adaptation decisions

### Open Notebook

[Chat graph](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/open_notebook/graphs/chat.py) uses a SQLite-backed LangGraph checkpointer. [Podcast models](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/open_notebook/podcasts/models.py) separate episode settings, speaker profiles and generated episodes; speaker profiles validate a range of one to four speakers. [Podcast commands](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/commands/podcast_commands.py) resolve voice/model settings and delegate generation to a separate podcast library through a background command.

**Racall proposal:** persist notebook-scoped threads and messages, including citation references, before adding new generators. Later separate an editable episode script from voice settings and audio files. Retain our SQLite storage and provider interfaces unless measurements justify additional frameworks; a useful pattern does not require adopting the reference project's database or graph framework.

### SurfSense

[Desktop architecture](https://github.com/MODSetter/SurfSense/blob/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e/surfsense_local/README.md) describes Electron starting an API plus import and Studio workers. [Queue code](https://github.com/MODSetter/SurfSense/blob/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e/surfsense_local/backend/shared/queue.py) defines separate ingest and Studio queues using SqliteHuey in a queue database. [Artifact models](https://github.com/MODSetter/SurfSense/blob/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e/surfsense_local/backend/modules/artifacts/models.py) store generated-output metadata and primary/preview files with checksums; deleting a chat thread detaches its artifact instead of deleting the deliverable. [Studio router](https://github.com/MODSetter/SurfSense/blob/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e/surfsense_local/backend/worker/studio/job_router.py) dispatches summaries, quizzes, flashcards, mind maps, office formats, images and podcasts to separate renderers. These routes were read, not executed.

**Racall proposal:** isolate heavy imports from model generation, persist job state, and use a shared output catalog instead of separate storage conventions for every format. Keep generated reports or decks when a user deletes their chat. Evaluate whether a small SQLite job runner is sufficient before adding a queue dependency.

### Open-NotebookLM

[Slide workflow](https://github.com/Anionex/Open-NotebookLM/blob/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a/workflow_engine/workflow/wf_paper2ppt_parallel_consistent_style.py) separates page generation, single-page revision and export. In this particular export path, the converter is called with `output_pptx_path=None` and the result clears `ppt_pptx_path`. Do not treat that path as demonstrated editable PPTX export; other routes need separate inspection.

[Podcast workflow](https://github.com/Anionex/Open-NotebookLM/blob/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a/workflow_engine/workflow/wf_kb_podcast.py) separates file parsing, script generation and audio generation, then splits speech into speaker-labelled segments with bounded concurrency and retries. The inspected language branch distinguishes Chinese from other languages; Russian quality has not been established. [Local TTS manager](https://github.com/Anionex/Open-NotebookLM/blob/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a/fastapi_app/qwen_tts_manager.py) lazily loads Qwen3-TTS and schedules unloading after idle time. Its device selection uses CUDA or CPU; this is not evidence of optimized Apple Silicon support.

**Racall proposal:** make the script and slide outline reviewable before paid media generation. For presentations, produce editable text and shapes with template-based export first; generated slide images can be an optional visual mode. Keep heavyweight speech models optional, with explicit download and resource information. Test English and Russian independently.

## Mapping to Racall

This table records the published **0.1 baseline** used for planning. The first 0.2 development slice now implements persistent conversations, citation snapshots and conflict-aware autosave; see [development notes](releases/0.2.0-beta.1.md) for verified scope and remaining work.

| Workflow | Current Racall baseline | Next implementation and completion check | Target |
| --- | --- | --- | --- |
| Conversations | Turns live in UI state | Store threads/messages and source-version references; reopen the same conversation after restart without mixing notebooks | 0.2 |
| Notes and sources | Explicit note saves; existing import/index pipeline | Recover drafts, handle external Markdown edits without silent overwrite, preserve old citation provenance when refreshing a source | 0.2 |
| Background generation | Research runs within the request | Persist queued/running/completed/failed/cancelled states; test restart, cancellation and retry without duplicate outputs | 0.3 |
| Studio catalog | Research reports can be saved as Markdown | Common output record with type, source versions, model settings, job ID, editable content and exported files; reports and study tools first | 0.3 |
| Slides | Not implemented | Outline → editable slide structure → renderer → preview/export; open the resulting PPTX in a presentation editor and verify text remains editable | 0.4 target |
| Audio | Not implemented | Script → reviewed speaker segments → TTS → assembled audio; retry failed segments, preserve order, test EN/RU intelligibility and source fidelity | 0.5 target |
| Video | Not implemented | Combine reviewed slides and narration with subtitles; verify timing, export playback and restart behavior | 0.6 target |

Local baseline: [workspace UI](../apps/web/features/chat/chat.tsx), [storage](../apps/api/on_knowledge/storage.py), [knowledge service](../apps/api/on_knowledge/knowledge.py). Persistent generation records remain future work. The 0.2 implementation and its limits are recorded in [ADR 0012](adr/0012-feature-organization-and-persistence.md).

## Reuse boundaries

We have not copied implementation code or imported dependencies from these projects in this review. The inspected root license files state:

- [Open Notebook: MIT](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/LICENSE).
- [SurfSense: Apache 2.0 with a directory exception](https://github.com/MODSetter/SurfSense/blob/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e/LICENSE): `surfsense_backend/app/proprietary/` is designated Business Source License 1.1. The desktop paths reviewed here are outside that exception, subject to separately licensed components.
- [Open-NotebookLM: Apache 2.0](https://github.com/Anionex/Open-NotebookLM/blob/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a/LICENSE).

Before importing code, inspect the exact files, notices, dependencies and any model weights; record provenance and preserve applicable terms. A root license does not automatically cover every bundled dependency or model. Architectural observations alone do not introduce those dependencies into Racall.

## Working method for each feature

1. Select one user workflow and a reference implementation; record the reviewed commit and paths.
2. Trace its inputs, source handling, persisted state, provider calls, outputs and failure behavior. Treat upstream README claims as claims until checked.
3. Write the Racall adaptation and acceptance checks before implementation. Record substantial architecture changes in an ADR.
4. Build a narrow end-to-end slice using a fixed sample notebook; test failures and recovery as well as a successful run.
5. Compare citation correctness, editable output quality, EN/RU behavior, cost where measurable, latency, installer size and memory use. Real-provider checks complement deterministic tests.
6. Record what was actually verified and any reused code/dependencies. Promote a feature to release documentation only after Racall's own checks pass.

This is a feature-development reference process, not a scheduled monitoring service. Revisit the relevant upstream snapshot when work on that feature begins.
