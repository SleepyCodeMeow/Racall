# Native 0.3 candidate verification — October 25, 2026

This is the historical pre-refactor candidate report. The later
[native refactor verification](NATIVE_REFACTOR_VERIFICATION_03_2026-10-25.md)
records fresh packages from source `4389b888daa2c3b8825e55ca4beec9a13bdc0b24`.

**All six native candidate jobs passed. Publication remains on hold.**

- Version: `0.3.0-beta.1` (`0.3 Beta`).
- Exact package source: [`94c34702fb6e1a8e08f7cbd2cd4ceb0fc7348b78`](https://github.com/SleepyCodeMeow/Racall/commit/94c34702fb6e1a8e08f7cbd2cd4ceb0fc7348b78).
- Branch at dispatch: `codex/0.3-context-studio`.
- Candidate workflow: [GitHub Actions 40209217858](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858), triggered by `workflow_dispatch`.
- Build policy: six native targets, `publication: hold`, `github_latest: false`.
- Result: six successful native jobs, six uploaded package artifacts, ten
  distribution files; the publication job was skipped.

The source above identifies the binaries. Later documentation-only commits do not
change their provenance. The public 0.2 release was not replaced.

## Native results

| Application target | Hosted runner | Build, packaged app and installation |
| --- | --- | --- |
| Windows x64 | `windows-latest` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858/job/121216700897) |
| Windows ARM64 | `windows-11-arm` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858/job/121216700899) |
| macOS Intel x64 | `macos-15-intel` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858/job/121216700933) |
| macOS Apple Silicon ARM64 | `macos-15` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858/job/121216700926) |
| Linux x64 | `ubuntu-22.04` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858/job/121216700922) |
| Linux ARM64 | `ubuntu-22.04-arm` | [Passed](https://github.com/SleepyCodeMeow/Racall/actions/runs/40209217858/job/121216700883) |

Each successful job ran **486 Python tests**, the native-target Node checks,
lint, installer catalog and EN/RU checks, release consistency, deterministic
fixture evaluation, the production web/PyInstaller build and TypeScript checks.
Node and Python must match the declared architecture on the selected native
hosted runner. The Electron and frozen backend executable headers must match
the target both before and after installation/copy.

The packaged application checks run desktop, languages, providers, workbench,
Studio, persistence and maintenance scenarios. Frozen-backend checks additionally
cover PDF import, search, page citations, original download and authentication;
synthetic provider checks cover protocol handling, citations, save/reopen and
truncated Claude responses. They do not evaluate a real model.

Installation scope:

- Windows: native language picker; Russian then English silent NSIS installation,
  first-launch language seeds, installed application launch and architecture,
  and uninstall with a preserved knowledge sentinel.
- macOS: readonly DMG mount, application copy to a test Applications directory,
  installed application launch and architecture. ZIP creation and checksums pass;
  a separate ZIP extraction/install scenario is not included.
- Linux: Debian package architecture, package install/launch/remove, and execution
  of the extracted AppImage launcher and native payload. The knowledge sentinel
  survives removal. FUSE mounting is not exercised.

## Package provenance and checksums

The Actions artifacts are named `Racall-win-x64`, `Racall-win-arm64`,
`Racall-mac-x64`, `Racall-mac-arm64`, `Racall-linux-x64` and
`Racall-linux-arm64`. Each successful artifact contains its distribution files,
`BUILD.json` (source, version, target, publication state) and `SHA256SUMS.txt`.
The following digests were computed on the CI host from the finished packages and
read back from the successful job's manifest. GitHub additionally records a
separate SHA-256 for each uploaded artifact ZIP. Artifact availability is subject
to the repository's Actions retention period.

| Distribution file | Bytes | SHA-256 |
| --- | ---: | --- |
| `Racall-0.3.0-beta.1-win-x64.exe` | 153,265,636 | `525132f9e92eeec9dd18a26293e00c8125dada45c214f752081da1cc45b31cd2` |
| `Racall-0.3.0-beta.1-win-arm64.exe` | 145,021,442 | `f0f4d6d073ed109dd1428e18e3217bb13f6209d28b7cb3a97e85bee733ba7194` |
| `Racall-0.3.0-beta.1-mac-x64.dmg` | 172,187,757 | `da515d380cb9eba3802dbb73fe7db5c932d440322ab0ecf6746a63b00b10e10b` |
| `Racall-0.3.0-beta.1-mac-x64.zip` | 166,249,210 | `ba22e62d13f98997cf72280e00d284d01ebcc6052715f3290feba1acdf96ccdf` |
| `Racall-0.3.0-beta.1-mac-arm64.dmg` | 166,814,226 | `068138bd0e16b1239b5c29882e11cff0933ccda78c36e1e7cb4a2031c2597b8b` |
| `Racall-0.3.0-beta.1-mac-arm64.zip` | 160,944,057 | `389eaf63ccb73ad9676a0f2e1ccd506c21e8d5a6d27322da03649b735bd9979c` |
| `Racall-0.3.0-beta.1-linux-x86_64.AppImage` | 169,691,076 | `d5ebeb564ea1501e7adfcda5c0c17e921de4613bf64a958f7331fc37e6a0a7ea` |
| `Racall-0.3.0-beta.1-linux-amd64.deb` | 137,726,972 | `00c4443affc8850d0c52c76026ae8fd2d78d0ddd895fe841745db8a7762d8460` |
| `Racall-0.3.0-beta.1-linux-arm64.AppImage` | 168,159,616 | `66998671d64958892d031270844292d7b781e93fe4fd24d84ec578c0b0bce0a2` |
| `Racall-0.3.0-beta.1-linux-arm64.deb` | 128,832,232 | `9e8b726d73208f528e79688b84e2d0e83b2503087de430f57cc29d1d54698649` |

## Native fixes verified by this run

The downloaded job/artifact metadata and all six logged manifests were checked
for the same immutable source, exact declared target/package set, nonexpired
artifacts, file sizes and SHA-256 fields. The local evidence snapshot is
`test-results/native-candidates-40209217858/verification.json`, with a combined
`SHA256SUMS.txt`; `test-results/verify_native_candidates_03.py` validated it.
This checks CI provenance and recorded digests. Package binaries were not
downloaded and rehashed locally; they remain in the Actions artifacts.

Windows ARM64 and Intel macOS build locked `cryptography 50.0.1` from source
with native Rust and static OpenSSL; the pipeline preserves the OpenSSL notice.
Windows ARM64 pins the vcpkg/toolchain inputs, verifies a native ARM64 C object,
and exports compiler paths in the correct order. No crypto downgrade was used.

The installer uses `electron-builder 26.15.6`. Its
[upstream NSIS fix](https://github.com/electron-userland/electron-builder/pull/9989)
selects an archive filter readable by the install-time extractor. The preceding
26.15.3 candidate passed packaged app checks but failed installed-payload checks
on ARM64: a language seed was present while the application EXE was absent.
Keep the full installation check; an installer exit code alone is insufficient.

Generation without a configured model is rejected before queueing, preserving
the localized settings error. Hosted Windows/Linux Studio screenshots use a
visible window bounded by the runner's display; local test windows remain hidden.
Functional Studio checks remain required.

## Limits and publication

These are automated native candidate checks, not owner hands-on acceptance.
There is no Windows publisher signature or macOS Developer ID/notarization.
Downloaded-file quarantine, Gatekeeper prompts, every OS version, Linux desktop
environment and GPU configuration have not been certified. Intel macOS's
cryptography source build does not reinstate that dependency's upstream Intel
support.

No installed 0.2 binary was upgraded to 0.3. Portable 0.2 data compatibility and
same-version Windows reinstall checks do not establish that upgrade path.
No live cloud/Ollama/llama.cpp inference, real model download or model-quality
evaluation was performed. No local Docker/WSL workload was used.

No release tag or GitHub release was created. Publication remains explicitly
held; eventual publication still requires its approved policy and a matching
tag-triggered build. Windows x86/ia32, Linux x86/ARMv7 and a macOS universal bundle
are excluded for the reasons in [the native candidate scope](NATIVE_CANDIDATES_03.md).

