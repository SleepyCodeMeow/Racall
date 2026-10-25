# 0.3 development verification — October 25, 2026

Branch: `codex/0.3-context-studio`, based on
`38be1aed934b0f3ef2769332c1582206b3d83dfa`. The checked changes are local working
tree changes at the initial development check, not a released installer.
Publication remains on hold. The published 0.2 tag and assets were not changed.

Later on the same day, the expanded six-target native matrix passed with 486
Python tests per target. That separate source/run/package evidence is recorded in
[the native verification report](NATIVE_VERIFICATION_03_2026-10-25.md); the checks
below retain the initial development snapshot and its original test count.

## Completed checks

- Python suite: **462 passed**, using `.venv/Scripts/python.exe scripts/test.py -q -p no:cacheprovider`.
- Ruff: passed for the API, tests and the existing configured Python build/evaluation tools.
- Release consistency: `0.3.0-beta.1` / Python `0.3.0b1`, explicit publication hold.
- Localization: **448** matching EN/RU keys, placeholders, service messages and existing preference checks.
- Production static frontend build and TypeScript: passed with webpack, one configured Next.js worker and a 1,536 MB Node heap limit.
- `node scripts/smoke-studio.cjs`: passed against the development Electron + Python application with GPU disabled, an isolated knowledge directory, an isolated Chromium profile and a synthetic loopback completion provider.
- `node scripts/smoke-persistence.cjs`: passed for the existing chat/note recovery and edit-conflict scenarios against the updated development app.
- `node scripts/smoke-workbench.cjs`: passed for Apps, provider/model selection, explicit synthetic download/cancellation, EN/RU, light/dark/system theme, restart and minimum-window layout; zero inference, real-model downloads or unexpected external requests.
- JavaScript syntax checks and `git diff --check`: passed.

The Python run emits a Starlette TestClient/httpx deprecation warning. No test
failed; changing the HTTP test dependency is outside this feature slice.

## What the new desktop scenario checks

Selected-note chat, exclusion of another source from writer input, bounded
follow-up history, restored thread selection and saved note-citation snapshots;
all three Studio formats with verified canonical citations; editable note copy
and a real Markdown download into the test directory; cancellation of an idle
HTTP stream and explicit retry; restart without inference replay and retained
materials; English/light and Russian/dark controls; keyboard context controls
and the 1,000×680 minimum window without horizontal document overflow.

The fixture records completion protocol requests and supports writer/critic
responses. It does not run an AI model. Existing backend tests additionally cover
context revisions, selection before FTS/embedding ranking, provider/credential
snapshots, single-worker queue ordering, cancellation races, crash recovery
between material and job commits, and legacy 0.2 reports without duplicate entries.

Local ignored artifacts:

- `test-results/studio-desktop-1792936515312/result.json`, exported Markdown and EN/RU/minimum-window screenshots.
- `test-results/persistence-1792936235445/result.json` and its recovery screenshots.
- `test-results/workbench-desktop-1792936600517/result.json`, layout/contrast checks and workbench screenshots.

Screenshots were inspected for the new Studio light and dark layouts. This is
automated development verification, not owner hands-on acceptance.

## Not established

At this initial development check, no fresh 0.3 native package or installer was
built or installed. No installed 0.2 binary was upgraded.
No live cloud/Ollama/llama.cpp inference, model-quality
evaluation, real model download, Docker/WSL, macOS/Linux acceptance or publication
was performed. The previous 0.2 release evidence does not certify those 0.3 gates.
