"""Reject emulated/mixed Python, Electron and frozen backend architecture labels."""
import argparse
import json
import os
import platform
import struct
import subprocess
import sys
import sysconfig
from pathlib import Path

PLATFORMS = {"win32": "win", "darwin": "mac", "linux": "linux"}
MACHINES = {"AMD64": "x64", "x86_64": "x64", "ARM64": "arm64", "aarch64": "arm64", "arm64": "arm64"}


def python_architecture() -> str:
    if struct.calcsize("P") != 8:
        raise ValueError("Only 64-bit native Python is supported.")
    if sys.platform == "win32":
        value = sysconfig.get_platform().lower()
        result = {"win-amd64": "x64", "win-arm64": "arm64"}.get(value)
    else:
        result = MACHINES.get(platform.machine())
    if result is None:
        raise ValueError("Unsupported Python architecture: " + sysconfig.get_platform())
    return result


def binary_architecture(path: Path) -> str:
    with path.open("rb") as stream:
        header = stream.read(64)
        if header[:2] == b"MZ" and len(header) == 64:
            stream.seek(struct.unpack_from("<I", header, 60)[0])
            signature = stream.read(6)
            if signature[:4] != b"PE\0\0":
                raise ValueError("Invalid PE signature: " + str(path))
            machine = struct.unpack_from("<H", signature, 4)[0]
            result = {0x8664: "x64", 0xAA64: "arm64"}.get(machine)
        elif header[:4] == b"\x7fELF" and len(header) >= 20:
            if header[4] != 2 or header[5] not in (1, 2):
                raise ValueError("Expected a 64-bit ELF executable: " + str(path))
            machine = struct.unpack_from("<H" if header[5] == 1 else ">H", header, 18)[0]
            result = {62: "x64", 183: "arm64"}.get(machine)
        elif header[:4] in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf") and len(header) >= 8:
            machine = struct.unpack_from("<I" if header[:1] == b"\xcf" else ">I", header, 4)[0]
            result = {0x01000007: "x64", 0x0100000C: "arm64"}.get(machine)
        else:
            raise ValueError("Expected a native PE, ELF or Mach-O executable: " + str(path))
    if result is None:
        raise ValueError("Unsupported executable architecture: " + str(path))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, action="append", default=[])
    args = parser.parse_args()
    host_platform = PLATFORMS[sys.platform]
    arch = python_architecture()
    target = os.environ.get("RACALL_TARGET_ARCH", arch)
    target_platform = os.environ.get("RACALL_TARGET_PLATFORM", host_platform)
    if target != arch or target_platform != host_platform:
        raise ValueError(f"Expected native {target_platform}/{target}, running Python {host_platform}/{arch}")
    node = json.loads(subprocess.check_output(
        ["node", "-p", "JSON.stringify({platform:process.platform,arch:process.arch})"], text=True,
    ))
    if node != {"platform": sys.platform, "arch": target}:
        raise ValueError("Node.js architecture differs from native Python: " + json.dumps(node))
    binaries = {}
    for path in args.binary:
        actual = binary_architecture(path)
        if actual != target:
            raise ValueError(f"Expected {target} executable, got {actual}: {path}")
        binaries[str(path)] = actual
    print(json.dumps({"passed": True, "platform": host_platform, "arch": arch,
                      "python_platform": sysconfig.get_platform(), "binaries": binaries}))


if __name__ == "__main__":
    main()
