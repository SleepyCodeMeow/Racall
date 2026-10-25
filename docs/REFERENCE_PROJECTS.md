# Reference projects and implementation priorities

Last refreshed 2026-10-25 for 0.3 planning; the October 17 and September 26 reviews are retained below. [Roadmap](ROADMAP.md) · [Architecture decisions](adr) · [Project home](../README.md)

Use comparable projects to learn which workflows matter and how they are implemented. Adapt useful patterns to Racall's desktop application, local files and Python service. Source reviews and observations of an installed application are distinguished below. Code presence is evidence of an implementation path, not proof of output quality, completeness, security or cross-platform support.

## Refresh: 2026-10-25

This is a source audit and a proposed 0.3 scope, not a feature implementation. Racall's published baseline is [0.2 Beta for Windows](releases/0.2.0-beta.1.md), application commit `70fd79b`, with documentation at local `main` commit `38be1ae`. The [published verification](VERIFICATION_2026-10-19.md) records its 404 backend tests and exact package scope. No Docker/WSL load, real model inference or upstream application installation was started for this audit.

### Pinned references and changes

| Project | Current reviewed source | Change since the previous review |
| --- | --- | --- |
| Open Notebook | [`a0f6f3081ae0`](https://github.com/lfnovo/open-notebook/tree/a0f6f3081ae06328f0a451b3a3ef2959ca25721d) | Same HEAD as October 17; compare is identical, with zero new commits/files |
| SurfSense | [`e3de9e0d293b`](https://github.com/MODSetter/SurfSense/tree/e3de9e0d293b2ebb1fb813628ecc1d6f26909396) | 131 commits ahead of the October 17 snapshot; current HEAD is dated October 21 |
| Open-NotebookLM | [`36ecc9336eb5`](https://github.com/Anionex/Open-NotebookLM/tree/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a) | Same HEAD as the September review; compare is identical |

Open Notebook remains the primary product reference. Its [chat graph](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/open_notebook/graphs/chat.py) actually supplies accumulated conversation messages to the model and persists graph state. Its [context builder](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/open_notebook/utils/context_builder.py) supports source inclusion modes and selected notes. The viewed notebook chat node does not itself establish a bounded history window; Racall should add its own explicit budget.

Its [transformations](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/docs/3-USER-GUIDE/transformations.md) are saved prompts producing Markdown insights, with built-in summaries, key insights, article analysis, reflection questions and a table of contents. Dedicated quiz, flashcard and PPTX workflows were not found in this inspected tree. [Podcast generation](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/commands/podcast_commands.py) has separate outline/transcript/speech configuration and saved outputs. However, generic [job listing and cancellation](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/api/command_service.py#L71-L89) are placeholders: listing returns an empty list, and cancellation logs then returns success. Do not infer working cancellation or stage-level recovery from the existence of these routes.

SurfSense is useful for the generation lifecycle. Its [format catalog](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/modules/artifacts/formats.py) declares 12 formats, with model capability requirements rather than treating a text connection as image/speech support. Its [artifact records](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/modules/artifacts/models.py) retain generated files independently of a chat, and [grounding](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/worker/studio/shared/gather.py) has a bounded input budget. A selected source count is not evidence that all selected text reached the model.

Its [worker lifecycle](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/worker/jobs.py) checks cancellation around long operations and prevents a late success from replacing cancellation. [Startup handling](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/worker/interrupted_documents.py) marks interrupted processing failed, rather than resuming an in-flight model call. The [Studio task](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/modules/artifacts/tasks.py) also configures a retry for ordinary failures; Racall should retain its own explicit-retry policy rather than copying that behavior unchanged.

Recent SurfSense additions include a [Claude plan connection using installed Claude Code](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/modules/llm/subscriptions/claude/router.py) and [OCR-first scan handling](https://github.com/MODSetter/SurfSense/blob/e3de9e0d293b2ebb1fb813628ecc1d6f26909396/surfsense_local/backend/worker/ingestion/scan_ocr/switch.py). These are source-level findings, not verified account access, OCR quality or resource usage. The core Studio backend/catalog/queue/artifact modules are unchanged from the October 17 snapshot; the broad Studio is not a new feature of these eight days. The inspected Studio changes are a Word list-numbering fix and a frontend event type correction.

Open-NotebookLM remains a later media-workflow reference. The inspected [slide export path](https://github.com/Anionex/Open-NotebookLM/blob/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a/workflow_engine/workflow/wf_paper2ppt_parallel_consistent_style.py#L704-L728) still passes `output_pptx_path=None` and clears the PPTX result. A variable named editable PPTX is not proof of editable export. Its [local speech manager](https://github.com/Anionex/Open-NotebookLM/blob/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a/fastapi_app/qwen_tts_manager.py) chooses CUDA or CPU and manages optional model weights; that path is unnecessary for Racall's first text-only Studio.

### Racall gaps confirmed in the current code

| Existing behavior in 0.2 | Proposed 0.3 improvement |
| --- | --- |
| [Chat turns](../apps/api/on_knowledge/features/chats/router.py) are saved, but `knowledge.answer` receives only the new question. The source panel opens sources, without selecting context for an answer | Bounded history from the active thread, explicit source selection and an optional saved-note context selection |
| [Research POST](../apps/api/on_knowledge/features/research/router.py) runs inside the request. [Research](../apps/api/on_knowledge/knowledge.py) writes initial/final state, while intermediate steps remain in memory | A shared durable generation-job lifecycle for Research and Studio, with actual stage progress, cancellation and explicit retry |
| Artifacts are saved Markdown Research reports shown through the notes preview | A small typed material library: summary, study guide and review questions with answers; reopen, inspect citations, save an editable note copy and export Markdown |

Racall already has background import execution and a durable/cancellable model-download operation. These are useful local patterns; the gap is a shared lifecycle for text generation, not the total absence of background work. Existing Research reports, notes and citation snapshots must remain readable.

### Proposed 0.3 scope and delivery order

One complete workflow: **select materials → discuss them with context → generate and retain a useful learning material**.

1. **Context-aware chat.** Resolve follow-up questions using bounded history from one thread. Keep source passages as evidence; previous model prose is conversation context, not a new factual source. Offer clear source selection and saved-note inclusion, with visible context limits.
2. **Durable generation jobs.** Move Research onto the shared job lifecycle first. Use one generation worker initially, persisted stages and request IDs. Cancellation must affect actual work/results. Restart retains the job as interrupted and never silently repeats paid model calls.
3. **First Studio.** Add exactly three text presets: concise summary, study guide, and review questions with answers. These are saved, cited learning materials; an interactive quiz/scoring engine and flashcard UI are not part of this initial slice. Reuse configured text providers and the Markdown editor/export path.
4. **Material library and compatibility.** Keep results independently of the originating chat. Store input source versions, note revisions, model/profile identity and job ID without credentials. Open/export earlier reports and create editable note copies without a destructive migration of 0.2 notebooks.

Keep these responsibilities in `features/context`, `features/jobs`, `features/studio` and `features/artifacts`, with small shared retrieval/provider modules. Durable job state must not live in `index.sqlite3`, which is a rebuildable search cache. The precise durable storage mechanism should be chosen during implementation without introducing Redis/PostgreSQL or a new graph framework by default.

### Acceptance cases for the proposed slice

- A follow-up such as “why?” or “compare that with the previous result” uses the correct thread; another thread/notebook cannot affect it.
- An excluded source never enters retrieval or generation. An explicit empty selection never silently becomes all sources. Saved-note inclusion is explicit and revision-aware.
- Long histories obey the context budget. A context-trim indication is available, and earlier assistant text never substitutes for evidence supporting a new claim.
- Repeating a submission with the same request ID cannot start a second generation. A cancelled queued job makes no provider call; a late result cannot overwrite cancellation.
- Restart preserves completed outputs and interrupted state without automatic model replay. Explicit retry creates a traceable attempt and does not duplicate a finished material.
- Source replacement during a queued/running job cannot silently substitute a new version. Snapshot the inputs or detect the change and require an explicit retry.
- A changed provider profile cannot silently change a queued job or send newly saved credentials to an older snapshotted endpoint. Persist nonsecret configuration identity/revision; invalidate incompatible queued work rather than storing keys in job metadata.
- Old 0.2 notebooks/chats/reports reopen, and all three new formats work in EN/RU with inspectable citations and Markdown export. Provider-fixture checks remain separate from actual model-quality evaluation.

**Deferred from this 0.3 proposal:** presentations, audio/video, OCR engines, Claude subscription/CLI backends, a full office-file agent, extra languages, mobile/sync, a new database stack and a major visual redesign. Flashcards and interactive quizzes can follow once the common generation/material lifecycle works. Later roadmap targets remain provisional.

No upstream implementation, assets or dependencies were imported. Detailed source responses and audit notes are retained only in ignored `test-results/reference-audit-20261025/`. This planning update does not change the application version or publish a release.

## Refresh: 2026-10-17

This refresh is an audit and adaptation proposal. It does not implement the proposed features, change the release version or publish a release. The current Racall workbench is documented in [Workbench](WORKBENCH.md) and its [verification record](WORKBENCH_2026-10-17.md).

### Current source snapshots

| Project | Reviewed commit | Primary reference |
| --- | --- | --- |
| Ollama | [`d1ed3fd13ac7`](https://github.com/ollama/ollama/tree/d1ed3fd13ac73f60cff00bbead8af24a68c4200d) | Minimal chat, model discovery, Apps and settings |
| Open Notebook | [`a0f6f3081ae0`](https://github.com/lfnovo/open-notebook/tree/a0f6f3081ae06328f0a451b3a3ef2959ca25721d) | Sources/notes context and persistent multi-turn conversations |
| SurfSense | [`176aed261a24`](https://github.com/MODSetter/SurfSense/tree/176aed261a24a85d217538960e91c59746561bd2) | Studio, background jobs and durable generated outputs |

Open-NotebookLM was not refreshed in this audit; its September snapshot below remains historical. These repositories were inspected as source, not installed or executed.

### Installed Ollama: observed separately

On the inspected Windows computer, Ollama is installed under `%LOCALAPPDATA%\Programs\Ollama`. The desktop executable is `ollama app.exe`, with `ollama.exe` beside it. The CLI and running local API reported **0.40.5**. Settings showed the model directory as `%USERPROFILE%\.ollama\models`. The exact source commit of the installed binary was not established; current upstream source must not be treated as an exact build match.

The preinstalled app was opened and its sidebar, Apps grid, empty Chat, model popup and Settings were inspected. Observed flows:

- The sidebar collapses and exposes Apps, Chat and Settings; chat history is grouped separately.
- Apps uses a two-column grid of 14 compact tool cards. No command was copied during this inspection. Command-copy behavior and feedback were traced in source.
- Empty Chat places the mascot above the composer, with attachment, web-search, model and send controls. The model popup has search at the top and seven entries marked as cloud, downloadable or selected locally.
- Settings groups account, cloud, updates, network exposure, model folder and context length into simple rows. No setting or account state was changed.

Only metadata was requested from the local API: version, currently loaded models (zero at the time checked), and model recommendations. The experimental recommendations endpoint returned the same seven model IDs seen in the popup. No prompt was sent, model downloaded, cloud sign-in attempted or answer quality evaluated. Opening the app started its local service; this was not an inference test. Search filtering, generated-answer controls and download behavior were reviewed in source rather than exercised in the installed UI.

### Ollama appearance and behavior to adapt

The following dimensions come from the pinned upstream source, not pixel measurements of the installed binary.

| Element | Upstream Ollama | Racall at this audit | Proposed adaptation |
| --- | --- | --- | --- |
| Sidebar | 192 px, collapsible | 214 px normally / 192 px at smaller widths, no collapse | Add collapse while retaining notebooks, sources, notes and research |
| Navigation | 14 px text, 20 px icons, 8 px radius | 13 px text, 7 px radius | Shared navigation tokens and consistent hit areas |
| Composer | Up to 768 px wide, minimum 88 px high, 24 px radius | Wrapper up to 748 px, inner width about 700 px, 20 px radius | Calm central composer; move to the bottom once the conversation has content |
| Composer buttons | 36 × 36 px | Attachment 30 px, Send 31 px | Consistent 36 px controls |
| Model popup | 256 px wide, 16 px radius; search first | 350 px wide, 13 px radius; provider/header before search | Compact searchable list; advanced connection and manual-ID controls secondary |
| Apps grid | Up to 620 px, 8 px gap, 16 px card radius | 584 px wrapper including padding, 7 px gap, 12 px radius | Tight two-column grid and feedback on the clicked card |
| Dark colors | Neutral 900 background / neutral 800 composer | Already close: `#171717` / `#262626` | Preserve the existing light/dark/system themes and orange Racall branding |

Sources: [layout](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/components/layout/layout.tsx#L25), [navigation](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/components/AppSidebar.tsx#L8), [composer](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/components/ChatForm.tsx#L685), [model popup](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/components/ModelPicker.tsx#L187), [Apps and copy feedback](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/components/Onboarding.tsx#L812), [settings](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/components/Settings.tsx#L488).

**Model discovery is a functional difference.** Ollama [merges recommendations and installed models](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/hooks/useModels.ts#L23), deduplicates entries and filters cloud entries when Cloud is disabled. Its [recommendations request](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/api.ts#L563) uses `GET /api/experimental/model-recommendations`; the [hook](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/ui/app/src/hooks/useFeaturedModels.ts) caches it for five minutes. Selecting a row saves the selection and closes the popup; it does not itself call the download API.

Racall currently discovers installed Ollama models through `/api/tags`; manual model IDs and explicit confirmed downloads are already available. A recommendations adapter should be optional, bounded by a timeout and fall back to installed models. Do not hardcode today's seven recommendations or equate a cloud listing with an authenticated account or entitlement. Retain explicit download confirmation and cancellation. The selected-model glyph issue identified in this audit was addressed during 0.2 finalization: it uses catalog metadata and avoids asserting a local type before an ambiguous Ollama ID is resolved.

**Apps are tool integrations, not chat providers.** Copying a launch command for Claude Code or Codex does not authenticate that tool or make it a Racall model backend. Ollama's current source also contains macOS desktop integrations that are excluded on Windows. Keep platform-specific entries explicit. The missing selectable command on clipboard failure identified in this audit was added during 0.2 finalization, with stale success feedback cleared. Recommendations, sidebar collapse and the larger layout adaptations remain proposals for a separately selected milestone.

The [Ollama app](https://github.com/ollama/ollama/blob/d1ed3fd13ac73f60cff00bbead8af24a68c4200d/app/README.md) uses Go and platform WebViews with a React frontend. Racall can adopt its interaction patterns within the existing Electron/React/Python structure; changing desktop frameworks is not required.

### NotebookLM alternatives: useful functional differences

| Reference workflow | Source evidence | Racall adaptation |
| --- | --- | --- |
| Open Notebook: sources, notes and chat | [Notebook page](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/frontend/src/app/%28dashboard%29/notebooks/%5Bid%5D/page.tsx) uses collapsible columns and mobile tabs. [Chat context](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/frontend/src/app/%28dashboard%29/notebooks/components/ChatColumn.tsx) exposes source/insight/note counts. | Keep source access close to Chat; show a compact context summary, with advanced controls expandable. Do not force three open columns on a narrow window. |
| Open Notebook: conversational context | [Chat graph](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/open_notebook/graphs/chat.py) supplies accumulated messages and persists graph state. | Racall saves transcripts, but its current chat route passes only the new question to `knowledge.answer`. Add bounded thread context, notebook isolation and citation-aware follow-up retrieval; persistence alone is not model memory. |
| Open Notebook: transformations | [Transformation graph](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/open_notebook/graphs/transformation.py) applies instructions to a source, validates output and persists an insight. | Start Studio with a few working outputs: summary, study guide and quiz; preserve source versions and allow saving as a Markdown note. |
| SurfSense: Studio | [Studio panel](https://github.com/MODSetter/SurfSense/blob/176aed261a24a85d217538960e91c59746561bd2/surfsense_local/frontend/src/features/studio/studio-panel.tsx) selects a format, ready sources and instructions; [format capabilities](https://github.com/MODSetter/SurfSense/blob/176aed261a24a85d217538960e91c59746561bd2/surfsense_local/backend/modules/artifacts/formats.py) govern availability. | Show only implemented formats and explain missing model capabilities. A working chat connection does not establish speech or image support. |
| SurfSense: jobs and artifacts | [Queues](https://github.com/MODSetter/SurfSense/blob/176aed261a24a85d217538960e91c59746561bd2/surfsense_local/backend/shared/queue.py) separate workloads. [Artifact records](https://github.com/MODSetter/SurfSense/blob/176aed261a24a85d217538960e91c59746561bd2/surfsense_local/backend/modules/artifacts/models.py) preserve files/checksums when a chat is deleted. | Durable jobs with progress, cancel/retry/restart and an output catalog; evaluate a small SQLite runner before adding a queue framework. |
| Slides and audio | SurfSense [dispatches output formats](https://github.com/MODSetter/SurfSense/blob/176aed261a24a85d217538960e91c59746561bd2/surfsense_local/backend/worker/studio/job_router.py); Open Notebook [separates outline/transcript/TTS and speaker profiles](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/open_notebook/podcasts/models.py). | Editable outline → structured slides → template renderer/export; reviewed script → separately configured speech → audio. These are later milestones, not completed Racall features. |

Racall evidence: [chat persistence and dispatch](../apps/api/on_knowledge/features/chats/router.py), [answer pipeline](../apps/api/on_knowledge/knowledge.py), [model service](../apps/api/on_knowledge/features/models/service.py), [model picker](../apps/web/features/models/ModelPicker.tsx), [Apps](../apps/web/features/apps/apps.tsx), [settings](../apps/web/features/settings/settings.tsx).

### Proposed order and acceptance

1. Finish 0.2 acceptance within the already agreed scope. Any chosen UI refinement must preserve EN/RU, source citations, notes, saved provider behavior and keyboard access. Keep publication on hold.
2. Adapt the compact model popup, collapsible sidebar and grouped settings. Introduce shared size tokens in feature styles rather than adding another layer of global overrides. Check light/dark/system themes, long model names, small windows, focus/Escape and clipboard failure.
3. Add optional model recommendations with installed/downloadable/cloud distinctions. Check missing/slow/unsupported recommendation endpoints, cloud visibility and duplicate IDs. Selecting a model must not download or load it.
4. Add bounded conversation context and clearer source controls after 0.2 acceptance. Test follow-up questions, isolated notebooks/threads, context limits, interrupted turns and preserved citation provenance.
5. Build jobs and the first Studio outputs for the 0.3 milestone, followed by editable slides and audio in later milestones. Verify restart/retry without duplicate outputs; evaluate actual EN/RU output with a real provider before claiming quality.

This audit reused no upstream code, assets or dependencies. It does not establish working cloud login, downloaded-model execution, generated-answer quality or native macOS/Linux parity. Future implementation still needs Racall's own acceptance checks.

## Historical snapshots: 2026-09-26

Pinned links below keep the findings reproducible even when upstream main changes.

| Project | Reviewed commit | Primary use for Racall |
| --- | --- | --- |
| [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook) | [`3127f14ea9db`](https://github.com/lfnovo/open-notebook/tree/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef) | Persistent conversations, podcast profiles and generation jobs |
| [MODSetter/SurfSense](https://github.com/MODSetter/SurfSense) | [`014e47a7efa1`](https://github.com/MODSetter/SurfSense/tree/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e) | Desktop workers, Studio dispatch and durable output files |
| [Anionex/Open-NotebookLM](https://github.com/Anionex/Open-NotebookLM) | [`36ecc9336eb5`](https://github.com/Anionex/Open-NotebookLM/tree/36ecc9336eb5fb9b9e91e48a057ef9fb010ea50a) | Slide generation stages, segmented speech and optional local TTS |

## Findings and adaptation decisions from 2026-09-26

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
