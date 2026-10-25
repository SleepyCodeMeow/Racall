import hashlib
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    helper = runpy.run_path(str(ROOT / "scripts/check_candidate_packages.py"))["manifest"]
    (tmp_path / "apps/shared").mkdir(parents=True)
    (tmp_path / "apps/shared/release.json").write_text(
        json.dumps(
            {
                "version": "0.3.0-beta.1",
                "publication": "hold",
                "platforms": ["linux-arm64"],
            }
        )
    )
    (tmp_path / "package.json").write_text(json.dumps({"version": "0.3.0-beta.1"}))
    (tmp_path / "release").mkdir()
    for suffix in ("linux-arm64.deb", "linux-arm64.AppImage"):
        (tmp_path / "release" / ("Racall-0.3.0-beta.1-" + suffix)).write_bytes(b"a" * 1_000_001)
    return tmp_path, helper


def test_candidate_manifest_binds_packages_to_architecture_source_and_hash(candidate):
    root, helper = candidate
    result = helper(root, "linux", "arm64", "a" * 40)
    assert result["source"] == "a" * 40 and result["publication"] == "hold"
    assert len(result["packages"]) == 2
    assert all(
        item["sha256"] == hashlib.sha256(b"a" * 1_000_001).hexdigest() and item["size"] == 1_000_001
        for item in result["packages"]
    )


def test_x64_packages_cannot_satisfy_an_arm64_candidate(candidate):
    root, helper = candidate
    path = root / "release/Racall-0.3.0-beta.1-linux-arm64.deb"
    path.rename(root / "release/Racall-0.3.0-beta.1-linux-amd64.deb")
    with pytest.raises(ValueError, match="Missing or invalid"):
        helper(root, "linux", "arm64", "a" * 40)


def test_undeclared_target_cannot_be_presented_as_verified(candidate):
    root, helper = candidate
    with pytest.raises(ValueError, match="not declared"):
        helper(root, "win", "arm64", "a" * 40)
