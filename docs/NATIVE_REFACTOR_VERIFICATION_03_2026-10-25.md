# Native verification after the 0.3 maintainability refactor

**All six native targets passed. Ten distribution files were uploaded. Publication remains on hold.**

- Exact binary source: [`4389b888daa2c3b8825e55ca4beec9a13bdc0b24`](https://github.com/SleepyCodeMeow/Racall/commit/4389b888daa2c3b8825e55ca4beec9a13bdc0b24).
- Candidate run: [40212923810](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810), `workflow_dispatch`, branch `codex/0.3-context-studio`.
- Version: `0.3.0-beta.1`; label `0.3 Beta`; `publication: hold`, `github_latest: false`.

This run checks the source after the [maintainability refactor](REFACTOR_03_2026-10-25.md).
Later documentation-only commits do not change the provenance of these binaries.
The earlier [native report](NATIVE_VERIFICATION_03_2026-10-25.md) remains evidence
for its pre-refactor source; it is not substituted for this run.

## Results

| Application target | Native hosted runner | Build, packaged application and installation/copy |
| --- | --- | --- |
| Windows x64 | `windows-latest` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/job/121227866469) |
| Windows ARM64 | `windows-11-arm` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/job/121227866479) |
| macOS Intel x64 | `macos-15-intel` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/job/121227866585) |
| macOS Apple Silicon ARM64 | `macos-15` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/job/121227866430) |
| Linux x64 | `ubuntu-22.04` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/job/121227866525) |
| Linux ARM64 | `ubuntu-22.04-arm` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/job/121227866444) |

Every successful target passed **493 Python tests**, eight native-target checks,
Ruff, the new Ruff/Prettier formatting gate, EN/RU catalog checks, release metadata,
deterministic fixture evaluation, production frontend/frozen Python build and
TypeScript validation.

The native Node/Python runtime and both Electron/frozen backend executable headers
must match the declared architecture. All seven packaged scenarios ran: desktop,
languages, providers, workbench, Studio, persistence and maintenance. Frozen-backend
checks also cover PDF import, search, provenance, original download, authentication
and synthetic provider protocols, including truncated completions.

Installed-package checks cover:

- Windows: native language picker, Russian/English silent install and language
  seeds, installed executable/sidecar architecture, maintenance and uninstall
  preserving a knowledge sentinel.
- macOS: readonly DMG mount, application copy into the test Applications directory,
  installed native headers and maintenance. ZIP generation/checksum is included;
  a separate ZIP extraction/launch scenario is not.
- Linux: DEB architecture, installation/launch/removal with preserved knowledge,
  and extracted AppImage launcher/native payload execution. FUSE mounting is not
  exercised.

## Artifacts and package digests

Each successful target uploads its packages, `BUILD.json` identifying source and
target, and `SHA256SUMS.txt`. Actions retention applies; these are candidate
artifacts, not public release assets.

| Artifact | Download from Actions |
| --- | --- |
| `Racall-win-arm64` | [12606518639](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/artifacts/12606518639) |
| `Racall-mac-arm64` | [12607110148](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/artifacts/12607110148) |
| `Racall-linux-arm64` | [12607066211](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/artifacts/12607066211) |
| `Racall-win-x64` | [12606896781](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/artifacts/12606896781) |
| `Racall-linux-x64` | [12606846873](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/artifacts/12606846873) |
| `Racall-mac-x64` | [12606526855](https://github.com/SleepyCodeMeow/Racall/actions/runs/40212923810/artifacts/12606526855) |

The following package digests were computed on the runner and read from its
logged manifest. GitHub separately records the outer artifact ZIP digest.
Package binaries were not downloaded and independently rehashed locally.

| Distribution file | Bytes | SHA-256 |
| --- | ---: | --- |
| `Racall-0.3.0-beta.1-win-x64.exe` | 153,279,052 | `9d682aee901526141e85d82e4bdf9a5cd71bd87c75eeb3a51675a9deae4e471b` |
| `Racall-0.3.0-beta.1-win-arm64.exe` | 145,034,656 | `1cd366a783f3623f5ca3e660c45d4c90d4275929481f6e8bba2b0aef2904285c` |
| `Racall-0.3.0-beta.1-mac-x64.dmg` | 172,190,493 | `c4f9145bbd736ca741d13844d4ceb35dc65c24e81f259c7d3d1f57ee11fb265d` |
| `Racall-0.3.0-beta.1-mac-x64.zip` | 166,265,484 | `da3cd09633e13063691c0329d128492cd9265c1ee800be4ff562493ed66c7c64` |
| `Racall-0.3.0-beta.1-mac-arm64.dmg` | 166,817,507 | `cff59d1f43486764bb988e1de4b24c7fd3799d4fbde21db3bbac7b7002d577b8` |
| `Racall-0.3.0-beta.1-mac-arm64.zip` | 160,956,494 | `7d15c2ea4addaa702fe12ee497ecf13cfd48d6c905471ba3fd1afec896e0d48f` |
| `Racall-0.3.0-beta.1-linux-x86_64.AppImage` | 169,707,347 | `7b4a75f4b4494da41453ca468c2493902765916d2931565cd8729350c0ccdd84` |
| `Racall-0.3.0-beta.1-linux-amd64.deb` | 137,742,400 | `1c4adf823e169d9aaad1e422fb1808d693495e532dd23e8f2546218098022443` |
| `Racall-0.3.0-beta.1-linux-arm64.AppImage` | 168,175,813 | `2de5dc9a7f0f96fe917305023331dee8718e607e4064a22869fdb10ed31e21ba` |
| `Racall-0.3.0-beta.1-linux-arm64.deb` | 128,846,760 | `a2e1d671e393c5794a989e2884693c4b4afad354a1a1f63a7dee2fd2c6b3fc48` |

## Local application evidence

The complete run ended with `success`; its publication job was skipped. The
local metadata/manifests snapshot is
`test-results/native-candidates-40212923810/verification.json`, with combined
`SHA256SUMS.txt`. The local verification helper checked all six successful jobs,
formatting gates, exact ten package names, sizes/digest fields, matching source
and nonexpired artifact metadata. It grants no publication permission.

All seven local development Electron scenarios passed on the production static
frontend and the refactored Python/Electron modules. The local record is
`test-results/refactor-03-local-verification.json`; screenshots and individual
result paths are listed there. The initial restricted-sandbox attempt ended
before the first window; the unchanged scenario passed outside that sandbox.

Three Studio snapshots are pixel-identical to the pre-refactor snapshots, covering
light, dark and minimum-window layouts. Seven of ten workbench snapshots are
pixel-identical too. The others differ only by the ephemeral test-server port
and 14/1 border-rendering pixels in the compared images.

## Limits and release boundary

All provider inference in these checks uses synthetic fixtures. Real-model
quality, GPU behavior, an installed binary upgrade from 0.2, owner hands-on
acceptance and every supported OS version/desktop environment are not established.
Windows publisher signing and macOS Developer ID/notarization remain absent;
download quarantine and Gatekeeper prompts were not manually checked.

No local Docker/WSL workload or real model download was used. No release tag,
GitHub release or change to the public 0.2 assets was made. Publication stays on
hold; a future approved release must still satisfy its tag/source verification.

