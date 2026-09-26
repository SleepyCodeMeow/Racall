# Contributing to Racall

Bug reports, focused fixes and translations are welcome. Use [Issues](https://github.com/SleepyCodeMeow/Racall/issues/new/choose) to discuss larger changes first.

## Contribution licensing

Contributors keep copyright in their own work. By intentionally submitting a contribution for inclusion, you license that contribution under the target component's existing terms: Apache-2.0 for the Python service and tools; AGPL-3.0-only for the UI, desktop shell, shared UI resources and installer. See [LICENSING.md](LICENSING.md) for exact scope and legacy MIT rights.

Submit only work you have permission to license on those terms. Retain third-party notices and identify any differently licensed material in your pull request. No copyright assignment or blanket permission to relicense your contribution is required. Both component licenses permit commercial use under their respective conditions.

## Reference-driven feature work

For source ingestion, chat, Studio, presentation or audio changes, consult [Reference projects](docs/REFERENCE_PROJECTS.md). Record the relevant upstream commit and implementation paths, explain the adaptation to Racall, and define acceptance checks. Distinguish source inspection from runtime verification. If reusing code, record provenance and preserve applicable license notices; do not assume every directory or model has the repository root license.

## Local development

Use Node.js 24, Python 3.12 and uv. Clone the repository, then run `npm ci` and `uv sync --frozen`, or use `scripts/setup.ps1` / `scripts/setup.sh`. Run `npm run dev` to start the frontend and desktop app. Use an isolated `OPENNOTEBOOK_DATA_DIR` for experiments involving storage.

Before a pull request:

```sh
npm test -- -q
npm run lint
npm run test:i18n
npm run check:release
npm run build
npm run typecheck
npm run test:desktop
```

On headless Linux, run the desktop test under `xvfb-run -a`. Build installers on their target OS with `npm run dist`. The CI matrix covers Windows x64, macOS arm64/x64 and Linux x64.

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

The public version is 0.1 Beta (`0.1.0-beta.1` in package metadata). Follow [RELEASING.md](docs/RELEASING.md) for version updates and prereleases. Signing and platform installation checks must be described truthfully.
