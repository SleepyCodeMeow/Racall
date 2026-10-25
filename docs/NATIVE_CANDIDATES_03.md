# Native 0.3 build candidates

The owner requested Windows, Linux and macOS packages, then expanded the request
to the full supported processor-architecture matrix. These builds are candidates.
`apps/shared/release.json` remains on publication hold. Do not create a release
tag or publish a GitHub release merely because a candidate build passes.

| Target | Native GitHub runner | Distribution files |
| --- | --- | --- |
| Windows x64 | `windows-latest` | `win-x64.exe` |
| Windows ARM64 | `windows-11-arm` | `win-arm64.exe` |
| macOS Intel x64 | `macos-15-intel` | `mac-x64.dmg`, `mac-x64.zip` |
| macOS Apple Silicon ARM64 | `macos-15` | `mac-arm64.dmg`, `mac-arm64.zip` |
| Linux x64 | `ubuntu-22.04` | `linux-x86_64.AppImage`, `linux-amd64.deb` |
| Linux ARM64 | `ubuntu-22.04-arm` | `linux-arm64.AppImage`, `linux-arm64.deb` |

Each filename starts with `Racall-0.3.0-beta.1-`. Candidate archives also contain
`BUILD.json` identifying the exact source and target, plus `SHA256SUMS.txt` for the
distribution files. The authoritative packaging matrix is
[release_policy.py](../scripts/release_policy.py).

## Processor and package checks

The workflow selects native Node.js and Python, builds the Python service on its
target host, and verifies interpreter and executable architectures. The Electron
shell and bundled service must agree with the requested target. Emulated x64
execution does not count as a native ARM64 build. NSIS's installer bootstrap can
have a different architecture from the application payload.

The package checks exercise the actual frozen backend and Electron workflows,
then installation/copy paths: NSIS install/uninstall, DMG mount and application
copy, Debian install/remove, and extracted AppImage execution. AppImage FUSE
mounting, all desktop environments, download-quarantine dialogs, every OS release
and real model quality are not certified by these automated checks.

## Dependency toolchains

The current lock retains `cryptography 50.0.1`. Its native wheels cover Linux and
Apple Silicon but not Windows ARM64 or Intel macOS. The latter targets need a
source build with Rust and statically linked OpenSSL. Windows ARM64 uses the
dedicated [toolchain bootstrap](../scripts/prepare_windows_arm64.ps1); Intel macOS
uses the native Homebrew OpenSSL and Rust toolchain on its hosted runner.

Upstream pyca removed Intel macOS support in version 49. A successful Racall
candidate demonstrates this particular application's tested build; it does not
restore upstream support. Do not downgrade to cryptography 48.0.1 merely to get
an Intel wheel: [GHSA-g6cj-pr64-35w5](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5)
was patched in 50.0.0. See the [current source-build instructions](https://cryptography.io/en/50.0.2/installation/).

## 32-bit and universal packages

Electron 44.4.5, pinned by Racall, does not publish Windows `ia32` or Linux
`armv7l` binaries. This candidate matrix therefore has no Windows x86, Linux x86
or ARMv7 packages. Supporting them would require a separately maintained legacy
stack. See the [Electron 44 announcement](https://www.electronjs.org/blog/electron-44-0).

Mac x64 and ARM64 are separate native packages. A universal Electron shell would
also require a genuinely universal Python service and every native dependency;
simply adding `--universal` is insufficient for this architecture.

## Distribution boundaries

The current pipeline has no Developer ID/notarization credentials or Windows
publisher certificate. Do not describe these candidates as signed/notarized
distribution builds. Local Docker/WSL or macOS hardware is not needed to run the
hosted matrix. Hosted execution and its artifacts do not publish a release.
