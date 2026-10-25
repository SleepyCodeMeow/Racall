"""Release policy must narrow platform scope explicitly without weakening provenance."""

import base64
import hashlib
import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
helpers = runpy.run_path(str(ROOT / "scripts/release_policy.py"))
VERSION = "0.2.0-beta.1"
SHA = "a" * 40


def policy(**changes):
    return {
        "version": VERSION,
        "label": "0.2 Beta",
        "publication": "approved",
        "platforms": ["win-x64"],
        "github_latest": True,
        **changes,
    }


@pytest.mark.parametrize("platforms", [None, [], "win-x64", ["unknown"], ["win-x64", "win-x64"], [None]])
def test_invalid_platform_scope_fails_closed(platforms):
    with pytest.raises(ValueError):
        helpers["release_targets"](policy(platforms=platforms))


@pytest.mark.parametrize("value", ["true", 1, None])
def test_latest_requires_a_real_boolean(value):
    with pytest.raises(ValueError, match="boolean"):
        helpers["release_targets"](policy(github_latest=value))


def test_windows_only_and_all_native_platforms_use_one_package_map():
    assert helpers["package_names"](policy(), VERSION) == [f"Racall-{VERSION}-win-x64.exe"]
    assert helpers["build_matrix"](policy()) == {
        "include": [{"os": "windows-latest", "platform": "win", "arch": "x64"}]
    }
    all_policy = policy(platforms=["win-x64", "mac-arm64", "mac-x64", "linux-x64"])
    assert set(helpers["package_names"](all_policy, VERSION)) == {
        f"Racall-{VERSION}-{suffix}"
        for suffix in (
            "win-x64.exe",
            "mac-arm64.dmg",
            "mac-arm64.zip",
            "mac-x64.dmg",
            "mac-x64.zip",
            "linux-x86_64.AppImage",
            "linux-amd64.deb",
        )
    }
    assert len(helpers["build_matrix"](all_policy)["include"]) == 4


def test_six_native_targets_have_distinct_packages_and_native_arm_runners():
    complete = policy(platforms=["win-x64", "win-arm64", "mac-x64", "mac-arm64", "linux-x64", "linux-arm64"])
    packages = helpers["package_names"](complete, VERSION)
    assert len(packages) == len(set(packages)) == 10
    assert f"Racall-{VERSION}-win-arm64.exe" in packages
    assert f"Racall-{VERSION}-linux-arm64.deb" in packages
    assert f"Racall-{VERSION}-linux-arm64.AppImage" in packages
    matrix = helpers["build_matrix"](complete)["include"]
    assert len(matrix) == 6
    assert {item["os"] for item in matrix if item["arch"] == "arm64"} == {
        "windows-11-arm",
        "macos-15",
        "ubuntu-22.04-arm",
    }


def build_evidence():
    return (
        {"status": "completed", "event": "push", "path": ".github/workflows/build.yml", "head_sha": SHA},
        [{"name": "desktop (windows-latest, win, x64)", "conclusion": "success"}],
        [{"name": "Racall-win-x64", "expired": False, "size_in_bytes": 1_000_001}],
    )


def test_windows_build_passes_without_claiming_other_platforms():
    helpers["verify_build"](*build_evidence(), SHA, policy())
    with pytest.raises(AssertionError, match="Every declared"):
        helpers["verify_build"](*build_evidence(), SHA, policy(platforms=["win-x64", "linux-x64"]))


@pytest.mark.parametrize(
    "bad",
    ["sha", "event", "workflow", "pending", "failed", "missing", "expired", "empty", "extra", "duplicate"],
)
def test_unverified_or_wrong_artifacts_cannot_authorize_reuse(bad):
    run, jobs, artifacts = build_evidence()
    if bad == "sha":
        run["head_sha"] = "b" * 40
    elif bad == "event":
        run["event"] = "workflow_dispatch"
    elif bad == "workflow":
        run["path"] = ".github/workflows/other.yml"
    elif bad == "pending":
        run["status"] = "in_progress"
    elif bad == "failed":
        jobs[0]["conclusion"] = "failure"
    elif bad == "missing":
        artifacts.clear()
    elif bad == "expired":
        artifacts[0]["expired"] = True
    elif bad == "empty":
        artifacts[0]["size_in_bytes"] = 0
    elif bad == "extra":
        artifacts.append({"name": "Racall-linux-x64", "expired": False, "size_in_bytes": 1_000_001})
    elif bad == "duplicate":
        artifacts.append(artifacts[0].copy())
    with pytest.raises(AssertionError):
        helpers["verify_build"](run, jobs, artifacts, SHA, policy())


@pytest.fixture
def release_tree(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    for name in ("release_policy.py", "publish_release.py", "verify_release_build.py"):
        shutil.copyfile(ROOT / "scripts" / name, tmp_path / "scripts" / name)
    (tmp_path / "apps/shared").mkdir(parents=True)
    (tmp_path / "apps/shared/release.json").write_text(json.dumps(policy()), encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"version": VERSION}), encoding="utf-8")
    (tmp_path / "docs/releases").mkdir(parents=True)
    (tmp_path / f"docs/releases/{VERSION}.md").write_text("Beta notes", encoding="utf-8")
    (tmp_path / "release").mkdir()
    package = tmp_path / f"release/Racall-{VERSION}-win-x64.exe"
    package.write_bytes(b"p" * 1_000_001)
    monkeypatch.syspath_prepend(str(tmp_path / "scripts"))
    monkeypatch.setenv("RACALL_RELEASE_TAG", "v" + VERSION)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("RACALL_BUILD_RUN", "12345")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "github-env"))
    return tmp_path


def test_ci_output_uses_the_same_declared_matrix(release_tree, monkeypatch):
    output = release_tree / "github-output"
    script = str(release_tree / "scripts/release_policy.py")
    monkeypatch.setattr(sys, "argv", [script, "--github-output", str(output)])
    runpy.run_path(script, run_name="__main__")
    name, matrix = output.read_text().strip().split("=", 1)
    assert name == "matrix"
    assert json.loads(matrix) == helpers["build_matrix"](policy())


def test_wrong_release_tag_stops_before_external_actions(release_tree, monkeypatch):
    monkeypatch.setenv("RACALL_RELEASE_TAG", "v0.1.0-beta.1")

    def unexpected_action(*args, **kwargs):
        pytest.fail("A mismatched tag must fail before calling GitHub")

    monkeypatch.setattr(subprocess, "run", unexpected_action)
    with pytest.raises(AssertionError):
        runpy.run_path(str(release_tree / "scripts/publish_release.py"))


@pytest.mark.parametrize("latest", [True, False])
def test_publication_exact_assets_checksums_and_explicit_latest(release_tree, monkeypatch, latest):
    (release_tree / "apps/shared/release.json").write_text(json.dumps(policy(github_latest=latest)))
    commands = []

    def fake_gh(args, **kwargs):
        commands.append(args)
        assert args[0] == "gh"
        if args[1:3] == ["release", "list"]:
            result = []
        elif args[1:3] == ["release", "view"]:
            result = {
                "assets": [
                    {"name": file.name, "size": file.stat().st_size}
                    for file in (release_tree / "release").iterdir()
                ]
            }
        else:
            result = {}
        return SimpleNamespace(stdout=json.dumps(result))

    monkeypatch.setattr(subprocess, "run", fake_gh)
    runpy.run_path(str(release_tree / "scripts/publish_release.py"))
    create = next(args for args in commands if args[1:3] == ["release", "create"])
    assert "--verify-tag" in create and "--draft" in create
    assert "--title" in create and create[create.index("--title") + 1] == "Racall 0.2 Beta"
    edit = commands[-1]
    assert edit[1:3] == ["release", "edit"] and "--draft=false" in edit
    assert "--latest=" + str(latest).lower() in edit
    assert "--prerelease=" + str(not latest).lower() in edit
    name = f"Racall-{VERSION}-win-x64.exe"
    expected_hash = hashlib.sha256((release_tree / "release" / name).read_bytes()).hexdigest()
    assert (release_tree / "release/SHA256SUMS.txt").read_text() == f"{expected_hash}  {name}\n"


@pytest.mark.parametrize("failure", ["published", "missing", "extra", "remote-extra", "upload"])
def test_failed_publication_never_goes_public(release_tree, monkeypatch, failure):
    commands = []
    if failure == "missing":
        (release_tree / f"release/Racall-{VERSION}-win-x64.exe").unlink()
    if failure == "extra":
        (release_tree / f"release/Racall-{VERSION}-linux-amd64.deb").write_bytes(b"p")

    def fake_gh(args, **kwargs):
        commands.append(args)
        if args[1:3] == ["release", "list"]:
            result = [{"tagName": "v" + VERSION, "isDraft": False}] if failure == "published" else []
        elif args[1:3] == ["release", "upload"] and failure == "upload":
            raise subprocess.CalledProcessError(1, args)
        elif args[1:3] == ["release", "view"]:
            result = {
                "assets": [
                    {"name": file.name, "size": file.stat().st_size}
                    for file in (release_tree / "release").iterdir()
                ]
            }
            if failure == "remote-extra":
                result["assets"].append({"name": "unexpected.zip", "size": 10})
        else:
            result = {}
        return SimpleNamespace(stdout=json.dumps(result))

    monkeypatch.setattr(subprocess, "run", fake_gh)
    with pytest.raises((AssertionError, subprocess.CalledProcessError)):
        runpy.run_path(str(release_tree / "scripts/publish_release.py"))
    assert not any(args[1:3] == ["release", "edit"] for args in commands)
    if failure in {"published", "missing", "extra"}:
        assert not any(args[1:3] == ["release", "upload"] for args in commands)


@pytest.mark.parametrize("changed_policy", [False, True])
def test_reuse_requires_the_exact_tagged_policy(release_tree, monkeypatch, changed_policy):
    run, jobs, artifacts = build_evidence()
    source = policy(platforms=["win-x64", "linux-x64"]) if changed_policy else policy()
    replies = {
        "actions/runs/12345": run,
        "git/ref/tags/v" + VERSION: {"object": {"type": "tag", "sha": "c" * 40}},
        "git/tags/" + "c" * 40: {"object": {"type": "commit", "sha": SHA}},
        f"contents/apps/shared/release.json?ref={SHA}": {
            "encoding": "base64",
            "content": base64.b64encode(json.dumps(source).encode()).decode(),
        },
        "actions/runs/12345/jobs?per_page=100": {"jobs": jobs},
        "actions/runs/12345/artifacts?per_page=100": {"artifacts": artifacts},
    }

    def fake_api(args, **kwargs):
        assert args[:2] == ["gh", "api"]
        return SimpleNamespace(stdout=json.dumps(replies[args[2].removeprefix("repos/owner/repo/")]))

    monkeypatch.setattr(subprocess, "run", fake_api)
    script = str(release_tree / "scripts/verify_release_build.py")
    if changed_policy:
        with pytest.raises(AssertionError, match="tagged build policy"):
            runpy.run_path(script)
        assert not (release_tree / "github-env").exists()
    else:
        runpy.run_path(script)
        assert (release_tree / "github-env").read_text() == f"RACALL_RELEASE_TAG=v{VERSION}\n"
