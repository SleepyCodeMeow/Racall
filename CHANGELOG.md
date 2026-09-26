# Changelog

## 0.2 Beta — unreleased, first development slice

- Notebook rename, recoverable trash/restore and protection during active operations.
- Source replacements, website refresh, historical originals/citations and failed-update recovery.
- Isolated file/web parsers with time and memory supervision.
- Native installer CI checks, an opt-in model evaluation kit and an explicit publication hold.

- Persistent notebook chats with saved citation snapshots, rename/delete and interrupted-request recovery.
- Serialized note autosave, durable recovery drafts and external-edit conflict handling.
- Feature folders for API routes and interface sections, plus a contributor code map.
- Full 0.2 scope and native platform verification remain in progress; 0.1 release assets are unchanged.

## Repository documentation update — no new application version

- Apache-2.0 for the Python core/tools, AGPL-3.0-only for the UI/desktop components; contribution scope and legacy MIT grants documented.
- README layout aligned with the project reference: logo, divider, description, navigation, screenshot and download table.
- Existing 0.1 Beta tag, installers and original MIT grants are unchanged.

## 0.1.0-beta.1 — 0.1 Beta

First public beta of Racall, focused on a local desktop knowledge workspace.

### Added

- Local notebooks, portable Markdown notes, frontmatter and wikilinks.
- Text PDF, Markdown, TXT, DOCX and public HTML URL imports.
- Text search, optional embeddings, cited answers and passage inspection.
- Research planning, retrieval and model critique, with saved reports.
- OpenAI-compatible and Ollama provider settings; OS keychain credentials.
- Read-only MCP access scoped to one notebook.
- English and Russian interface; Windows installer language selection.
- Raccoon branding, desktop packaging and GitHub build/release workflows.

### Known limitations

Unsigned installers, no macOS notarization or automatic updater. No mobile apps or sync. Chat history is not persisted; research stops when the app closes. No OCR, source refresh, notebook rename/delete, graph view or remote MCP/OAuth. Automated AI checks use mocks; real-model evaluation remains pending.

See the [release notes](docs/releases/0.1.0-beta.1.md) and [roadmap](docs/ROADMAP.md).
