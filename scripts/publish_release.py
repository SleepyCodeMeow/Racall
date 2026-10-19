"""Publish the complete declared native package set; failed uploads remain drafts."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
policy = json.loads((root / "apps/shared/release.json").read_text(encoding="utf-8"))
if policy.get("publication") != "approved":
    raise SystemExit("Publication is on hold. Release timing must be explicitly approved before publication.")

from release_policy import package_names  # noqa: E402

version = json.loads((root / "package.json").read_text())["version"]
assert policy["version"] == version, "Release policy must match package version"
tag = "v" + version
assert (os.environ.get("RACALL_RELEASE_TAG") or os.environ.get("GITHUB_REF_NAME")) == tag
repo = os.environ["GITHUB_REPOSITORY"]
expected = package_names(policy, version)
files = [root / "release" / name for name in expected]
packages = {file.name for file in (root / "release").iterdir()
            if file.is_file() and file.suffix in {".exe", ".dmg", ".zip", ".AppImage", ".deb"}}
assert packages == set(expected), "Package files must exactly match declared release platforms"
for file in files:
    assert file.is_file() and file.stat().st_size > 1_000_000, f"Missing/invalid package: {file.name}"
sums = root / "release/SHA256SUMS.txt"
lines = []
for file in files:
    with file.open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        lines.append(f"{digest.hexdigest()}  {file.name}")
sums.write_text("\n".join(lines) + "\n")
notes = root / f"docs/releases/{version}.md"
assert notes.is_file()
def gh(*args):
    return subprocess.run(["gh", *args, "--repo", repo], check=True, text=True, capture_output=True).stdout
# List releases instead of treating authentication/network errors as a missing release.
releases = json.loads(gh("release", "list", "--limit", "100", "--json", "tagName,isDraft"))
existing = next((r for r in releases if r["tagName"] == tag), None)
if existing:
    assert existing["isDraft"], "Never overwrite a published release; increment the version."
else:
    label = policy["label"]
    gh("release", "create", tag, "--verify-tag", "--draft", "--title", "Racall " + label,
       "--notes-file", str(notes), "--prerelease=" + str(not policy.get("github_latest", False)).lower())
gh("release", "upload", tag, *(str(f) for f in [*files, sums]), "--clobber")
assets = json.loads(gh("release", "view", tag, "--json", "assets"))["assets"]
remote = {a["name"]: a["size"] for a in assets}
assert len(assets) == len(remote) and set(remote) == {file.name for file in [*files, sums]}, \
    "Release assets must exactly match declared packages and SHA256SUMS.txt"
for file in [*files, sums]:
    assert remote.get(file.name) == file.stat().st_size, f"Incomplete upload: {file.name}"
latest = policy.get("github_latest", False)
gh("release", "edit", tag, "--draft=false", "--prerelease=" + str(not latest).lower(),
   "--latest=" + str(latest).lower())
print(f"Published {repo} {tag} with {len(files)} packages and SHA256SUMS.txt")
