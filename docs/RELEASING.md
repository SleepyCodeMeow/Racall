# Releasing Racall

## Version policy

Use a readable release name such as **Racall 0.1 Beta**, with a machine version `0.1.0-beta.1` and Git tag `v0.1.0-beta.1`. A beta correction can be `0.1.0-beta.2`; the next feature releases are `0.2.0-beta.1` and `0.3.0-beta.1`. Python metadata uses the equivalent PEP 440 form, such as `0.1.0b1`.

Update `package.json`, the root entries in `package-lock.json`, `pyproject.toml`, `uv.lock`, `apps/shared/release.json` and `apps/api/on_knowledge/version.py`. Add matching `docs/releases/<version>.md`, update CHANGELOG and README. `npm run check:release` rejects version drift and a mismatched release tag.

## Before tagging

Run the documented checks and packaged smoke tests. Review the staged files for secrets, documents, generated artifacts and machine-specific paths. Build on each native target; Python executables are not cross-compiled. Record known limits and model/OS verification honestly. Do not call unsigned builds signed or notarized.

Push the branch and wait for all CI platforms to pass. Then create and push the matching annotated tag. The tag workflow repeats checks and builds on Windows x64, macOS arm64/x64 and Linux x64. A separate publication job receives write permission only for tags.

## Publication

After all platforms pass, the workflow downloads the seven installers/archives, computes SHA-256 checksums, creates a draft GitHub release, uploads all assets, then publishes it as a prerelease when the version has a prerelease suffix. It never uploads API keys, test profiles or source documents. A failed upload leaves a draft rather than a partial public release; rerunning can finish that draft. It will not replace an already-published release.

Download and test the actual installer after publication. CI launches unpacked packaged apps, which does not cover every OS installer flow or permissions dialog. This beta has no automatic updater; users install later releases manually. Existing data and language preferences must survive upgrades.

GitHub is the project's home: README, docs, Issues, Releases and Actions. No website or website secret is required. Standard `GITHUB_TOKEN` with `contents: write` in the publication job is sufficient. Signing/notarization certificates are optional future additions; no fabricated signing settings belong in the workflow.

## Recover a publication-only failure

If all four native jobs passed but publishing failed, fix the publication script on main. Run **Publish verified existing build** from Actions and enter the completed build run ID. It verifies the run belongs to this repository's build workflow, all four native jobs passed, artifacts are available, and its commit exactly matches the current version tag. It reuses those packages and never moves the tag. Current main version metadata must still match the tag being published. An already-public release is never overwritten.

Linux filenames use packaging-native architecture names: `linux-x86_64.AppImage` and `linux-amd64.deb` for x64 builds.
