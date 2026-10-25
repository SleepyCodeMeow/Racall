# Published 0.3 Beta verification — October 25, 2026

**[Racall 0.3 Beta](https://github.com/SleepyCodeMeow/Racall/releases/tag/v0.3.0-beta.1) was published at 2026-10-25T19:30:19Z and is GitHub Latest.**
The owner approved this beta with its documented model, hardware and distribution limits.

## Released source and packages

- Tag: `v0.3.0-beta.1`.
- Exact application source: `839d5219d9269071c07e61497061905cc3f707e9`.
- Fresh tag-push build and publication: [Actions run 40223957296](https://github.com/SleepyCodeMeow/Racall/actions/runs/40223957296).
- All six native targets passed **499 Python tests per target**, architecture, formatting, localization/version, frontend/type checks, packaged workflows and native installation/copy checks.
- The publication job completed successfully. Old workflow-dispatch candidates were not reused as this release build.

The uploaded set is exactly **ten distribution packages plus SHA256SUMS.txt**.
`BUILD.json` source/target manifests remain in the six Actions artifacts; they are
not additional public release assets. Each manifest was matched to the exact tag
source and approved release policy. All package names, sizes and SHA-256 digests
match across CI manifests, GitHub's uploaded-asset metadata and the downloaded
public checksum file. The checksum file's own remote digest was checked too:
`f5d61813293ca6fc553da394a909d8c093051d8b53e833d4718b896122c540ea`.

All eleven public download URLs returned HTTP 200 to anonymous HEAD requests,
with the expected content lengths. The public checksum file and the combined CI
checksum file are byte-for-byte identical. GitHub Latest points to this release;
its title and machine version retain Beta status even though GitHub's prerelease
flag is disabled for the Latest presentation.

| Package                                     |     Bytes | SHA256                                                             |
| ------------------------------------------- | --------: | ------------------------------------------------------------------ |
| `Racall-0.3.0-beta.1-win-x64.exe`           | 153279432 | `b968cb0f91f0ddfba481853c2949e0978d7d603a9634b18be6d76fde91dc1eb9` |
| `Racall-0.3.0-beta.1-win-arm64.exe`         | 145036660 | `d77520ac8453d397f3bfb362f4675055ee9ccb6a85d0596f3fe2c75e2935c290` |
| `Racall-0.3.0-beta.1-mac-arm64.dmg`         | 166815806 | `b4cf5d3c8246f519a4f72a9d8f519293826246e7506f1e893e0c0aaf0894d060` |
| `Racall-0.3.0-beta.1-mac-arm64.zip`         | 160958260 | `0fa27f6809c11e426b17a9dedbb42e5c114548b09c291bdef07a8039c8f31449` |
| `Racall-0.3.0-beta.1-mac-x64.dmg`           | 172192946 | `f0355f2d13c07be21f18a6a685f02b6c7d66788af17052ec0c81ee14d3b43573` |
| `Racall-0.3.0-beta.1-mac-x64.zip`           | 166265302 | `98a26e78f5afb4c971b91aaa7337115ef2ec9127393313189760d898a7e3ddc0` |
| `Racall-0.3.0-beta.1-linux-x86_64.AppImage` | 169707395 | `882f0189653b518123321c675c81e74063e1b7ee0ebeccbca161d880662e9256` |
| `Racall-0.3.0-beta.1-linux-amd64.deb`       | 137740860 | `ac4351b14652c064cb442ccd4f328f8136d0b9d1380b905af4242ea00bd434fd` |
| `Racall-0.3.0-beta.1-linux-arm64.AppImage`  | 168179919 | `b63d1e6655eb47c5b454ba9f2f6bc07a359f992d1b7408882389fd347ebeb905` |
| `Racall-0.3.0-beta.1-linux-arm64.deb`       | 128847192 | `a516c19dbfe6af05eac06f20141e1d52f0d16c127369803c60e2239ae9d5812a` |

## Exact released Windows upgrade

[Upgrade run 40225220035](https://github.com/SleepyCodeMeow/Racall/actions/runs/40225220035)
passed with the **same Windows x64 EXE and SHA256 shown above**, from release run
40223957296 / artifact 12611260738. It installed public 0.2, seeded synthetic
knowledge through that installed app, upgraded in place and exercised the new
installed 0.3. Both versions used the same default profile and executable path.

All nineteen previous authoritative files retained their size and SHA256 after
upgrade, UI checks, restart and uninstall. Twenty-one files remained: the old
nineteen plus a new completed job and material. Historical citations/originals,
legacy reports/export, EN/RU, light/dark and a new Studio job passed. Restart made
no automatic inference replay. The fixture recorded seven synthetic calls and no
errors; no real provider or model was used in this hosted upgrade check.

[Upgrade evidence](https://github.com/SleepyCodeMeow/Racall/actions/runs/40225220035/artifacts/12610937134)
includes input hashes, snapshots, result records, screenshots and logs. Its archive
is 248,403 bytes, SHA256
`3112d3acaad9b4a9017e17ae1d4d4a6ee860bde781a42e85b007e61e253972ef`.
No application was installed on the owner's PC by these hosted checks.

## Existing release preserved

The public 0.2 release ID, name, body, tag and publication date were compared
before/after. Both previous asset IDs, names, sizes, digests and upload timestamps
are unchanged. Its EXE remains 144,616,175 bytes with SHA256
`82fc01e779997f7fc4fe5c570cd371c6dc5d83cea0cf7d337b508332f45e02e0`.
Download counters may increase naturally; they are not content-integrity fields.
The 0.1 and 0.2 releases remain available separately.

## Model and platform limits

The [local Ollama report](MODEL_EVALUATION_03_2026-10-25.md) records 25 completed
workflow contracts, independent output review and observed critic false positives.
Application code under `apps/api`, `apps/web` and `apps/desktop` is unchanged from
that live-tested candidate; the release policy was subsequently approved.
Publication approval does not certify the critic or establish every hardware/model
combination. Cloud providers, llama.cpp and embeddings quality were not exercised
live. Generated facts still require review against their cited passages.

Windows packages are unsigned; macOS packages are unsigned and not notarized.
Hosted tests do not certify every OS release, physical device, Linux desktop,
quarantine dialog or AppImage FUSE mounting. The separate x64/ARM64 packages do
not include 32-bit or universal macOS binaries. See the release notes for details.

## Presentation and evidence

The project home keeps the raccoon logo, centered introduction and platform
links, now describing the actual 0.3 features. Its refreshed image is a real 0.3
frontend capture with sample documents, visible Apps/Studio/context/version and
the existing orange presentation backdrop. It made zero model or external requests;
[brand instructions](BRAND.md) describe reproduction. The bug form accepts OS,
architecture, provider/model and hardware details for community testing.

Local ignored evidence is under `test-results/release03-40223957296/`, including
`verified-release.json`, GitHub metadata, native logs/manifests, the actual public
checksum file and `public-download-links.json`. The exact-upgrade snapshots are
under `test-results/upgrade-release-40225220035/`. Subsequent documentation,
screenshot and test-harness commits do not move the tag or replace release assets.
