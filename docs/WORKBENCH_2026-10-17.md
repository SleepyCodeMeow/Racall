# Apps, models and appearance — October 17, 2026

Local work for the unpublished **0.2 Beta** candidate. The version, release tag and publication hold are unchanged. This report covers the current working tree, not the older four-platform CI build.

## Behavior

- Light, Dark and System appearance use shared colors across chat, sources, notes, Research, Connect, Apps and settings. The saved preference is independent of interface language and credentials. Electron retains a native title bar and follows the selected appearance.
- Apps copies eight fixed Ollama launch commands and displays a dismissible notification. Desktop copying uses a trusted, allowlisted IPC operation. It does not execute the command, install a tool or start a model.
- The composer model picker lists the saved provider's real catalog, supports search, keyboard selection and manual IDs, and distinguishes local, cloud and server models. Selecting an answer model preserves other provider profiles and independent embeddings.
- Local Ollama downloads require explicit confirmation and use streamed progress for the current layer. Cancellation closes the request; partial cache files remain managed by Ollama. Restart marks unfinished work interrupted without replay. Completion refreshes the catalog without automatically selecting or running a model.
- English and Russian controls and errors are included. Feature modules and contributor entry points are listed in [CODE_MAP.md](CODE_MAP.md); usage is documented in [English](WORKBENCH.md) and [Russian](WORKBENCH.ru.md).

## Initial interface verification

| Check | Result |
| --- | --- |
| Backend regression suite | 370 passed; one existing Starlette/httpx deprecation warning |
| Ruff and TypeScript | Passed |
| EN/RU catalogs | 371 keys; parity, placeholders, plurals, diagnostics and preference/installer behavior passed |
| Production web and frozen Python service | Built successfully |
| Windows x64 unpacked application | Built locally with publication disabled |
| Packaged resource comparison | 245 files match web/backend build output and desktop/shared sources; package metadata matches |
| Workbench in the packaged app | Passed all 13 scenario groups; no renderer errors, inference, real downloads or credential writes |
| Minimum Windows size | 1000 × 680 outer window; menu/confirmation remain visible in the 984 × 641 client area, notebook row fully visible |
| Full Windows packaged suite | Passed: desktop, EN/RU and installer seed, provider profiles, workbench, persistence, maintenance and both frozen-service exercises |

The workbench smoke uses a separate knowledge profile and an owned loopback HTTP fixture. It verifies actual clipboard copying, provider/model persistence, explicit download confirmation, cancellation, completion, interrupted-download recovery, theme persistence and minimum-window layout. It rejects inference requests, credential writes and unexpected renderer network requests. Existing provider protocol checks use deterministic HTTP fixtures, not live model accounts.

During development, checks exposed clipboard permission/API handling, nested composer forms, an unwanted initial provider query, popup clipping, a clipped notebook row at minimum height and Escape losing its target after a confirmation button disappeared. These were corrected and covered by regression assertions. Manual model selection and search Enter preserve the draft without sending a chat request. The harness also handles an empty Windows clipboard, materializes original formats in main-process memory and restores the clipboard only while its own copied value is still current.

Raw build/resource evidence is in ignored `test-results/ui-refresh-20261016/`; the passing workbench result and eight actual Electron captures are in `test-results/workbench-desktop-1792233609931/`. The local executable is `test-results/ui-refresh-20261016/windows/win-unpacked/Racall.exe`. The build folder retains its October 16 creation date; final verification continued on October 17. Screenshots use synthetic test catalogs and are verification artifacts, not claims of live provider access. Actual light/dark EN/RU images were inspected; measured selected text samples meet their stated contrast thresholds. This is not a full accessibility audit.

At that stage, sequential `npm run test:packaged` exited with code 0. Other passing result directories are `desktop-1792233486086`, `languages-1792233526537`, `providers-desktop-1792233558997`, `persistence-1792233748598`, `maintenance-1792233790577` and `provider-bundle-af9d9d76e800`, all under `test-results/`. Frozen checks include PDF import, full-text retrieval, page citations, original-file authentication, planner/writer/critic provider protocols, saved reports/reopening and safe rejection of a truncated Claude stream.

## Finalization follow-up

The finalization pass keeps the 0.2 scope and version unchanged. Larger sidebar/settings revisions, optional model recommendations, conversation context and durable Studio generation remain later milestones. This pass addresses failures in existing workflows:

- Leaving Notes for Apps, settings or a new notebook waits for all pending saves. An unsavable draft keeps the editor open. Creating a notebook checks again after the delayed creation response, preserving edits made while that request was in flight. Ordinary workspace tabs keep Notes mounted, so a recovered conflict draft remains accessible for resolution.
- Startup marks unfinished Research sessions interrupted, preserves their saved question and steps, and never repeats model requests. English and Russian distinguish interrupted work from a running session.
- Failed clipboard copying clears stale success feedback and exposes the fixed launch command in a selectable, read-only field. A subsequent successful copy removes that fallback.
- Model icons follow catalog metadata for cloud, local and server connections. A selected Ollama cloud alias remains neutral after a cold restart until its type can be resolved; browsing another provider does not change the selected model's type or trigger background discovery.

The backend suite passed **372 tests**; Ruff, TypeScript, the **374-key** EN/RU checks, release metadata and installer catalogs passed. Production web and frozen Python builds succeeded. The backend run reported the existing Starlette/httpx deprecation and a sandbox denial when writing pytest's optional cache; no product test failed.

Regression checks first reproduced lost-note navigation, missing clipboard fallback and incorrect model typing. An initial packaged run then caught a guard that also blocked opening Notes to resolve a recovered conflict. That guard was narrowed to transitions which unmount the editor. The corrected targeted persistence run passed all 14 scenarios, including both delayed-response races, restored Research in EN/RU and no model replay (`test-results/persistence-1792236405421/`). Earlier red-run logs remain under `test-results/release-02-*.log`.

### Final candidate verification

| Check | Result |
| --- | --- |
| Fresh Windows x64 candidate | Web, frozen service, unpacked application and NSIS installer built with publication disabled |
| Packaged resource comparison | 249/249 files match; no missing, extra or mismatched files. Runtime package metadata matches after normal build-field removal |
| Packaged workbench | All 15 scenario groups passed; no renderer errors, inference, real model downloads, credential writes or external renderer requests |
| Packaged persistence | All 14 scenarios passed, including unsavable navigation, both delayed-response races, recovered conflicts and interrupted Research without replay |
| Full sequential packaged suite | Exit 0: desktop, EN/RU/installer language seed, provider profiles, workbench, persistence, maintenance and both frozen-service checks |
| Documentation and source checks | Local links in seven touched guides/reports resolve; `git diff --check` and both changed smoke scripts' syntax checks passed |

The final candidate is `test-results/release-02-final-20261017/windows/Racall-0.2.0-beta.1-win-x64.exe` (144,744,048 bytes). SHA-256: `4e8b1b93ebf45992fda0fe94de5d9a0c989500382bebd5746c0381a8e0d0a50b`. `SHA256SUMS.txt` beside it also records the blockmap. The suite launched the unpacked `windows/win-unpacked/Racall.exe` from this same build using isolated profiles; this pass did not install or uninstall the program on the owner's computer.

Raw evidence: `test-results/release-02-final-20261017/resource-comparison.json`, `release-02-polish-backend.log`, `release-02-polish-web-final.log`, `release-02-polish-frozen.log`, `release-02-polish-package.log` and `release-02-polish-packaged-final.log`. Final passing directories under `test-results/`: `desktop-1792236546078`, `languages-1792236586777`, `providers-desktop-1792236621396`, `workbench-desktop-1792236670468`, `persistence-1792236825785`, `maintenance-1792236913038` and `provider-bundle-4386de5e5683`. Final light/dark captures include the manual-copy fallback and metadata-driven model icons; the English fallback and Russian model popup were visually inspected.

These tests use owned synthetic HTTP fixtures. The two expected persistence-fixture answer calls do not represent real inference; restart recovery added no calls. Native protocol and frozen-service checks establish transport, citation and persistence behavior, not live account access or model-answer quality.

## Remaining acceptance boundaries

- No real model weights were downloaded and no real local/cloud inference was run for this UI update. Live account access, actual model availability and answer quality require separate acceptance.
- Fresh native macOS/Linux builds and the full native CI matrix remain pending. Earlier CI on `e708fe4` does not validate this changed worktree.
- Owner visual review remains pending. No installation, GitHub publication, release tag or version change was performed.

See the [release checklist](RELEASE_02_CHECKLIST.md) for the remaining release gates.
