"""Messages API completion state machine; only completed text becomes JSON.

Thinking and signatures keep the connection active but are never answer text.
Tools, refusals, token limits and incomplete messages fail closed.
"""

from __future__ import annotations

import httpx

from .completion_stream import (
    _CONTENT_LIMIT,
    CompletionProtocolError,
    _chunks,
    _content,
    _Events,
    _json_object,
    _utf8_size,
)


def _invalid() -> CompletionProtocolError:
    return CompletionProtocolError("The provider did not finish a valid Messages completion.")


def _message(message: object, *, streaming: bool):
    if not isinstance(message, dict) or message.get("type") != "message" \
            or message.get("role") != "assistant" or "error" in message:
        raise _invalid()
    if message.get("stop_reason") != (None if streaming else "end_turn") \
            or message.get("stop_sequence") is not None:
        raise _invalid()


class _Text:
    def __init__(self):
        self.parts: list[str] = []
        self.size = 0

    def append(self, value: object):
        if not isinstance(value, str):
            raise _invalid()
        self.size += _utf8_size(value)
        if self.size > _CONTENT_LIMIT:
            raise CompletionProtocolError("The completion content is too large.")
        self.parts.append(value)

    def result(self) -> dict:
        return _content("".join(self.parts))


def _block(block: object, text: _Text) -> str:
    if not isinstance(block, dict):
        raise _invalid()
    kind = block.get("type")
    if kind == "text":
        text.append(block.get("text"))
    elif kind == "thinking":
        if not isinstance(block.get("thinking"), str) or not isinstance(block.get("signature"), str):
            raise _invalid()
    elif kind == "redacted_thinking":
        if not isinstance(block.get("data"), str):
            raise _invalid()
    else:
        # In particular, tool_use/server_tool_use/refusal cannot become text.
        raise _invalid()
    return kind


def full_response(payload: dict) -> dict:
    _message(payload, streaming=False)
    blocks = payload.get("content")
    if not isinstance(blocks, list) or not blocks:
        raise _invalid()
    text = _Text()
    for block in blocks:
        _block(block, text)
    return text.result()


async def stream_response(response: httpx.Response) -> dict:
    parser = _Events()
    text = _Text()
    started = finished = False
    next_index = 0
    active_index = None
    active_kind = None
    async for chunk in _chunks(response):
        for event_name, event in parser.feed_named(chunk):
            payload = _json_object(event)
            event_type = payload.get("type")
            if "error" in payload or not isinstance(event_type, str) or event_type == "error" \
                    or event_name != event_type:
                raise _invalid()
            if event_type == "ping":
                continue
            if event_type == "message_start":
                if started or finished:
                    raise _invalid()
                message = payload.get("message")
                _message(message, streaming=True)
                if message.get("content") != []:
                    raise _invalid()
                started = True
            elif event_type == "content_block_start":
                index = payload.get("index")
                if not started or finished or active_index is not None \
                        or type(index) is not int or index != next_index:
                    raise _invalid()
                active_kind = _block(payload.get("content_block"), text)
                active_index = index
            elif event_type == "content_block_delta":
                index = payload.get("index")
                delta = payload.get("delta")
                if active_index is None or type(index) is not int or index != active_index \
                        or not isinstance(delta, dict):
                    raise _invalid()
                kind = delta.get("type")
                if active_kind == "text" and kind == "text_delta":
                    text.append(delta.get("text"))
                elif active_kind == "thinking" and kind in ("thinking_delta", "signature_delta"):
                    value = delta.get("thinking" if kind == "thinking_delta" else "signature")
                    if not isinstance(value, str):
                        raise _invalid()
                else:
                    raise _invalid()
            elif event_type == "content_block_stop":
                index = payload.get("index")
                if active_index is None or type(index) is not int or index != active_index:
                    raise _invalid()
                active_index = active_kind = None
                next_index += 1
            elif event_type == "message_delta":
                delta = payload.get("delta")
                if not started or finished or active_index is not None or not isinstance(delta, dict):
                    raise _invalid()
                reason = delta.get("stop_reason")
                if reason is not None:
                    if reason != "end_turn" or delta.get("stop_sequence") is not None:
                        raise _invalid()
                    finished = True
            elif event_type == "message_stop":
                if not started or not finished or active_index is not None:
                    raise _invalid()
                return text.result()
            else:
                # New metadata events are permitted by Anthropic's versioning
                # policy. They cannot contribute answer content or close blocks.
                continue
    raise CompletionProtocolError("The provider stream ended before message_stop.")
