# Changelog

## 0.3.0-beta.1 — 0.3 Beta — 2026-10-25

Selected evidence, conversational context and reusable text materials, with native x64/ARM64 packages for Windows, macOS and Linux.

### Added

- Bounded active-thread history for follow-up questions; saved assistant prose remains context rather than factual evidence.
- Explicit source and saved-note selection for chat, Research and Studio, including empty context, persisted selection and revision-specific note citations.
- Durable Research/Studio jobs with stage progress, duplicate-submission protection, queued/running cancellation and explicit retry after failure or interruption. Restart does not automatically replay inference.
- Three Studio text formats: summary, study guide, and review questions with answers.
- A material library with cited Markdown export and independent editable note copies, including access to earlier 0.2 Research reports.
- Windows ARM64, macOS Intel x64/Apple Silicon ARM64, and Linux x64/ARM64 distributions alongside Windows x64; separate macOS DMG/ZIP and Linux AppImage/DEB packages.

### Changed and hardened

- Split Python retrieval, generation, document processing and completion protocols into responsibility-based modules; separate feature execution, frontend controllers/views and Electron lifecycle/security/native actions.
- Reuse one Markdown note parser for editing and context snapshots; add a contributor development guide, updated code map and formatting checks.
- Check selected context and saved AI configuration around generation, fence cancelled/interrupted results and reject an empty model name before persisting a generation job.
- Add shared evidence-scope instructions and recorded semantic regression fixtures, while retaining the known limitations of model-based critique.

### Verification and limits

- Six native candidate targets passed 499 Python tests each, packaged application scenarios and native installation/copy checks. A separate installed Windows x64 0.2 → 0.3 upgrade preserved existing knowledge and historical citations; see the [candidate report](docs/CANDIDATE_VERIFICATION_03_2026-10-25.md).
- One Windows/local Ollama configuration completed 25 functional scenarios. Earlier accepted unsupported claims remain evidence that the critic is not a factual guarantee; see the [model report](docs/MODEL_EVALUATION_03_2026-10-25.md). Generated claims and materials need review.
- Windows/macOS distributions are unsigned; macOS is not notarized. Native CI does not establish every OS/device, AppImage FUSE or live-provider configuration. Embeddings and other live models/providers were outside the local acceptance run.
- The owner approved publication on October 25, 2026 with these beta limits. Stable semantic verification remains uncertified. Presentations/audio/video generation, OCR, mobile and sync are outside this release.

See the [release notes](docs/releases/0.3.0-beta.1.md) for downloads, changes, upgrade guidance and known limits.

## 0.2.0-beta.1 — 0.2 Beta — 2026-10-19

Windows x64 release. Current Linux and macOS desktop packages are not included; earlier 0.1 downloads remain unchanged.

### Added

- Persistent notebook chats with saved answers, search results and citation snapshots, chat rename/removal and interrupted-request recovery without automatic replay.
- Serialized Markdown autosave, durable recovery drafts, external-edit conflict handling and a save-copy option.
- Notebook rename, recoverable trash/restore and protection during active model/import operations.
- Source file replacement and website refresh, preserving historical originals, passages and citation versions.
- Separate AI profiles for OpenAI, Claude, Ollama Local/Cloud and llama.cpp, plus custom OpenAI-compatible connections and independent optional embeddings. Claude uses its native Messages API.
- Light, Dark and System appearance; a searchable model picker using the saved connection's catalog; manual model IDs.
- Explicitly confirmed local Ollama downloads with streamed layer progress, cancellation and interrupted-download recovery.
- Apps with fixed Ollama launch commands for external coding tools. Commands are copied for manual use and never executed by Racall.
- Compact light Windows installer with a native frame, English/Russian selection, automatic installation location and an extraction progress screen.
- Feature folders, a contributor code map and an opt-in EN/RU model-evaluation kit.

### Fixed and hardened

- Preserve notes across delayed saves, unsavable navigation, delayed notebook creation and recovered editor conflicts.
- Recover interrupted Research sessions after restart, preserving saved steps without repeating model requests.
- Keep the last working source and index when a replacement fails; retain access to old citations after updates.
- Isolate file/web parsing in a supervised process with time and memory limits.
- Validate explicit claim references, repair answer-language mismatches within bounded attempts and localize Research headings.
- Bound internal completion streams, response size and deadlines; reject truncated/aborted output as an answer without automatically retrying inference.
- Offer a selectable command when clipboard copying fails and clear stale success feedback.
- Use catalog metadata for cloud/local/server model icons, keeping unresolved aliases neutral after restart.

### Verification and limits

- [Release-tag CI](https://github.com/SleepyCodeMeow/Racall/actions/runs/39257810891) passed 404 backend tests, 374-key EN/RU checks, production builds and the full Windows packaged regression suite, including 15 workbench groups, 14 persistence scenarios and both frozen-service exercises. Native installer language selection and NSIS install/uninstall with knowledge preservation also passed on a disposable host.
- Final provider checks use deterministic HTTP fixtures. Final live-provider acceptance and an owner's hands-on review were not performed; early-user feedback is welcome.
- Windows installer is unsigned. Back up the knowledge folder with Racall closed before upgrading. Saved chat history is not yet model context; sync, mobile, OCR, presentations/audio generation and remote MCP/OAuth remain outside this release.

See the [release notes](docs/releases/0.2.0-beta.1.md) for downloads, verification scope and upgrade guidance.

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
