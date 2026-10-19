# 0.2 Beta release candidate checklist

On **October 19, 2026**, the owner explicitly approved publication of **Racall 0.2 Beta for Windows x64**. The release policy declares `publication: "approved"`, `platforms: ["win-x64"]` and `github_latest: true`. The exact tagged source passed fresh Windows native CI and was [published](https://github.com/SleepyCodeMeow/Racall/releases/tag/v0.2.0-beta.1). Linux/macOS are outside this release's package and acceptance scope; the historical checks below do not establish acceptance of the current code on those platforms.

## Engineering scope

- [x] Persist chats, answers, search results and citation snapshots; mark unfinished Research sessions interrupted on startup without automatic paid replay.
- [x] Autosave Markdown, preserve metadata, detect external edits, recover drafts and protect unsaved edits on close/navigation, including changes during delayed notebook creation. Keep recovered conflicts accessible through workspace tabs.
- [x] Rename notebooks; confirmed removal to recoverable trash; restore notes, chats, source versions and files.
- [x] Block notebook removal during active model/import work.
- [x] Replace imported files and refresh public web sources. Preserve old versions and exact originals used by past citations.
- [x] Keep the last working source/index if a replacement fails; recover/retry interrupted imports.
- [x] Run file parsing and web-page extraction outside the API process, with a 60-second deadline and supervised 512 MiB RSS budget. Linux also bounds address space to 1 GiB. This is resource isolation, not a security sandbox.
- [x] Separate feature folders and document where contributors should edit each workflow.
- [x] EN/RU controls and errors; stable version metadata and explicit publication/platform policy.
- [x] Synthetic real-model evaluation fixture and owner instructions.
- [x] Light/dark/system appearance, searchable saved-provider model picker, explicit local Ollama downloads with cancellation/restart recovery, and Apps launch-command copying with a manual fallback. Model types follow provider metadata; unresolved aliases remain neutral after restart. See [interface guide](WORKBENCH.md).

## Verification gates

- [x] Local backend regression checks and production frontend/frozen backend builds.
- [x] Local Windows maintenance smoke: version replacement, historical citations/originals, failure preservation, notebook rename/trash/restore and restart.
- [x] Full Windows packaged regression suite for code commit `d909076` in native CI; includes the searchable installer and model citation-label fix.
- [x] Native CI: Windows x64, Linux x64, macOS arm64 and macOS x64 — [run 36251019854](https://github.com/SleepyCodeMeow/Racall/actions/runs/36251019854), code commit `d909076`.
- [x] Installer checks on disposable native hosts: NSIS install/uninstall, DMG copy/launch, Debian install/remove, extracted AppImage launch.
- [x] Reference-style Windows first screen and language dropdown: local native opening/translation/handoff checks, rebuilt EXE and actual bundled-screen cancellation check. Separate search, directory controls and size summary removed from the first screen.
- [x] Reference caption geometry: local Windows 11 native-frame/client-size checks, disabled edge resizing, EN/RU selection and rebuilt EXE cancellation. Title-bar colors remain native.
- [x] Matching progress-page layout: local EN/RU native control, shared dimensions, path display and no-install preview cancellation checks. Production uses the existing extraction progress control.
- [x] Native CI for the revised welcome/progress layouts and two-screen completion flow: all four platforms passed [run 38940737841](https://github.com/SleepyCodeMeow/Racall/actions/runs/38940737841), application commit `e708fe4`; publication skipped. See [full verification report](VERIFICATION_2026-10-16.md).
- [x] Native CI for the searchable installer: immediate translation, search/selection, path handoff, actual Russian installation seed and English reinstall seed. All four platform jobs passed in the run above; publication was skipped.
- [x] Local model-response and transport fixes: explicit claim-ID verifier, bounded EN/RU repair, localized Research heading and bounded internal SSE. 171 backend tests, 274-key catalog checks, fresh production builds and Windows packaged regressions passed. See [Research timeout verification](RESEARCH_TIMEOUT_2026-10-16.md).
- [x] Latest real Ollama GPU run: all 10 questions, source replacement/history, Research, English Markdown export and service/store reopening without model replay passed independent assistant review. Full quotation/version/hash checks passed. Current weights differ from the earlier failed run; this is not a controlled speed comparison.
- [x] Four primary provider connections, separate profiles, native Claude Messages and independent embeddings: 287 backend tests, 299-key catalogs, new Windows build and full packaged suite passed. Native HTTP fixtures cover all five explicit modes, cited Research/save/reopen and truncated Claude rejection. See [provider verification](PROVIDERS_2026-10-16.md).
- [x] Final local 0.2 pass: 372 backend tests, 374-key EN/RU catalogs, production builds and the full rebuilt Windows packaged suite passed. Includes 15 workbench groups, 14 persistence scenarios, guarded unsavable navigation/delayed notebook creation, interrupted Research without replay, manual clipboard fallback and model-type metadata after restart. All 249 packaged files match their expected outputs. See [October 17 final candidate verification](WORKBENCH_2026-10-17.md#final-candidate-verification).
- [x] Explicit Windows-only release scope, publication timing and Latest presentation approved by the owner on October 19. Policy tests preserve immutable tag/build matching, native-check requirements, exact artifacts/checksums and draft-before-publication behavior.
- [x] Fresh Windows x64 native CI for the exact release source `70fd79bd69cef06d88c03e1fa5ff88929fc1fa3e`: [run 39257810891](https://github.com/SleepyCodeMeow/Racall/actions/runs/39257810891). All jobs passed: 404 backend tests, 374-key EN/RU checks, production builds, native language picker, full packaged suite, NSIS installation/uninstallation preserving user knowledge, and publication. Earlier native/local candidates remain historical evidence; the released EXE is from this fresh tag build.

Current Linux/macOS packaged and installer acceptance is deferred. Their packages must not be attached to this Windows-only 0.2 release or described as verified for its current source. A later release can explicitly include them after its native checks pass.

## Owner-approved acceptance exceptions — October 19, 2026

For the first Windows 0.2 Beta, the owner waived mandatory final live-model acceptance and an owner's hands-on review, choosing to collect feedback from early users. These checks were **not performed, not passed**, and are no longer blocking manual gates for that Windows beta:

- Live acceptance of the final provider/model configurations using [MODEL_EVALUATION.md](MODEL_EVALUATION.md), including cloud providers and an actual llama.cpp server. The prior real Ollama run predates the provider-profile update. Deterministic protocol checks do not establish live account access or model quality. Earlier [model-fix timeout](MODEL_FIXES_2026-10-16.md), [October 16](VERIFICATION_2026-10-16.md) and [September 26](OLLAMA_EVALUATION_2026-09-26.md) failures remain recorded. The evaluation kit remains available for voluntary testing.
- Owner's hands-on review of the candidate on their computer.

This exception does not establish Linux or macOS acceptance or waive the fresh Windows engineering/build gate. Publication timing was subsequently approved by the owner's separate explicit request to publish 0.2 on October 19.

## Known limits to carry into release notes

Builds are unsigned; macOS builds are not notarized because signing credentials are unavailable. Native CI is not a substitute for every interactive SmartScreen/Gatekeeper/permission dialog. The AppImage check extracts and runs its contents, without exercising FUSE mounting. Mobile/sync, chat-model conversational context and durable Studio generation are outside 0.2.

Autosave cannot preserve keystrokes that never reached the service before a crash. Resource sampling is a best-effort memory bound with a short sampling interval, not a hardened OS sandbox. All source versions and trashed notebooks are retained; there is no permanent-delete UI yet. Backup the full knowledge directory while the app is closed before upgrading; downgrade behavior for new versioned sources is not guaranteed.

## Release timing gate

The approved Windows release is published as **Racall 0.2 Beta**, machine version `0.2.0-beta.1`, immutable tag `v0.2.0-beta.1`. The fresh Windows gate passed, and publication uploaded the EXE with SHA-256 checksums. The October 19 acceptance exceptions above remain disclosed as unperformed checks. Return the next development version to `publication: "hold"`; do not infer timing approval for 0.3 or additional platform releases.
