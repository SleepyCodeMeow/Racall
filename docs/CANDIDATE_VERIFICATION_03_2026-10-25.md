# 0.3 candidate verification — October 25, 2026

**Publication was on hold during these candidate checks.** The owner later
approved 0.3 Beta; see the [published release verification](VERIFICATION_03_RELEASE_2026-10-25.md)
for the fresh tag build and public files. The candidate checks below did not
change the old 0.2 assets. Model quality is a separate gate and is not certified:
see the [local-model report](MODEL_EVALUATION_03_2026-10-25.md) for actual false
positives, failed runs, controls and the final functional run.

The candidate's application source is
`50e1a65a80f86c2f66c6132289904057ec89bbb2`, on branch
`codex/0.3-context-studio`. Later documentation and upgrade-input pin commits
must not be mistaken for a different application payload.

## Checks

| Gate                                   | Result and evidence                                                                                                                                                                 |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python suite on Windows                | 499 passed; one existing Starlette/httpx deprecation warning                                                                                                                        |
| Python style                           | Ruff check and formatting passed for API, tests and all Python scripts                                                                                                              |
| Local Ollama workflow                  | 25/25 functional contracts; 24 reviewed cases pass and one naming note; model reliability remains not certified                                                                     |
| Six native targets                     | [Run 40221003598](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598) passed all six; 499 Python tests per target, packaged workflows and native install/copy checks |
| Installed Windows 0.2 → this candidate | [Run 40222132278](https://github.com/SleepyCodeMeow/Racall/actions/runs/40222132278) passed on the exact Windows x64 EXE below                                                      |

The local suite includes four evidence-scope workflow regressions and two
evaluator shutdown regressions. The latter use a real application job worker
with a synthetic transport, without real inference. They test STOP before local
worker cleanup, bounded waiting, terminal trace preservation and explicit timeout.

## Native package scope

The six separate native jobs are Windows x64/ARM64, macOS Intel x64/Apple Silicon
ARM64 and Linux x64/ARM64. Each builds its bundled Python service on the target
runner, checks executable architecture, runs the backend suite, formatting,
frontend/type/localization/release checks, packaged application scenarios and
native installation/copy checks. The package matrix remains authoritative in
[release_policy.py](../scripts/release_policy.py).

Ten distribution files were uploaded in six Actions artifacts, with source-bound
`BUILD.json` and `SHA256SUMS.txt`. The publication job was skipped. Checksums below
are computed by CI and matched against the source/target manifests and archive
metadata. The installed-upgrade gate additionally downloads and hashes the actual
Windows x64 EXE. Building candidates does not publish them or permit replacing
public assets.

### CI artifacts

| Target      | Artifact                                                                                               | Archive SHA256                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| win-x64     | [12609985853](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598/artifacts/12609985853) | `6d0d2c4d8402150b34f627a7b17fe483ba966c3b4ef525c7b128fe8c61c7352e` |
| win-arm64   | [12610670114](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598/artifacts/12610670114) | `4221588373ef5ef4a21f53340586f0e264a42d4a37fcb74002ae4871cd722809` |
| mac-x64     | [12609766399](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598/artifacts/12609766399) | `800ad5a768381ad1a2589292cf219669d9a86deff51f84b269215136f96f0cd7` |
| mac-arm64   | [12608973435](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598/artifacts/12608973435) | `3cfb8c885a4f377e478b77054ffd87e6b879fde93beed84133255c5c59f53918` |
| linux-x64   | [12610120596](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598/artifacts/12610120596) | `9fbfdbf9f311cfc22c44b5fb2c24ad27937376bc8e44c746728735e576e6647c` |
| linux-arm64 | [12610030790](https://github.com/SleepyCodeMeow/Racall/actions/runs/40221003598/artifacts/12610030790) | `a34a234d5b40df34452ffbe25981b499365aa83fce7c6aee8942558aff211dec` |

### Distribution checksums

| Package                                     |     Bytes | SHA256                                                             |
| ------------------------------------------- | --------: | ------------------------------------------------------------------ |
| `Racall-0.3.0-beta.1-win-x64.exe`           | 153279558 | `7aa36844f6893335299bdca2f4d906e2ef980ccd3c443634eb6303dd507d5af5` |
| `Racall-0.3.0-beta.1-win-arm64.exe`         | 145035860 | `107a9339b3020835725c8ce765ac5a420312f512576ac4aa0d959d7de7800592` |
| `Racall-0.3.0-beta.1-mac-x64.dmg`           | 172192634 | `51c19efe91a6ebb6cf21e578e1caabd1792dafa72bc221e3d9f713b22f10c619` |
| `Racall-0.3.0-beta.1-mac-x64.zip`           | 166267767 | `f7f38382ad108dfae4dc293bf13f3369eba1cc48f04203c84370884c661d7a56` |
| `Racall-0.3.0-beta.1-mac-arm64.dmg`         | 166820836 | `285f58e9ccd56868db7699a4052d0f5e3cbeb7aa6e6dc2a3ad88a8b9f20199b7` |
| `Racall-0.3.0-beta.1-mac-arm64.zip`         | 160959980 | `58c8be3fec494c456d6497f2142ff415b3f8f3273dcfb58e88de4f888a9ded79` |
| `Racall-0.3.0-beta.1-linux-x86_64.AppImage` | 169699187 | `21f1e3448c8bf9690f9c6e0fe2c079039b240e17627a292c581946beae174d65` |
| `Racall-0.3.0-beta.1-linux-amd64.deb`       | 137742996 | `26af7f64301133387be542a0c56b3a8d7a35159c989df06b7f3d0961cdcb22e2` |
| `Racall-0.3.0-beta.1-linux-arm64.AppImage`  | 168179945 | `861f740d1063dff1a3de5696c38bf55a95586c046dce04410133872e12853201` |
| `Racall-0.3.0-beta.1-linux-arm64.deb`       | 128847440 | `2d438b34c9a1c0b1b919698d2ea38ef2d43680a72e419250895630145aa0c5c3` |

## Installed upgrade scope

The [dedicated upgrade workflow](../.github/workflows/check-upgrade.yml) is
restricted to disposable GitHub-hosted Windows x64. It verifies immutable input
manifests, sizes and hashes, installs the published 0.2 binary, seeds synthetic
knowledge through that installed backend and then upgrades in place. The new
installer is invoked without overriding the existing installation path. Both
versions use the same default Chromium/knowledge profile, not isolated paths
that would skip migration behavior.

The scenario compares authoritative data bytes, reopens historical citations and
original source versions, checks legacy reports/export and a new note-only Studio
material, switches EN/RU and light/dark, restarts without inference replay and
uninstalls while preserving knowledge. A synthetic protocol fixture makes no
real provider/model calls. It does not install or modify Racall on the owner's PC.

The first attempt failed because the test expected an asynchronously persisted
theme radio to change immediately. Clicking the actual theme control and waiting
for API, HTML and native theme agreement fixed that test race. The corrected
[run 40219233184](https://github.com/SleepyCodeMeow/Racall/actions/runs/40219233184)
passed against the earlier `4389b888...` candidate. That historical pass does not
certify the current payload by itself.

The final [run 40222132278](https://github.com/SleepyCodeMeow/Racall/actions/runs/40222132278),
using harness source `b1ae96eed8b0d19ccc1263ed834ae86c3d837911`, passed against the
exact application source `50e1a65a...`. Its Windows x64 input was artifact
`12609985853` from native run `40221003598`, EXE size 153,279,558 bytes and SHA256
`7aa36844f6893335299bdca2f4d906e2ef980ccd3c443634eb6303dd507d5af5`.
The old public installer was pinned at 144,616,175 bytes and SHA256
`82fc01e779997f7fc4fe5c570cd371c6dc5d83cea0cf7d337b508332f45e02e0`.

All installed-upgrade checks described above passed. Nineteen pre-existing authoritative files
were preserved byte for byte; the synthetic provider recorded seven calls and
no errors. The [upgrade evidence artifact](https://github.com/SleepyCodeMeow/Racall/actions/runs/40222132278/artifacts/12609254169)
contains input manifests, file snapshots, result records, exported Markdown,
screenshots and logs. It is 247,124 bytes with archive SHA256
`172e4f38db2203719c1e1f807644fffc3a60028a0c45b54953bffd43b07f769a`.

## Limits

Hosted native execution does not certify every OS version, Linux desktop or
AppImage FUSE configuration, download quarantine, physical device behavior,
publisher signing or macOS notarization. No Windows x86/ARM32, Linux x86/ARMv7 or
universal macOS binary is declared. See the [native candidate policy](NATIVE_CANDIDATES_03.md).

The owner has not completed hands-on desktop acceptance. Live cloud providers,
llama.cpp, embeddings quality and real model downloading were not exercised in
this run. Local WSL/Docker was not used. Neither deterministic fixtures nor a
later accurate Ollama answer erase an observed semantic verification failure.
