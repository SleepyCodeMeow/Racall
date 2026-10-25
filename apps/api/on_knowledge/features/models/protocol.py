"""Strict provider metadata and bounded Ollama download stream decoding."""

from __future__ import annotations

import json
from collections.abc import Callable

LINE_LIMIT = 32 * 1024
PULL_LIMIT = 8 * 1024 * 1024


def decode_json(value: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = item
        return result

    def invalid_constant(value):
        raise ValueError("Invalid JSON constant")

    result = json.loads(value.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("Expected an object")
    return result


def model_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 200
        or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ValueError("Invalid model ID")
    return value


def counter(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError("Invalid progress count")
    return value


def progress_update(item: dict) -> dict:
    """Validate an upstream event without mutating or persisting app job state."""
    if "error" in item:
        raise ValueError("Model download failed. Check Ollama and try again.")
    status = item.get("status")
    if not isinstance(status, str) or len(status) > 256:
        raise ValueError("Model download progress was invalid.")
    if status == "success":
        return {"status": "completed", "phase": "completed"}
    if status == "pulling manifest":
        phase = "manifest"
    elif status.startswith("pulling "):
        phase = "downloading"
    elif status.startswith("verifying "):
        phase = "verifying"
    elif status.startswith(("writing ", "removing ")):
        phase = "writing"
    else:
        raise ValueError("Model download progress was invalid.")
    try:
        completed, total = counter(item.get("completed", 0)), counter(item.get("total", 0))
        if completed > total:
            raise ValueError("Invalid progress")
    except ValueError:
        raise ValueError("Model download progress was invalid.") from None
    return {"phase": phase, "completed": completed, "total": total}


async def pull_model(
    client,
    url: str,
    headers: dict,
    model: str,
    progress: Callable[[dict], bool],
    *,
    line_limit: int,
    wire_limit: int,
):
    """Consume through explicit success; exiting always closes the HTTP stream."""
    async with client.stream("POST", url, headers=headers, json={"model": model, "stream": True}) as response:
        if response.status_code != 200:
            raise ValueError(f"Model provider returned HTTP {response.status_code}.")
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise ValueError("Model download progress was invalid.")
        buffer, count = bytearray(), 0
        async for chunk in response.aiter_raw():
            count += len(chunk)
            if count > wire_limit:
                raise ValueError("Model download progress was invalid.")
            buffer.extend(chunk)
            while b"\n" in buffer:
                line, _, remaining = buffer.partition(b"\n")
                buffer = bytearray(remaining)
                if len(line) > line_limit:
                    raise ValueError("Model download progress was invalid.")
                if line.strip() and progress(decode_json(line)):
                    return
            if len(buffer) > line_limit:
                raise ValueError("Model download progress was invalid.")
        if buffer.strip() and progress(decode_json(bytes(buffer))):
            return
        raise ValueError("Model download progress was invalid.")
