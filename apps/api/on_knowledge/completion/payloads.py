"""Strict bounded JSON and Unicode validation shared by completion protocols."""

from __future__ import annotations

import json
import math

CONTENT_LIMIT = 256 * 1024


class CompletionProtocolError(ValueError):
    """The provider did not deliver one complete bounded JSON object."""


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CompletionProtocolError("The completion contains duplicate JSON keys.")
        result[key] = value
    return result


def _invalid_constant(value: str):
    raise CompletionProtocolError("The completion contains a non-JSON number.")


def json_object(value: str | bytes) -> dict:
    try:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="strict")
        result = json.loads(value, object_pairs_hook=_object, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise CompletionProtocolError("The provider did not return valid JSON.") from error
    if not isinstance(result, dict):
        raise CompletionProtocolError("The completion must be a JSON object.")
    # JSON escape sequences are decoded after the wire's UTF-8 check. Validate
    # those strings too, along with overflowed numeric literals such as 1e309.
    pending: list[object] = [result]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str):
            utf8_size(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise CompletionProtocolError("The completion contains a non-JSON number.")
    return result


def content_object(value: object) -> dict:
    if not isinstance(value, str) or utf8_size(value) > CONTENT_LIMIT:
        raise CompletionProtocolError("The completion content is invalid or too large.")
    return json_object(value)


def utf8_size(value: str) -> int:
    try:
        return len(value.encode("utf-8", errors="strict"))
    except UnicodeError as error:
        raise CompletionProtocolError("The completion contains invalid Unicode.") from error
