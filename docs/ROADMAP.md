# Racall roadmap

[Project home](../README.md) · [Changelog](../CHANGELOG.md)

Small, usable releases: **0.1 Beta → 0.2 Beta → 0.3 Beta**. Priorities may change with feedback; these are targets, not promised dates.

## Product direction — research, creation and connected notes

Racall aims to cover the major NotebookLM-style workflows alongside Obsidian-style connected Markdown notes: bring sources, ask grounded questions, create reusable materials, and keep the results linked to your knowledge. This is a development direction, not a claim of current feature parity or equivalent model quality.

Planned Studio outputs include reports, study guides, flashcards, quizzes, mind maps, data tables, slide decks, infographics, audio overviews and narrated video overviews. The source pipeline should gradually add scanned-document OCR, presentation/e-book import, audio transcription, permitted video transcripts, web discovery and selected connectors. Sharing, sync and mobile access remain longer-term work.

Use the [official product help](https://support.google.com/gemininotebook/?hl=en) and [Google's March 2026 feature update](https://workspaceupdates.googleblog.com/2026/03/new-ways-to-customize-and-interact-with-your-content-in-NotebookLM.html) as references for user workflows, not as promises of identical implementation. Targets below are provisional release groupings; split or reorder them based on testing and feedback.

Implementation references and acceptance criteria are maintained in [Reference projects](REFERENCE_PROJECTS.md). Review the relevant upstream code before each major workflow; verify the result in Racall rather than treating feature lists as tested capabilities.

## 0.1 Beta — Desktop foundation

Local notebooks and portable Markdown; PDF/MD/TXT/DOCX/URL import; search and cited answers; limited research with a critic; read-only MCP; English/Russian UI; Windows/macOS/Linux packaging. See [release notes](releases/0.1.0-beta.1.md) for testing status and limits.

## 0.2 Beta — Everyday reliability

- Persistent chat history and safer note draft recovery/autosave.
- Rename/delete notebooks with clear confirmation and recovery safeguards.
- Source refresh/version tracking and better import failure handling.
- Real cloud/Ollama model evaluation on a fixed test corpus.
- Manual installation checks, signing/notarization when certificates are available.
- Parser workers with time and memory limits.

## 0.3 Beta — Research and the first Studio tools

- Durable research and generation jobs, cancellation, progress and recovery.
- A Studio area with saved, regenerable outputs tied to the selected source versions.
- Start with reports/study guides, then flashcards, quizzes and mind maps as quality allows.
- Better retrieval evaluation, reranking and scalable vector lookup.
- Improved PDF/table handling and a richer Markdown editor.
- Additional interface languages from maintained translations.

## 0.4 Beta target — Presentations and visual summaries

- Source-grounded slide outlines and editable slides, with PPTX/PDF export.
- Review and revise individual slides before exporting; retain source references in the deck or its companion notes.
- Template-based layouts first; optional generated illustrations, infographics and data tables after factual and export checks.

## 0.5 Beta target — Audio

- Read-aloud playback and saved audio summaries, followed by scripted two-speaker overviews.
- Reviewable scripts linked to sources, voice/language settings and audio export.
- Dedicated speech-provider settings and optional local speech engines after hardware, language and redistribution-license validation.
- Audio import/transcription with timestamps so spoken-source citations remain inspectable.

## 0.6 Beta target — Narrated video

- Combine reviewed slides, narration and subtitles into exportable video overviews.
- Reuse the presentation/audio pipeline and background generation jobs.
- Evaluate richer animation and generated visuals separately; cinematic generation is exploratory, not a guaranteed milestone.

## Shared requirements for generated materials

- Keep source versions and references inspectable; flag unsupported statements and allow edits before export.
- Persist output, status and generation settings; support cancellation and recovery after restart.
- Configure text, speech, transcription and image providers by capability. A chat-compatible endpoint does not imply support for every media task.
- Explain which source material leaves the device and require an explicit generation action; show cost information where the provider makes it available. Free application code does not make hosted inference free.
- Evaluate factual grounding, English/Russian output quality, export fidelity, latency and resource use before claiming a feature works reliably. Existing deterministic mock tests alone are insufficient.

## Later

Sync, sharing and mobile experiences; remote MCP with OAuth; server profiles and multiuser isolation; broader source connectors and web research. Continue improving backlinks and Markdown editing alongside Studio. Treat a visual note graph and graph-assisted retrieval as separate features; adopt graph retrieval only if it improves measured retrieval quality.

The initial [technical specification](OpenNotebook_Technical_Spec.md) describes a broader destination, including PostgreSQL/pgvector and Redis. The desktop beta uses a local SQLite index and does not claim completion of that full plan. [Architecture decisions](adr) record the tradeoffs.
