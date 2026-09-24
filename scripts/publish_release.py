"""Publish only a complete native-build artifact set; failed uploads remain drafts."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "package.json").read_text())["version"]
tag = "v" + version
assert os.environ["GITHUB_REF_NAME"] == tag
repo = os.environ["GITHUB_REPOSITORY"]
expected = [
    f"Racall-{version}-win-x64.exe",
    f"Racall-{version}-mac-arm64.dmg", f"Racall-{version}-mac-arm64.zip",
    f"Racall-{version}-mac-x64.dmg", f"Racall-{version}-mac-x64.zip",
    f"Racall-{version}-linux-x64.AppImage", f"Racall-{version}-linux-x64.deb",
]
files = [root / "release" / name for name in expected]
for file in files:
    assert file.is_file() and file.stat().st_size > 1_000_000, f"Missing/invalid package: {file.name}"
sums = root / "release/SHA256SUMS.txt"
lines = []
for file in files:
    with file.open("rb") as stream:
        lines.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {file.name}")
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
    label = json.loads((root / "apps/shared/release.json").read_text())["label"]
    gh("release", "create", tag, "--verify-tag", "--draft", "--title", "Racall " + label,
       "--notes-file", str(notes), *( ["--prerelease"] if "-" in version else [] ))
gh("release", "upload", tag, *(str(f) for f in [*files, sums]), "--clobber")
assets = json.loads(gh("release", "view", tag, "--json", "assets"))["assets"]
remote = {a["name"]: a["size"] for a in assets}
for file in [*files, sums]:
    assert remote.get(file.name) == file.stat().st_size, f"Incomplete upload: {file.name}"
gh("release", "edit", tag, "--draft=false")
print(f"Published {repo} {tag} with {len(files)} packages and SHA256SUMS.txt")
