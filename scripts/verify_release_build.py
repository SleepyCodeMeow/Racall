"""Authorize reuse only from the tagged build of every declared native target."""
import base64
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
policy = json.loads((root / "apps/shared/release.json").read_text(encoding="utf-8"))
if policy.get("publication") != "approved":
    raise SystemExit("Publication is on hold. Release timing must be explicitly approved before publication.")

from release_policy import release_targets, verify_build  # noqa: E402

version = json.loads((root / "package.json").read_text())["version"]
assert policy["version"] == version, "Release policy must match package version"
release_targets(policy)
tag = "v" + version
repo = os.environ["GITHUB_REPOSITORY"]
run_id = os.environ["RACALL_BUILD_RUN"]
assert run_id.isdigit(), "Build run ID must be numeric"


def api(path):
    return json.loads(subprocess.run(["gh", "api", f"repos/{repo}/{path}"],
                                    capture_output=True, text=True, check=True).stdout)


run = api(f"actions/runs/{run_id}")
ref = api(f"git/ref/tags/{tag}")["object"]
while ref["type"] == "tag":
    ref = api(f"git/tags/{ref['sha']}")["object"]
assert ref["type"] == "commit", "Release tag must resolve to a commit"
source_policy = api(f"contents/apps/shared/release.json?ref={ref['sha']}")
assert source_policy["encoding"] == "base64", "Unexpected release-policy content encoding"
tagged_policy = json.loads(base64.b64decode(source_policy["content"]))
assert tagged_policy == policy, "Current release policy must exactly match the tagged build policy"
jobs = api(f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]
artifacts = api(f"actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
verify_build(run, jobs, artifacts, ref["sha"], policy)
with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env:
    env.write(f"RACALL_RELEASE_TAG={tag}\n")
print(f"Verified {tag} at {ref['sha']} from build {run_id}")
