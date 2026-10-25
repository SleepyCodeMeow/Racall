# 0.3 Beta release checklist

The owner approved publishing **0.3 Beta on October 25, 2026**, accepting the limited hardware/model coverage and known AI-critic false positives. **Release publication is in progress.** This supersedes the earlier timing hold; it does not turn incomplete model certification into a passed check or authorize replacing existing 0.2 assets. See [source review and scope](REFERENCE_PROJECTS.md#refresh-2026-10-25).

Earlier dated verification reports retain the hold status that applied when their checks ran. The [release notes](releases/0.3.0-beta.1.md) state the current user-facing scope and beta limits.

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
- [x] Full backend suite, lint, TypeScript and localization/release metadata checks (462 tests initially, 486 in the first native matrix, 493 after the maintainability refactor; 499 after evidence-scope and evaluator-shutdown regressions).
- [x] Production frontend build and isolated UI workflow smoke without real model requests/downloads.
- [x] Portable 0.2 chat/note/report compatibility regressions and preserved citation versions; this is not an installed binary upgrade test.
- [x] Separate installed Windows x64 0.2 → exact final 0.3 candidate upgrade, same default profile/path, preserved data and uninstall retention: [run 40222132278](https://github.com/SleepyCodeMeow/Racall/actions/runs/40222132278).
- [x] Fresh native candidate build and installer/copy checks for all six declared x64/ARM64 targets.
- [ ] Stable live-model semantic acceptance: recorded unsupported claims passed the local critic. **Accepted by the owner as a known beta limitation, not a passed certification gate.** Later successful examples do not establish reliability; see the [October 25 model report](MODEL_EVALUATION_03_2026-10-25.md).

Final application-source and binary upgrade checks are tracked in the
[candidate verification report](CANDIDATE_VERIFICATION_03_2026-10-25.md), separately
from model reliability and owner hands-on acceptance.

The owner subsequently expanded the candidate scope to x64 and ARM64 on Windows,
macOS and Linux. All six passed again on final application source
`50e1a65a80f86c2f66c6132289904057ec89bbb2` in
[Actions run 40221003598](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598).
See [native candidates](NATIVE_CANDIDATES_03.md) and the
[final candidate verification report](CANDIDATE_VERIFICATION_03_2026-10-25.md) for exact
source, package checksums and limits. Publication is authorized by the owner's
October 25 decision; these candidate checks do not replace the matching
tag-triggered release verification and uploaded-asset checks.

## Publication

- [x] Owner explicitly approved releasing 0.3 Beta with the documented hardware, platform and model-quality limits.
- [x] Public release notes and changelog explain the changes from 0.2, six native targets, unsigned distribution and AI review requirements.
- [ ] Matching tag-triggered release verification completes for the approved source and target matrix.
- [ ] GitHub release contains all declared packages, source/target manifests and matching checksums; uploaded assets are verified.
- [ ] Confirm the existing public 0.2 release and assets remain unchanged.

Development evidence is recorded in [the October 25 verification report](VERIFICATION_03_2026-10-25.md).
The completed [maintainability refactor](REFACTOR_03_2026-10-25.md) includes
controller/view and engine boundaries, shared note parsing, formatting gates and
the contributor development tour.

Model-quality evaluation, Windows/macOS/Linux acceptance and publication status are reported separately. The owner's qualified beta approval does not establish unperformed hands-on, provider or hardware tests. Earlier 0.2 results do not certify new 0.3 behavior. Do not run local Docker/WSL or a real model merely to satisfy this checklist.
