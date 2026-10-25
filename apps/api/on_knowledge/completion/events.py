"""Incremental SSE framing and wire-size limits, before protocol interpretation."""

from __future__ import annotations

from typing import Iterator

import httpx

from .payloads import CompletionProtocolError

WIRE_LIMIT = 1024 * 1024
LINE_LIMIT = 64 * 1024
EVENT_LIMIT = 64 * 1024


class EventDecoder:
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
                if len(self.line) > LINE_LIMIT:
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
                if self.data_size > EVENT_LIMIT:
                    raise CompletionProtocolError("The provider event is too large.")
                self.data.append(value)
            elif field == "event":
                self.event_name = value.removeprefix(" ") if separator else ""


async def response_chunks(response: httpx.Response):
    size = 0
    async for chunk in response.aiter_raw():
        size += len(chunk)
        if size > WIRE_LIMIT:
            raise CompletionProtocolError("The provider response is too large.")
        yield chunk
