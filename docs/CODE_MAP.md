# Code map

Start here when changing Racall. [Contributing](../CONTRIBUTING.md) · [Roadmap](ROADMAP.md)

The application is a modular desktop monolith: Electron starts one Python service and a static React interface. Feature folders contain the code for a user-facing section. Shared infrastructure stays small and explicitly named.

## Find a feature

| Change | Interface | Python service |
| --- | --- | --- |
| Chat history, selection and sending | [chat](../apps/web/features/chat/chat.tsx) | [chat routes](../apps/api/on_knowledge/features/chats/router.py), [transcript service](../apps/api/on_knowledge/features/chats/service.py) |
| Answer rendering and citation buttons | [answer view](../apps/web/features/chat/answer-view.tsx) | [retrieval and answer validation](../apps/api/on_knowledge/knowledge.py) |
| Cited answer generation and verifier protocol | — | [writer](../apps/api/on_knowledge/claim_generation.py), [claim-ID verifier](../apps/api/on_knowledge/claim_verification.py), [EN/RU prose policy](../apps/api/on_knowledge/answer_language.py) |
| Note editor and recovery actions | [notes](../apps/web/features/notes/notes.tsx) | [note routes](../apps/api/on_knowledge/features/notes/router.py) |
| Autosave, draft recovery and conflict handling | [editor hook](../apps/web/features/notes/use-note-editor.ts) | [note repository](../apps/api/on_knowledge/features/notes/repository.py), [request schemas](../apps/api/on_knowledge/features/notes/schemas.py) |
| Notebook rename, trash and restore | [notebook list/management](../apps/web/features/notebooks/notebook-list.tsx) | [notebook routes](../apps/api/on_knowledge/features/notebooks/router.py), [notebook repository](../apps/api/on_knowledge/features/notebooks/repository.py) |
| Source import/status | [sources](../apps/web/features/sources/source-panel.tsx) | [source routes](../apps/api/on_knowledge/features/sources/router.py), [import service](../apps/api/on_knowledge/features/sources/service.py) |
| Source versions, replacement and historical citations | [source details](../apps/web/features/sources/source-detail.tsx) | [source repository](../apps/api/on_knowledge/features/sources/repository.py) |
| Parser time/memory isolation | — | [supervisor](../apps/api/on_knowledge/features/sources/parser.py), [worker](../apps/api/on_knowledge/features/sources/parser_worker.py), [format parsers](../apps/api/on_knowledge/ingestion.py) |
| Research and saved reports | [research](../apps/web/features/research/research-panel.tsx) | [research routes](../apps/api/on_knowledge/features/research/router.py), [startup recovery](../apps/api/on_knowledge/features/research/service.py), [research engine](../apps/api/on_knowledge/knowledge.py), [Markdown export](../apps/api/on_knowledge/features/research/export.py) |
| Models and language preferences | [settings](../apps/web/features/settings/settings.tsx) | [settings routes](../apps/api/on_knowledge/features/settings/router.py), [providers](../apps/api/on_knowledge/providers.py) |
| Provider selection, credentials and profiles | [provider controls](../apps/web/features/settings/provider-connection.tsx), [embedding controls](../apps/web/features/settings/embedding-settings.tsx) | [profile normalization](../apps/api/on_knowledge/provider_settings.py), [completion factory](../apps/api/on_knowledge/provider_factory.py), [Claude adapter](../apps/api/on_knowledge/anthropic_provider.py) |
| Model picker, discovery and explicit downloads | [model picker](../apps/web/features/models/ModelPicker.tsx), [model type icons](../apps/web/features/models/model-type-icon.tsx), [query/download hooks](../apps/web/features/models/use-models.ts), [download progress](../apps/web/features/models/download-status.tsx) | [model routes](../apps/api/on_knowledge/features/models/router.py), [catalog/download service](../apps/api/on_knowledge/features/models/service.py) |
| External coding-tool launch commands | [Apps](../apps/web/features/apps/apps.tsx), [fixed launcher catalog](../apps/web/features/apps/catalog.ts) | —; clipboard only, manual launch in the user's terminal |
| Light, dark and system appearance | [theme context](../apps/web/lib/theme.tsx), [appearance controls](../apps/web/features/settings/appearance.tsx), [theme tokens](../apps/web/app/themes.css), [workbench layout](../apps/web/app/workbench.css) | [appearance routes](../apps/api/on_knowledge/features/appearance/router.py); native window theme in [Electron](../apps/desktop/main.cjs) |
| Connecting other AI clients | [connections](../apps/web/features/connections/connect.tsx) | [connection routes](../apps/api/on_knowledge/features/connections/router.py), [MCP](../apps/api/on_knowledge/mcp_server.py) |

## Shared infrastructure

- [API application](../apps/api/on_knowledge/app.py): service composition, startup/recovery, authorization, CORS, errors and static web hosting. Feature endpoints belong in feature routers.
- [Store](../apps/api/on_knowledge/storage.py): notebook paths, atomic file operations, retrieval database, audit log and a compatibility facade for notes. Note-specific file logic lives in the note repository.
- [Completion transport](../apps/api/on_knowledge/completion_stream.py): bounded SSE/JSON handling, idle and total deadlines. [Providers](../apps/api/on_knowledge/providers.py) bind it to model settings and safe service diagnostics; embedding requests retain their separate transport.
- [Claude stream parser](../apps/api/on_knowledge/anthropic_stream.py): native Messages events, text-only JSON assembly and terminal-state checks. It shares HTTP/framing limits with the Chat Completions transport.
- [HTTP client and shared types](../apps/web/lib/api.ts): service requests, error status and data types. Feature state belongs in its feature folder.
- [Markdown renderer](../apps/web/components/markdown.tsx): shared display component.
- [Translations](../apps/shared/locales): English and Russian catalogs. [Localization guide](LOCALIZATION.md).
- [Electron lifecycle](../apps/desktop/main.cjs): service process, window and trusted native actions. [Installer](../installer) contains Windows installer customization.
- [Styles](../apps/web/app): shared layout/style sheets. Keep feature-specific rules labelled and scoped; avoid global selectors for a single section.

## Tests and commands

- [Core workflow tests](../tests/test_knowledge.py): imports, retrieval, citation validation and Markdown metadata.
- [Verifier contract tests](../tests/test_claim_verification.py), [answer workflow tests](../tests/test_answer_generation.py), [EN/RU policy tests](../tests/test_answer_language.py), [Research export tests](../tests/test_research_export.py): recorded model failures, bounded repairs, exact citations and export language.
- [Completion transport tests](../tests/test_provider_completion.py) and [provider binding tests](../tests/test_provider_transport.py): complete-stream framing, real HTTP deadlines, size limits, interrupted/invalid output, reasoning separation and safe diagnostics without automatic inference retries.
- [Claude protocol tests](../tests/test_anthropic_provider.py), [profile tests](../tests/test_provider_settings.py) and [routing tests](../tests/test_provider_routing.py): native protocol, old-settings migration, key isolation, independent embeddings and cited-answer/Research routing. [Provider desktop check](../scripts/smoke-providers.cjs) covers actual settings/restart behavior; [setup guide](PROVIDERS.md).
- [Model catalog/download tests](../tests/test_models.py) and [appearance tests](../tests/test_appearance.py): bounded metadata requests, explicit/cancelled/interrupted downloads, preference validation and persistence. [Workbench desktop check](../scripts/smoke-workbench.cjs) uses a loopback fixture instead of downloading real model weights; [interface guide](WORKBENCH.md).
- [Persistence tests](../tests/test_persistence.py): history, idempotent requests, restart recovery, note revision conflicts and I/O failures.
- [Research recovery tests](../tests/test_research_recovery.py): interrupted startup sessions, unchanged completed results and no automatic model replay. Workspace exit guards live in [page.tsx](../apps/web/app/page.tsx) and use [pending edits](../apps/web/lib/pending-edits.ts) before unmounting the note editor.
- [0.2 maintenance tests](../tests/test_release02.py): notebook trash/restore, source history, failed promotions, legacy sources, parser limits and publication hold. [Desktop maintenance scenario](../scripts/smoke-maintenance.cjs); [native installer checks](../scripts/check-installer.cjs).
- [Persistence desktop check](../scripts/smoke-persistence.cjs): real app restarts, restored citations, typing during a delayed save, recovered drafts, notebook isolation and EN/RU controls. Uses a deterministic local model stub, not a paid API.
- `npm test -- -q`, `npm run lint`, `npm run typecheck`, `npm run test:i18n`, `npm run check:release`.
- `npm run build:web` then `npm run test:persistence` for the development desktop. `npm run test:packaged` also runs the persistence scenario against a packaged executable.

- [Real-model evaluation](../scripts/evaluate_model.py) is opt-in; [fixture and guide](MODEL_EVALUATION.md).
- [Publication policy](../apps/shared/release.json) controls the explicit hold. See [release checklist](RELEASE_02_CHECKLIST.md).

## Adding a section

Use matching feature names under `apps/web/features/` and `apps/api/on_knowledge/features/`. Place route handlers in `router.py`, substantial validation in `schemas.py`, workflow logic in a service, and file/database operations in a repository when that distinction is useful. A small feature does not need empty service layers.

Keep JSX focused on rendering; extract long asynchronous state/lifecycle logic into a named hook. Use explicit imports and names that explain the responsibility. Avoid catch-all `utils` or `manager` files and unrelated behavior in the application shell. Follow the [reference-project review process](REFERENCE_PROJECTS.md) before implementing a substantial new workflow.

Existing retrieval, ingestion and provider modules remain shared engine modules. Split them further when feature growth warrants it; do not silently change their public behavior during a directory move.

## Windows installer styling

See `installer/README.md`: `appearance.nsh` controls light colors and typography, `assets/` holds logo bitmaps, and `scripts/build_installer_assets.py` regenerates them. The compact first screen lives in `welcome.nsh`, its translations in `catalog.json`, the reference window layout in `layout.nsh`, and the parent handoff in `selection.nsh`. Keep language seeding in `languages.nsh` separate from styling.

`apps/api/on_knowledge/evidence_references.py` prepares short, request-local model citation labels. `knowledge.py` validates them exactly and restores canonical IDs before returning or saving an answer.
