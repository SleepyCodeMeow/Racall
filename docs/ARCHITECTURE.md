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

## The interface presents and requests

`apps/web` uses React/TypeScript and CSS for screens, controls, accessibility,
themes, translations, drafts and temporary UI state. It calls the Python API to
perform application operations. Polling job status, displaying progress and
downloading an already generated Markdown document are interface responsibilities.

Do not duplicate Python retrieval, inference, evidence verification or generation
workflows in the frontend. Disabling a button is useful feedback, but Python must
also enforce every validation and consistency rule.

`apps/desktop` uses Electron/JavaScript for starting the bundled Python service,
window lifecycle, system integration and narrowly scoped trusted native actions.
Keep document and AI business logic out of this bridge.

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
