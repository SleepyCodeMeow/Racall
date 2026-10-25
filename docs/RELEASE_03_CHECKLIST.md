# 0.3 Beta development checklist

The owner approved starting the context/jobs/Studio development scope on October 25, 2026. **Publication remains on hold**; this is not permission to publish another release or change the existing 0.2 assets. See [source review and scope](REFERENCE_PROJECTS.md#refresh-2026-10-25).

## Workflow

- [x] Bounded active-thread history and follow-up retrieval, with thread/notebook isolation.
- [x] Explicit source selection, including an empty selection, plus saved-note revisions and inspectable citations.
- [x] Persist selected context without silently returning to all sources after restart.
- [x] Durable Research/Studio jobs, one worker, real progress and no duplicate submission.
- [x] Queued/running cancellation, late-result protection and explicit retry after interruption.
- [x] Source/version and nonsecret provider snapshots; no credentials persisted in jobs or artifacts.
- [x] Three grounded text presets: summary, study guide, review questions with answers.
- [x] Material library, Markdown export and editable note copies; earlier 0.2 reports remain accessible.
- [x] EN/RU, light/dark and keyboard/minimum-window behavior in the development Electron app.
- [x] Existing system-theme/model workbench scenario rechecked on this source revision.

## Verification

- [x] Targeted deterministic backend regressions for context, jobs, materials and profile changes.
- [x] Full backend suite, lint, TypeScript and localization/release metadata checks (462 tests at initial development verification; 486 in the later native matrix).
- [x] Production frontend build and isolated UI workflow smoke without real model requests/downloads.
- [x] Portable 0.2 chat/note/report compatibility regressions and preserved citation versions; this is not an installed binary upgrade test.
- [x] Fresh native candidate build and installer/copy checks for all six declared x64/ARM64 targets.

The owner subsequently expanded the candidate scope to x64 and ARM64 on Windows,
macOS and Linux. All six passed in [Actions run 40209217858](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858).
See [native candidates](NATIVE_CANDIDATES_03.md) and the
[native verification report](NATIVE_VERIFICATION_03_2026-10-25.md) for exact
source, package checksums and limits. These candidate checks do not authorize
publication or replace the eventual matching tag-triggered release verification.

Development evidence is recorded in [the October 25 verification report](VERIFICATION_03_2026-10-25.md).

Model-quality evaluation, Windows/macOS/Linux acceptance and publication timing must each be reported separately. Earlier 0.2 results do not certify new 0.3 behavior. Do not run local Docker/WSL or a real model merely to satisfy this checklist.
