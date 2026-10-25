"""Native package labels must match executable headers, including the Python sidecar."""

import runpy
import struct
from pathlib import Path

import pytest

helpers = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/check_native_arch.py"))


@pytest.mark.parametrize(
    "format,arch,machine",
    [
        ("pe", "x64", 0x8664),
        ("pe", "arm64", 0xAA64),
        ("elf", "x64", 62),
        ("elf", "arm64", 183),
        ("macho", "x64", 0x01000007),
        ("macho", "arm64", 0x0100000C),
    ],
)
def test_native_headers_distinguish_x64_and_arm64(tmp_path, format, arch, machine):
    header = bytearray(128)
    if format == "pe":
        header[:2] = b"MZ"
        struct.pack_into("<I", header, 60, 64)
        header[64:68] = b"PE\0\0"
        struct.pack_into("<H", header, 68, machine)
    elif format == "elf":
        header[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", header, 18, machine)
    else:
        header[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", header, 4, machine)
    binary = tmp_path / "sidecar"
    binary.write_bytes(header)
    assert helpers["binary_architecture"](binary) == arch


@pytest.mark.parametrize("header", [b"", b"MZ", b"#!/bin/sh\n", b"\x7fELF\x01\x01" + b"\0" * 20])
def test_invalid_or_32bit_executables_cannot_pass_as_native_64bit(tmp_path, header):
    binary = tmp_path / "sidecar"
    binary.write_bytes(header)
    with pytest.raises(ValueError):
        helpers["binary_architecture"](binary)


def test_windows_python_arch_uses_interpreter_platform_not_host_emulation(monkeypatch):
    monkeypatch.setattr(helpers["sys"], "platform", "win32")
    monkeypatch.setattr(helpers["sysconfig"], "get_platform", lambda: "win-amd64")
    monkeypatch.setattr(helpers["platform"], "machine", lambda: "ARM64")
    assert helpers["python_architecture"]() == "x64"
