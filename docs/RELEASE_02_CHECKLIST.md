# 0.2 Beta release candidate checklist

Publication is **on hold** at the owner's request. No release date or interval has been chosen. Candidate builds and source updates may be tested; do not create a release tag or publish a GitHub release until the owner explicitly selects the timing.

## Engineering scope

- [x] Persist chats, answers, search results and citation snapshots; restart without automatic paid replay.
- [x] Autosave Markdown, preserve metadata, detect external edits, recover drafts and protect unsaved edits on close/navigation.
- [x] Rename notebooks; confirmed removal to recoverable trash; restore notes, chats, source versions and files.
- [x] Block notebook removal during active model/import work.
- [x] Replace imported files and refresh public web sources. Preserve old versions and exact originals used by past citations.
- [x] Keep the last working source/index if a replacement fails; recover/retry interrupted imports.
- [x] Run file parsing and web-page extraction outside the API process, with a 60-second deadline and supervised 512 MiB RSS budget. Linux also bounds address space to 1 GiB. This is resource isolation, not a security sandbox.
- [x] Separate feature folders and document where contributors should edit each workflow.
- [x] EN/RU controls and errors; stable version metadata and publication hold.
- [x] Synthetic real-model evaluation fixture and owner instructions.

## Verification gates

- [x] Local backend regression checks and production frontend/frozen backend builds.
- [x] Local Windows maintenance smoke: version replacement, historical citations/originals, failure preservation, notebook rename/trash/restore and restart.
- [x] Final full Windows packaged regression suite for code commit `7a73788`.
- [x] Native CI: Windows x64, Linux x64, macOS arm64 and macOS x64 — [run 36246042420](https://github.com/SleepyCodeMeow/Racall/actions/runs/36246042420), code commit `7a73788`.
- [x] Installer checks on disposable native hosts: NSIS install/uninstall, DMG copy/launch, Debian install/remove, extracted AppImage launch.
- [ ] Owner's real cloud/Ollama evaluation using [MODEL_EVALUATION.md](MODEL_EVALUATION.md). Deferred to the owner by explicit choice; not replaced by mock tests.
- [ ] Owner's hands-on review of the candidate on their computer.

## Known limits to carry into release notes

Builds are unsigned; macOS builds are not notarized because signing credentials are unavailable. Native CI is not a substitute for every interactive SmartScreen/Gatekeeper/permission dialog. The AppImage check extracts and runs its contents, without exercising FUSE mounting. Mobile/sync, chat-model conversational context and durable Studio generation are outside 0.2.

Autosave cannot preserve keystrokes that never reached the service before a crash. Resource sampling is a best-effort memory bound with a short sampling interval, not a hardened OS sandbox. All source versions and trashed notebooks are retained; there is no permanent-delete UI yet. Backup the full knowledge directory while the app is closed before upgrading; downgrade behavior for new versioned sources is not guaranteed.

## Release timing gate

Even when engineering checks pass, leave `apps/shared/release.json` at `publication: "hold"`. A future release requires explicit timing approval, the remaining human checks, a matching tag build and verified checksums. Do not advance to 0.3 merely to make another release immediately.
