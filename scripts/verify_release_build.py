"""Authorize reuse of artifacts only from the tagged, fully tested desktop build."""
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
policy = json.loads((root / "apps/shared/release.json").read_text(encoding="utf-8"))
if policy.get("publication") != "approved":
    raise SystemExit("Publication is on hold. Release timing must be explicitly approved before publication.")
version = json.loads((root / "package.json").read_text())["version"]
tag = "v" + version
repo = os.environ["GITHUB_REPOSITORY"]
run_id = os.environ["RACALL_BUILD_RUN"]
assert run_id.isdigit(), "Build run ID must be numeric"


def api(path):
    return json.loads(subprocess.run(["gh", "api", f"repos/{repo}/{path}"],
                                    capture_output=True, text=True, check=True).stdout)


run = api(f"actions/runs/{run_id}")
assert run["status"] == "completed", "The source build must have finished"
assert run["event"] == "push" and run["path"] == ".github/workflows/build.yml"
ref = api(f"git/ref/tags/{tag}")["object"]
while ref["type"] == "tag":
    ref = api(f"git/tags/{ref['sha']}")["object"]
assert ref["type"] == "commit" and ref["sha"] == run["head_sha"], "Build must match release tag"
expected = {
    "desktop (windows-latest, win, x64)", "desktop (ubuntu-22.04, linux, x64)",
    "desktop (macos-15, mac, arm64)", "desktop (macos-15-intel, mac, x64)",
}
jobs = api(f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]
passed = {j["name"] for j in jobs if j["conclusion"] == "success"}
assert expected <= passed, "Every native desktop build and packaged test must pass"
artifacts = api(f"actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
expected_artifacts = {"Racall-win-x64", "Racall-linux-x64", "Racall-mac-arm64", "Racall-mac-x64"}
available = {a["name"] for a in artifacts if not a["expired"] and a["size_in_bytes"] > 1_000_000}
assert expected_artifacts <= available, "A required build artifact is absent or expired"
with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env:
    env.write(f"RACALL_RELEASE_TAG={tag}\n")
print(f"Verified {tag} at {ref['sha']} from build {run_id}")
