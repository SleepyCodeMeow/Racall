# Racall 0.2 Beta — published Windows verification

Published on **October 19, 2026**, after the owner's explicit approval. This release targets **Windows x64**. Linux/macOS packages are not included, and this run does not establish acceptance on those platforms.

## Release and exact source

- [Racall 0.2 Beta](https://github.com/SleepyCodeMeow/Racall/releases/tag/v0.2.0-beta.1)
- Immutable tag: `v0.2.0-beta.1`
- Application source: [`70fd79bd69cef06d88c03e1fa5ff88929fc1fa3e`](https://github.com/SleepyCodeMeow/Racall/commit/70fd79bd69cef06d88c03e1fa5ff88929fc1fa3e)
- Fresh tag build: [GitHub Actions run 39257810891](https://github.com/SleepyCodeMeow/Racall/actions/runs/39257810891), all three jobs passed: platform policy, Windows native build/checks and publication.

The published installer was built by this run. The earlier local candidate was not reused. Documentation on the default branch records the resulting evidence without moving the application tag or replacing its assets.

## Checks passed

| Check | Result |
| --- | --- |
| Backend tests | 404 passed; one existing Starlette/httpx deprecation warning |
| Lint, TypeScript and release metadata | Passed |
| EN/RU and installer catalogs | 374 keys, matching placeholders and language behavior; passed |
| Evaluation fixtures | Validated without real inference |
| Production frontend and frozen Python service | Built successfully on the Windows runner |
| Windows x64 NSIS package | Built from the exact tag |
| Native language picker | Passed |
| Full packaged suite | Desktop, languages, provider profiles, workbench, persistence, maintenance and both frozen-service exercises passed |
| Workbench and persistence | 15 workbench groups and 14 persistence scenarios passed |
| Native install/uninstall | Russian language seed, installed application and removal preserving user knowledge passed on the disposable runner |
| Publication | Draft upload, exact asset names/sizes and final publication passed |
| Download verification | Downloaded EXE matches both `SHA256SUMS.txt` and GitHub's asset digest; installer was not executed on the owner's computer |

The earlier October 17 result of 372 tests and the 249-file resource comparison belong to the local candidate documented in [that report](WORKBENCH_2026-10-17.md). They are not measurements of this freshly built release artifact.

## Published downloads

[Windows installer](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.2.0-beta.1/Racall-0.2.0-beta.1-win-x64.exe) · [SHA256SUMS.txt](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.2.0-beta.1/SHA256SUMS.txt)

File: `Racall-0.2.0-beta.1-win-x64.exe`  
Size: **144,616,175 bytes**  
SHA-256: `82fc01e779997f7fc4fe5c570cd371c6dc5d83cea0cf7d337b508332f45e02e0`

The release is public and designated GitHub Latest. GitHub's prerelease flag is disabled for this presentation; the product remains **0.2 Beta**, with its beta version and limits unchanged. The previous 0.1 release and distribution files remain available separately.

## Acceptance boundaries

The final protocol checks use deterministic local HTTP fixtures. No final live-provider account/answer-quality acceptance or owner's hands-on pass was performed; the owner explicitly waived those manual gates for this Windows beta. The [evaluation kit](MODEL_EVALUATION.md) remains available to volunteers.

The installer is unsigned. Native automated checks do not cover every interactive security dialog or every user's hardware, provider and documents. The interrupted local Linux attempt is not a passed Linux application/installer check. No local Docker/WSL load or real model inference was started for this release publication.

Raw release/run/job metadata, CI logs and downloaded-file verification are retained locally under ignored `test-results/published-02-20261019/`. Private test profiles, machine files and credentials are not published.
