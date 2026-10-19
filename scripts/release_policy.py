"""Share the explicitly declared native release targets across CI and publication."""
import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReleaseTarget:
    os: str
    platform: str
    arch: str
    suffixes: tuple[str, ...]

    @property
    def job(self):
        return f"desktop ({self.os}, {self.platform}, {self.arch})"

    @property
    def artifact(self):
        return f"Racall-{self.platform}-{self.arch}"


TARGETS = {
    "win-x64": ReleaseTarget("windows-latest", "win", "x64", ("win-x64.exe",)),
    "mac-arm64": ReleaseTarget("macos-15", "mac", "arm64", ("mac-arm64.dmg", "mac-arm64.zip")),
    "mac-x64": ReleaseTarget("macos-15-intel", "mac", "x64", ("mac-x64.dmg", "mac-x64.zip")),
    "linux-x64": ReleaseTarget("ubuntu-22.04", "linux", "x64", ("linux-x86_64.AppImage", "linux-amd64.deb")),
}


def release_targets(policy):
    platforms = policy.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        raise ValueError("Declare a nonempty release platforms list")
    if any(not isinstance(name, str) or name not in TARGETS for name in platforms):
        raise ValueError("Unknown release platform")
    if len(platforms) != len(set(platforms)):
        raise ValueError("Release platforms must not contain duplicates")
    if type(policy.get("github_latest", False)) is not bool:
        raise ValueError("github_latest must be a boolean")
    return [TARGETS[name] for name in platforms]


def package_names(policy, version):
    return [f"Racall-{version}-{suffix}" for target in release_targets(policy) for suffix in target.suffixes]


def build_matrix(policy):
    return {"include": [{"os": target.os, "platform": target.platform, "arch": target.arch}
                        for target in release_targets(policy)]}


def verify_build(run, jobs, artifacts, tagged_sha, policy):
    """Require each declared native check and exactly its package artifacts."""
    targets = release_targets(policy)
    assert run["status"] == "completed", "The source build must have finished"
    assert run["event"] == "push" and run["path"] == ".github/workflows/build.yml"
    assert run["head_sha"] == tagged_sha, "Build must match release tag"
    expected_jobs = {target.job for target in targets}
    passed = {job["name"] for job in jobs if job["conclusion"] == "success"}
    assert expected_jobs <= passed, "Every declared native desktop build and packaged test must pass"
    expected_artifacts = {target.artifact for target in targets}
    package_artifacts = [artifact for artifact in artifacts if artifact["name"].startswith("Racall-")]
    assert {artifact["name"] for artifact in package_artifacts} == expected_artifacts, \
        "Build artifacts must exactly match declared release platforms"
    assert len(package_artifacts) == len(expected_artifacts), "Duplicate release artifact"
    assert all(not artifact["expired"] and artifact["size_in_bytes"] > 1_000_000
               for artifact in package_artifacts), "A required build artifact is absent or expired"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / "apps/shared/release.json").read_text(encoding="utf-8"))
    matrix = json.dumps(build_matrix(policy), separators=(",", ":"))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"matrix={matrix}\n")
    else:
        print(matrix)


if __name__ == "__main__":
    main()
