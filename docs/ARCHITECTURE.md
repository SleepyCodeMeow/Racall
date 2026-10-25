# Architecture and language boundaries

Racall is a Python application with a web-based desktop interface. Python is the
primary implementation language for application behavior. TypeScript, JavaScript
and CSS provide the interface and the native desktop bridge.

## Python owns application behavior

Keep these responsibilities in `apps/api/on_knowledge`:

- Document import, parsing, source versions and citation provenance.
- Retrieval, context selection validation, bounded conversation history and evidence checks.
- Model/provider communication, credentials and generation policies.
- Research and Studio workflows, durable jobs, cancellation, retry and recovery.
- Notebook, note, chat and material persistence, revisions and access validation.

Organize a growing feature under its own `features/<name>/` folder. Routes expose
the API, schemas validate input, services implement workflows, and repositories
handle durable storage where this separation is useful. Shared engines stay in
small modules with explicit responsibilities. See the [code map](CODE_MAP.md).

The public [Knowledge facade](../apps/api/on_knowledge/knowledge.py) delegates to
[retrieval](../apps/api/on_knowledge/retrieval) for evidence selection/ranking and
[generation](../apps/api/on_knowledge/generation) for cited answers and Research.
The [ingestion facade](../apps/api/on_knowledge/ingestion.py) keeps the parser worker
contract while [documents](../apps/api/on_knowledge/documents) owns normalized
models, local parsing, text blocks, chunk provenance and bounded web fetching.
The [completion transport facade](../apps/api/on_knowledge/completion_stream.py)
owns HTTP requests, deadlines and scoped cancellation; [completion](../apps/api/on_knowledge/completion)
contains strict payload decoding, bounded SSE framing and the Chat Completions state machine.

Feature services keep state and safety decisions close to their owner.
[Model discovery](../apps/api/on_knowledge/features/models/catalog.py) and
[protocol decoding](../apps/api/on_knowledge/features/models/protocol.py) do not own
the [download lifecycle](../apps/api/on_knowledge/features/models/service.py).
[Job execution](../apps/api/on_knowledge/features/jobs/execution.py) uses the accepted
snapshot inside the [job service's](../apps/api/on_knowledge/features/jobs/service.py)
credential/cancellation scope; the service retains its single worker, locks and final
commit checkpoint. [Markdown decoding](../apps/api/on_knowledge/features/notes/markdown.py)
is shared by note persistence and context snapshots so titles, bodies and revision hashes agree.

## The interface presents and requests

`apps/web` uses React/TypeScript and CSS for screens, controls, accessibility,
themes, translations, drafts and temporary UI state. It calls the Python API to
perform application operations. Polling job status, displaying progress and
downloading an already generated Markdown document are interface responsibilities.

[page.tsx](../apps/web/app/page.tsx) composes providers and the
[workspace](../apps/web/features/workspace/workspace.tsx). Workspace navigation,
queries and pending-edit guards live in [use-workspace](../apps/web/features/workspace/use-workspace.ts);
navigation, panels and dialogs are named view components. Chat and source details
follow the same split: [use-chat](../apps/web/features/chat/use-chat.ts) and
[use-source-detail](../apps/web/features/sources/use-source-detail.ts) own temporary
state and requests; their components render controls, transcripts and document previews.

The public [web API facade](../apps/web/lib/api.ts) re-exports the HTTP client,
DTOs, original-file retrieval and evidence location labels from [lib/api](../apps/web/lib/api).
[Desktop bridge declarations](../apps/web/lib/desktop.d.ts) describe the preload surface.
Styles are composed in [layout.tsx](../apps/web/app/layout.tsx): ordered entry-point
imports keep the cascade while shared foundations live in `app/styles/` and
feature rules live next to their section. Preserve import order and selectors when moving CSS.

Do not duplicate Python retrieval, inference, evidence verification or generation
workflows in the frontend. Disabling a button is useful feedback, but Python must
also enforce every validation and consistency rule.

`apps/desktop` uses Electron/JavaScript for starting the bundled Python service,
window lifecycle, system integration and narrowly scoped trusted native actions.
Keep document and AI business logic out of this bridge.

[main.cjs](../apps/desktop/main.cjs) owns lifecycle and shutdown ordering.
[Runtime](../apps/desktop/runtime.cjs) owns existing profile paths;
[backend](../apps/desktop/backend.cjs) owns the Python process and readiness;
[security](../apps/desktop/security.cjs) owns session headers, CSP, sender checks and navigation;
[window](../apps/desktop/window.cjs) owns appearance and the unsaved-edit dialog;
[native actions](../apps/desktop/native-actions.cjs) registers only fixed IPC capabilities.
The sandbox-compatible [preload](../apps/desktop/preload.cjs) stays narrow and never exposes the bearer token.

## Data and release boundaries

Original documents, Markdown and portable JSON metadata are authoritative. The
SQLite retrieval index is rebuildable; it must not become the sole store for jobs,
chat history or generated materials. Store credentials in the OS keychain and
retain execution snapshots only in memory where secrets are involved.

The installer bundles the runtime; end users do not need to install Python or
Node.js. Contributors need both toolchains because the desktop interface and
Python service have separate build steps.

GitHub's language bar reports repository source sizes. It is not an architecture
setting or a release acceptance goal. Keep generated/vendor files classified
honestly; do not add filler code or hide maintained TypeScript to change the bar.

## Contributor conventions

Split files when their responsibilities or lifecycles differ, not to satisfy a
line-count target. Prefer explicit names and imports, small public facades and
feature-local state over generic helper containers or empty layers. A structural
refactor must preserve API/IPC contracts, persistent paths, execution-local
credentials, cancellation/commit fences and OS-specific behavior.

Run `npm run format` to apply Ruff's Python formatter and Prettier 3.9.10 to
web/desktop/script sources; `npm run format:check` verifies the same formatting.
Formatting does not replace lint, type checking or behavior tests. See
[development setup](DEVELOPMENT.md) and the [code map](CODE_MAP.md) for commands and entry points.
