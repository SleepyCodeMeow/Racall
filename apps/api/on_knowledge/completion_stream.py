"""Bounded OpenAI-compatible completions; partial output never becomes an answer.

Streaming keeps an active local model from appearing idle while it thinks. The
idle timeout and independent wall-clock deadline remain separate safeguards.
"""

from __future__ import annotations

import asyncio
import json
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator

import httpx

_WIRE_LIMIT = 1024 * 1024
_CONTENT_LIMIT = 256 * 1024
_LINE_LIMIT = 64 * 1024
_EVENT_LIMIT = 64 * 1024


class CompletionProtocolError(ValueError):
    """The provider did not deliver one complete bounded JSON object."""


class CompletionDeadlineError(TimeoutError):
    """The entire request exceeded its deadline, even if bytes kept arriving."""


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CompletionProtocolError("The completion contains duplicate JSON keys.")
        result[key] = value
    return result


def _invalid_constant(value: str):
    raise CompletionProtocolError("The completion contains a non-JSON number.")


def _json_object(value: str | bytes) -> dict:
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
            _utf8_size(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise CompletionProtocolError("The completion contains a non-JSON number.")
    return result


def _content(value: object) -> dict:
    if not isinstance(value, str) or _utf8_size(value) > _CONTENT_LIMIT:
        raise CompletionProtocolError("The completion content is invalid or too large.")
    return _json_object(value)


def _utf8_size(value: str) -> int:
    try:
        return len(value.encode("utf-8", errors="strict"))
    except UnicodeError as error:
        raise CompletionProtocolError("The completion contains invalid Unicode.") from error


def _no_tools_or_refusal(message: dict):
    if any(message.get(key) is not None for key in ("tool_calls", "function_call")):
        raise CompletionProtocolError("Tool calls cannot be used as a JSON completion.")
    if message.get("refusal") is not None:
        raise CompletionProtocolError("A refusal cannot be used as a JSON completion.")


class _Events:
    """Incremental SSE framing, bounded before decoding any complete line."""

    def __init__(self):
        self.line = bytearray()
        self.data: list[str] = []
        self.data_size = 0
        self.event_name = ""
        self.skip_lf = False
        self.first_line = True

    def feed(self, chunk: bytes) -> Iterator[str]:
        for _, data in self.feed_named(chunk):
            yield data

    def feed_named(self, chunk: bytes) -> Iterator[tuple[str, str]]:
        for byte in chunk:
            if self.skip_lf:
                self.skip_lf = False
                if byte == 10:
                    continue
            if byte not in (10, 13):
                self.line.append(byte)
                if len(self.line) > _LINE_LIMIT:
                    raise CompletionProtocolError("The provider event line is too large.")
                continue
            self.skip_lf = byte == 13
            try:
                text = self.line.decode("utf-8", errors="strict")
            except UnicodeError as error:
                raise CompletionProtocolError("The provider event is not valid UTF-8.") from error
            self.line.clear()
            if self.first_line:
                text = text.removeprefix("\ufeff")
                self.first_line = False
            if not text:
                event_name = self.event_name or "message"
                self.event_name = ""
                if self.data:
                    result = "\n".join(self.data)
                    self.data.clear()
                    self.data_size = 0
                    yield event_name, result
                continue
            if text.startswith(":"):
                continue
            field, separator, value = text.partition(":")
            if field == "data":
                value = value.removeprefix(" ") if separator else ""
                self.data_size += len(value.encode("utf-8")) + 1
                if self.data_size > _EVENT_LIMIT:
                    raise CompletionProtocolError("The provider event is too large.")
                self.data.append(value)
            elif field == "event":
                self.event_name = value.removeprefix(" ") if separator else ""


async def _chunks(response: httpx.Response):
    size = 0
    async for chunk in response.aiter_raw():
        size += len(chunk)
        if size > _WIRE_LIMIT:
            raise CompletionProtocolError("The provider response is too large.")
        yield chunk


def _full_response(response: dict) -> dict:
    choices = response.get("choices")
    if "error" in response or not isinstance(choices, list) or len(choices) != 1:
        raise CompletionProtocolError("The provider did not return exactly one completion.")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise CompletionProtocolError("The provider completion choice is invalid.")
    if "index" in choice and (type(choice["index"]) is not int or choice["index"] != 0):
        raise CompletionProtocolError("The provider returned an unexpected choice index.")
    # Some compatible servers ignore stream and omit finish_reason entirely.
    # An explicitly reported interruption must never be accepted.
    if "finish_reason" in choice and choice["finish_reason"] != "stop":
        raise CompletionProtocolError("The provider did not finish the completion normally.")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise CompletionProtocolError("The provider completion message is invalid.")
    _no_tools_or_refusal(message)
    return _content(message.get("content"))


async def _stream_response(response: httpx.Response) -> dict:
    parser = _Events()
    content: list[str] = []
    content_size = 0
    finished = False
    async for chunk in _chunks(response):
        for event in parser.feed(chunk):
            if event == "[DONE]":
                if not finished:
                    raise CompletionProtocolError("The provider ended before finishing the completion.")
                return _content("".join(content))
            payload = _json_object(event)
            choices = payload.get("choices")
            if "error" in payload or not isinstance(choices, list):
                raise CompletionProtocolError("The provider event has no valid completion choice.")
            if not choices and "usage" in payload:
                continue
            if len(choices) != 1 or not isinstance(choices[0], dict):
                raise CompletionProtocolError("The provider event must contain exactly one choice.")
            choice = choices[0]
            if type(choice.get("index")) is not int or choice["index"] != 0:
                raise CompletionProtocolError("The provider returned an unexpected choice index.")
            if finished:
                raise CompletionProtocolError("The provider sent content after the completed choice.")
            delta = choice.get("delta")
            if not isinstance(delta, dict):
                raise CompletionProtocolError("The provider event delta is invalid.")
            _no_tools_or_refusal(delta)
            value = delta.get("content")
            if value is not None:
                if not isinstance(value, str):
                    raise CompletionProtocolError("The provider content delta is invalid.")
                content_size += _utf8_size(value)
                if content_size > _CONTENT_LIMIT:
                    raise CompletionProtocolError("The completion content is too large.")
                content.append(value)
            # Reasoning, role and other metadata are deliberately not answer text.
            reason = choice.get("finish_reason")
            if reason is not None:
                if reason != "stop":
                    raise CompletionProtocolError("The provider did not finish the completion normally.")
                finished = True
    raise CompletionProtocolError("The provider stream ended before its completion marker.")


async def _complete_json(url: str, headers: dict, payload: dict,
                         deadline_seconds: float, idle_seconds: float, protocol: str) -> dict:
    # Both APIs share request limits and framing; their completion state machines
    # remain separate so one protocol cannot accidentally accept the other.
    if protocol == "anthropic":
        from .anthropic_stream import full_response, stream_response
    else:
        full_response, stream_response = _full_response, _stream_response
    try:
        async with asyncio.timeout(deadline_seconds):
            async with httpx.AsyncClient(timeout=httpx.Timeout(idle_seconds, connect=15),
                                         trust_env=False) as client:
                request_headers = {"Accept-Encoding": "identity", **headers}
                async with client.stream("POST", url, headers=request_headers,
                                         json={**payload, "stream": True}) as response:
                    response.raise_for_status()
                    encoding = response.headers.get("content-encoding", "identity").lower().strip()
                    if encoding not in ("", "identity"):
                        raise CompletionProtocolError("The provider ignored the uncompressed response request.")
                    media_type = response.headers.get("content-type", "").partition(";")[0].lower().strip()
                    if media_type == "text/event-stream":
                        return await stream_response(response)
                    if media_type == "application/json":
                        body = bytearray()
                        async for chunk in _chunks(response):
                            body.extend(chunk)
                        return full_response(_json_object(bytes(body)))
                    raise CompletionProtocolError("The provider response type is unsupported.")
    except TimeoutError as error:
        raise CompletionDeadlineError("The completion exceeded its total deadline.") from error


def complete_json(url: str, headers: dict, payload: dict, *,
                  deadline_seconds: float = 300, idle_seconds: float = 120,
                  protocol: str = "openai") -> dict:
    """Return only one fully completed JSON object, without inference retries.

The public provider contract is synchronous, including calls made by an async
MCP tool. In that case the HTTP request gets its own loop in an isolated thread.
"""
    for value in (deadline_seconds, idle_seconds):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("Completion timeouts must be finite positive seconds.")
    if protocol not in ("openai", "anthropic"):
        raise ValueError("The completion protocol is unsupported.")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_complete_json(url, headers, payload, deadline_seconds, idle_seconds, protocol))
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="completion") as executor:
        return executor.submit(
            asyncio.run, _complete_json(url, headers, payload, deadline_seconds, idle_seconds, protocol)
        ).result()
