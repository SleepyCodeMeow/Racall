"""Reject inconsistent package, service, UI and tag versions before release."""
import json
import os
import re
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
package = json.loads((root / "package.json").read_text(encoding="utf-8"))
version = package["version"]
match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:-beta\.(\d+))?", version)
assert match, f"Unsupported version: {version}"
python_version = match[1] + ("b" + match[2] if match[2] else "")
lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
assert lock["version"] == lock["packages"][""]["version"] == version
project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
assert project["project"]["version"] == python_version
uv = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
assert next(p["version"] for p in uv["package"] if p["name"] == project["project"]["name"]) == python_version
release = json.loads((root / "apps/shared/release.json").read_text())
assert release["version"] == version
assert release.get("publication") in ("hold", "approved"), "Declare publication hold/approval explicitly"
assert (root / "apps/api/on_knowledge/version.py").read_text().strip() == f'VERSION = "{version}"'
assert (root / f"docs/releases/{version}.md").is_file(), "Release notes are missing"
if os.environ.get("GITHUB_REF_TYPE") == "tag":
    assert os.environ["GITHUB_REF_NAME"] == "v" + version, "Tag must match package version"
print(f"Release metadata consistent: {version} / Python {python_version}")
