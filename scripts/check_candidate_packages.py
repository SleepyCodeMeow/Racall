"""Record verified candidate package names, source and SHA-256 without publishing."""

import hashlib
import json
import os
from pathlib import Path

from release_policy import release_targets


def manifest(root: Path, platform: str, arch: str, source: str) -> dict:
    policy = json.loads((root / "apps/shared/release.json").read_text("utf-8"))
    version = json.loads((root / "package.json").read_text("utf-8"))["version"]
    if policy["version"] != version:
        raise ValueError("Candidate version differs from release policy.")
    target = next(
        (item for item in release_targets(policy) if item.platform == platform and item.arch == arch), None
    )
    if target is None:
        raise ValueError("Candidate target is not declared in release policy.")
    files = [root / "release" / f"Racall-{version}-{suffix}" for suffix in target.suffixes]
    records = []
    for file in files:
        if not file.is_file() or file.stat().st_size <= 1_000_000:
            raise ValueError("Missing or invalid candidate package: " + file.name)
        with file.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        records.append({"name": file.name, "size": file.stat().st_size, "sha256": digest})
    return {
        "version": version,
        "source": source,
        "platform": platform,
        "arch": arch,
        "publication": policy["publication"],
        "packages": records,
    }


def main():
    root = Path(__file__).resolve().parents[1]
    result = manifest(
        root, os.environ["RACALL_TARGET_PLATFORM"], os.environ["RACALL_TARGET_ARCH"], os.environ["GITHUB_SHA"]
    )
    (root / "release/BUILD.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (root / "release/SHA256SUMS.txt").write_text(
        "".join(f"{item['sha256']}  {item['name']}\n" for item in result["packages"]), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
