# Racall roadmap

[Project home](../README.md) · [Changelog](../CHANGELOG.md)

Small, usable releases: **0.1 Beta → 0.2 Beta → 0.3 Beta**. Priorities may change with feedback; these are targets, not promised dates.

## 0.1 Beta — Desktop foundation

Local notebooks and portable Markdown; PDF/MD/TXT/DOCX/URL import; search and cited answers; limited research with a critic; read-only MCP; English/Russian UI; Windows/macOS/Linux packaging. See [release notes](releases/0.1.0-beta.1.md) for testing status and limits.

## 0.2 Beta — Everyday reliability

- Persistent chat history and safer note draft recovery/autosave.
- Rename/delete notebooks with clear confirmation and recovery safeguards.
- Source refresh/version tracking and better import failure handling.
- Real cloud/Ollama model evaluation on a fixed test corpus.
- Manual installation checks, signing/notarization when certificates are available.
- Parser workers with time and memory limits.

## 0.3 Beta — Better research

- Durable research jobs, cancellation, progress and recovery.
- Better retrieval evaluation, reranking and scalable vector lookup.
- Improved PDF/table handling and a richer Markdown editor.
- Additional interface languages from maintained translations.

## Later

Sync and mobile experiences; remote MCP with OAuth; server profiles and multiuser isolation; OCR, media and selective connectors. Add graph retrieval only if it improves measured retrieval quality.

The initial [technical specification](OpenNotebook_Technical_Spec.md) describes a broader destination, including PostgreSQL/pgvector and Redis. The desktop beta uses a local SQLite index and does not claim completion of that full plan. [Architecture decisions](adr) record the tradeoffs.
