from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from ...ingestion import NormalizedDocument

PARSER_SECONDS = 60
PARSER_MEMORY_MB = 512
MAX_RESULT_BYTES = 64 * 1024 * 1024


def supervise(command: list[str], output: Path, seconds: float, memory_mb: int) -> dict:
    env = {**os.environ, "PYTHONUTF8": "1"}
    env.pop("OPENNOTEBOOK_SESSION_TOKEN", None)
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    deadline = time.monotonic() + seconds
    monitored = psutil.Process(process.pid)
    try:
        while process.poll() is None:
            if time.monotonic() >= deadline:
                raise ValueError("Document parsing exceeded the time limit.")
            try:
                if monitored.memory_info().rss > memory_mb * 1024 * 1024:
                    raise ValueError("Document parsing exceeded the memory limit.")
            except psutil.NoSuchProcess:
                break
            time.sleep(0.05)
        process.wait(timeout=2)
        if process.returncode != 0 or not output.exists():
            raise ValueError("The document parser stopped unexpectedly. Try a smaller or repaired file.")
        if output.stat().st_size > MAX_RESULT_BYTES:
            raise ValueError("The parsed document exceeds the output limit.")
        result = json.loads(output.read_text(encoding="utf-8"))
        if result.get("error"):
            raise ValueError(result["error"])
        return result
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def run_isolated(arguments: list[str], seconds: float, memory_mb: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="racall-parser-") as folder:
        output = Path(folder) / "result.json"
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.append(str(Path(__file__).resolve().parents[3] / "run.py"))
        command += [
            *arguments,
            "--parse-output",
            str(output),
            "--parent-pid",
            str(os.getpid()),
            "--parser-memory",
            str(memory_mb),
            "--parser-seconds",
            str(seconds),
        ]
        return supervise(command, output, seconds, memory_mb)


def parse_isolated(
    path: Path, seconds: float = PARSER_SECONDS, memory_mb: int = PARSER_MEMORY_MB
) -> NormalizedDocument:
    result = run_isolated(["--parse-document", str(path.resolve())], seconds, memory_mb)
    return NormalizedDocument.model_validate(result["document"])


def fetch_url_isolated(url: str) -> tuple[str, str]:
    result = run_isolated(["--parse-url", url], PARSER_SECONDS, PARSER_MEMORY_MB)
    return result["title"], result["text"]
