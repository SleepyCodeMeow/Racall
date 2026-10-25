# Releasing Racall

## Version policy

Use a readable release name such as **Racall 0.1 Beta**, with a machine version `0.1.0-beta.1` and Git tag `v0.1.0-beta.1`. A beta correction can be `0.1.0-beta.2`; the next feature releases are `0.2.0-beta.1` and `0.3.0-beta.1`. Python metadata uses the equivalent PEP 440 form, such as `0.1.0b1`.

Update `package.json`, the root entries in `package-lock.json`, `pyproject.toml`, `uv.lock`, `apps/shared/release.json` and `apps/api/on_knowledge/version.py`. Add matching `docs/releases/<version>.md`, update CHANGELOG and README. `npm run check:release` rejects version drift and a mismatched release tag.

## Publication hold and release spacing

`apps/shared/release.json` declares publication approval and the exact native platform scope. Both publication scripts refuse to proceed while `publication` is `"hold"`. Building, testing and saving candidate installers do not by themselves approve publication.

Only after the owner explicitly chooses the release timing may the maintainer change the value to `"approved"`, complete the final checklist and create a release tag. Do not infer a date or minimum interval, schedule automatic publication, or clear the hold merely because CI passed. Return the next development version to `"hold"`. See the [current release checklist](RELEASE_03_CHECKLIST.md).

On **October 19, 2026**, the owner explicitly approved publishing **Racall 0.2 Beta for Windows x64**. Its policy is `publication: "approved"`, `platforms: ["win-x64"]`, `github_latest: true`. macOS and Linux are not included in this release's packages or acceptance claim. The required fresh native build and publication passed in [run 39257810891](https://github.com/SleepyCodeMeow/Racall/actions/runs/39257810891), from the exact tagged source `70fd79bd69cef06d88c03e1fa5ff88929fc1fa3e`; old native CI and the earlier local candidate were not reused as the released build.

On **October 25, 2026**, the owner explicitly approved **0.3 Beta** for all six
x64/ARM64 targets on Windows, macOS and Linux, with the same GitHub Latest
presentation. The owner accepted limited hardware/model coverage and requested
community testing after being informed of local critic false positives. This
approval permits publication; it does not turn the open model-reliability gate
into a passed test. Preserve the [evaluation results](MODEL_EVALUATION_03_2026-10-25.md)
and the release's known limitations.

Supported platform identifiers are `win-x64`, `win-arm64`, `mac-arm64`, `mac-x64`,
`linux-x64` and `linux-arm64`. The nonempty, unique list is validated by
`scripts/release_policy.py` and drives the CI matrix, required native jobs,
reusable artifacts and exact package names. Expanding a future release requires
explicitly adding its platforms and passing their native checks. Do not silently
treat missing platform builds as accepted. The 0.3 policy declares all six
targets with publication approved by the owner.

## Before tagging

Run the documented checks and packaged smoke tests. Review the staged files for secrets, documents, generated artifacts and machine-specific paths. Build on each declared native target; Python executables are not cross-compiled. Record known limits and model/OS verification honestly. Do not call unsigned builds signed or notarized.

Push the prepared source branch. A branch CI pass can provide a preliminary check; publication always waits for the full fresh tag build. After explicit release-timing approval and removal of the publication hold, create and push the matching annotated tag at that exact source commit. The tag workflow runs all checks and builds for the declared platforms before publishing. A separate publication job receives write permission only for tags. The 0.3 policy requires all six native jobs, without starting local Docker/WSL. The default branch may then be fast-forwarded to the verified source, with a separate documentation commit recording the resulting run.

## Publication

After every declared platform passes, the workflow downloads exactly its installers/archives, computes SHA-256 checksums, creates a draft GitHub release, uploads all assets, verifies the exact asset names and sizes, then publishes. Windows-only 0.2 has one EXE plus `SHA256SUMS.txt`; all six platform targets require ten installers/archives plus checksums. Extra or missing distribution packages/assets cause publication to stop. It never uploads API keys, test profiles or source documents. A failed upload leaves a draft rather than a partial public release; rerunning can finish that draft. It will not replace an already-published release.

Before publication, CI checks unpacked apps plus the installer paths for each declared platform: Windows NSIS installation/uninstallation, macOS DMG copy/launch, Debian package installation/removal and extracted AppImage launch. These automated checks do not cover every interactive permissions or Gatekeeper dialog. Describe any unperformed manual acceptance and signing status honestly. The owner waived mandatory final live-model and hands-on acceptance for the first Windows 0.2 Beta, as recorded in the checklist. This beta has no automatic updater; users install later releases manually. Existing data and language preferences must survive upgrades.

GitHub is the project's home: README, docs, Issues, Releases and Actions. No website or website secret is required. Standard `GITHUB_TOKEN` with `contents: write` in the publication job is sufficient. Signing/notarization certificates are optional future additions; no fabricated signing settings belong in the workflow.

## GitHub Latest and the public beta

The earlier **Racall 0.1 Beta** was designated as GitHub Latest so it appeared in the repository sidebar. The same presentation is selected for **0.2 Beta** and **0.3 Beta**. GitHub does not allow a prerelease to be Latest, so its GitHub prerelease flag is disabled. The product remains a beta: its title, version, tag, assets and documented limitations retain that status. This presentation does not certify production readiness.

By default the workflow publishes a GitHub prerelease and explicitly avoids Latest. An explicitly declared `github_latest: true` publishes with GitHub's prerelease flag disabled and Latest enabled, while preserving the product's Beta title/version/limits. The value must be a JSON boolean. This is the approved presentation for 0.3 Beta, matching the earlier sidebar presentation. Do not recreate a release, move its tag or replace assets merely to change this display.

## Recover a publication-only failure

If every declared native job passed but publishing failed, fix the publication script on main. Run **Publish verified existing build** from Actions and enter the completed build run ID. It verifies the run belongs to this repository's push build workflow, all declared native jobs passed, exactly their package artifacts are available and unexpired, and its commit exactly matches the current version tag. The current release policy must exactly match the policy read from that tagged source commit, so changing main cannot retroactively lower its platform requirements. It reuses those packages and never moves the tag. Current main version metadata must still match the tag being published. An already-public release is never overwritten.

Linux filenames use packaging-native architecture names: `linux-x86_64.AppImage` and `linux-amd64.deb` for x64 builds.
