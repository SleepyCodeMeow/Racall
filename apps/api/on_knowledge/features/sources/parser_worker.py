"""One-shot parser process. The supervisor owns deadlines and memory monitoring."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import psutil

from ...ingestion import fetch_url, parse


def run_worker(
    source: Path | None, output: Path, parent: int, memory_mb: int, seconds: float, url: str | None = None
):
    # Also bound a worker orphaned by a crashed/killed desktop service.
    def watchdog():
        deadline = time.monotonic() + seconds + 5
        while time.monotonic() < deadline and psutil.pid_exists(parent):
            time.sleep(0.5)
        os._exit(70)

    threading.Thread(target=watchdog, daemon=True).start()
    if sys.platform == "linux":
        import resource

        # RSS is supervised on every OS. Linux additionally bounds address space.
        limit = memory_mb * 2 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    try:
        if url:
            title, text = fetch_url(url)
            result = {"title": title, "text": text}
        else:
            result = {"document": parse(source).model_dump()}
    except MemoryError:
        result = {"error": "Document parsing exceeded the memory limit."}
    except ValueError as error:
        result = {"error": str(error)[:500]}
    except Exception:
        result = {"error": "This document could not be parsed. Check the file or try another format."}
    output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
