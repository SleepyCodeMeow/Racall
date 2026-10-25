# Contributing to Racall

Bug reports, focused fixes and translations are welcome. Use [Issues](https://github.com/SleepyCodeMeow/Racall/issues/new/choose) to discuss larger changes first.

## Contribution licensing

Contributors keep copyright in their own work. By intentionally submitting a contribution for inclusion, you license that contribution under the target component's existing terms: Apache-2.0 for the Python service and tools; AGPL-3.0-only for the UI, desktop shell, shared UI resources and installer. See [LICENSING.md](LICENSING.md) for exact scope and legacy MIT rights.

Submit only work you have permission to license on those terms. Retain third-party notices and identify any differently licensed material in your pull request. No copyright assignment or blanket permission to relicense your contribution is required. Both component licenses permit commercial use under their respective conditions.

## Reference-driven feature work

For source ingestion, chat, Studio, presentation or audio changes, consult [Reference projects](docs/REFERENCE_PROJECTS.md). Record the relevant upstream commit and implementation paths, explain the adaptation to Racall, and define acceptance checks. Distinguish source inspection from runtime verification. If reusing code, record provenance and preserve applicable license notices; do not assume every directory or model has the repository root license.

## Code organization

Use the [development tour](docs/DEVELOPMENT.md), [code map](docs/CODE_MAP.md) and
[architecture boundaries](docs/ARCHITECTURE.md) to find the section you want to
change. Keep feature UI and Python routes in their named folders. Separate
substantial state/save logic from rendering; avoid unrelated handlers in the app shell.

Run `npm run format` to apply Ruff to Python and pinned Prettier to maintained
JavaScript, TypeScript and CSS. `npm run format:check` checks the same files in CI.
Keep a module together while it has one clear responsibility; do not introduce
empty layers or split each function into a separate file.

Python is the primary application language. Put document processing, retrieval,
AI/provider logic, generation workflows and durable storage in the Python service.
TypeScript/JavaScript and CSS are for the interface and desktop integration. Follow
the [architecture and language boundaries](docs/ARCHITECTURE.md); do not move
business logic to the frontend or duplicate it in both languages.

## Local development

Use Node.js 24, Python 3.12 and uv. Clone the repository, then run `npm ci` and `uv sync --frozen`, or use `scripts/setup.ps1` / `scripts/setup.sh`. Run `npm run dev` to start the frontend and desktop app. Use an isolated `OPENNOTEBOOK_DATA_DIR` for experiments involving storage.

Before a pull request:

```sh
npm test -- -q
npm run lint
npm run format:check
npm run test:i18n
npm run check:release
npm run build
npm run typecheck
npm run test:desktop
npm run test:languages
npm run test:persistence
npm run test:maintenance
```

On headless Linux, run the desktop test under `xvfb-run -a`. Build installers on
their target OS with `npm run dist`. CI selects candidates from
`apps/shared/release.json`: x64 and ARM64 for Windows, macOS and Linux. These are
build targets, not a statement that every current candidate passed acceptance.
See the [native candidate plan](docs/NATIVE_CANDIDATES_03.md). The current public
0.2 download remains Windows x64.

## Project map

- `apps/api/on_knowledge`: Python service, ingestion, retrieval, storage, providers and MCP.
- `apps/web`: TypeScript React UI and CSS.
- `apps/desktop`: Electron lifecycle, local service authentication and native integration.
- `apps/shared/locales`: English and Russian strings.
- `installer`: Windows installer customization.
- `tests`, `scripts`: backend checks, desktop smoke tests and release tooling.

Keep originals and Markdown as the source of truth; do not move user data during cosmetic changes. Never commit credentials, private documents, generated bundles or local logs. Generated files must not distort GitHub language statistics; do not relabel maintained code to manipulate the bar.

Add a regression check when fixing data loss, security boundaries or retrieval correctness. Explain user-visible behavior and validation in the pull request. See [localization](docs/LOCALIZATION.md) to add a language.

## Releases

The current public version is **0.2 Beta** for Windows x64. Development toward
**0.3 Beta** uses `0.3.0-beta.1` package metadata with publication on hold. Follow
[RELEASING.md](docs/RELEASING.md) for version updates and prereleases. Signing and
platform installation checks must be described truthfully.
