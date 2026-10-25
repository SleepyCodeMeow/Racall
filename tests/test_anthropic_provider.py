"""Claude protocol fixtures use HTTPX streams; no credentials or inference."""

import asyncio
import json
import time

import httpx
import pytest
from on_knowledge import anthropic_provider, completion_stream, providers
from on_knowledge.anthropic_provider import AnthropicProvider
from on_knowledge.completion_stream import CompletionDeadlineError, CompletionProtocolError

HTTPX_CLIENT = httpx.AsyncClient
URL = "https://api.anthropic.com/v1/messages"


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self):
        self.closed = True


def event(kind, **values):
    payload = json.dumps({"type": kind, **values}, ensure_ascii=False)
    return f"event: {kind}\ndata: {payload}\n\n".encode()


def start():
    return event(
        "message_start",
        message={
            "type": "message",
            "role": "assistant",
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
        },
    )


def block(text='{"claims": []}', *, index=0):
    return (
        event("content_block_start", index=index, content_block={"type": "text", "text": ""})
        + event("content_block_delta", index=index, delta={"type": "text_delta", "text": text})
        + event("content_block_stop", index=index)
    )


def finish(reason="end_turn"):
    return event(
        "message_delta", delta={"stop_reason": reason, "stop_sequence": None}, usage={"output_tokens": 5}
    ) + event("message_stop")


def completed(text='{"claims": []}'):
    return start() + block(text) + finish()


def transport(monkeypatch, stream, *, content_type="text/event-stream", status=200, headers=None):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            status, headers={"Content-Type": content_type, **(headers or {})}, stream=stream
        )

    def client(**kwargs):
        assert kwargs["trust_env"] is False
        assert kwargs["timeout"].read == 120
        assert kwargs["timeout"].connect == 15
        return HTTPX_CLIENT(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(completion_stream.httpx, "AsyncClient", client)
    return requests


def call(**kwargs):
    return completion_stream.complete_json(
        URL, {"x-api-key": "fixture"}, {"model": "fixture"}, protocol="anthropic", **kwargs
    )


def fixture_provider(monkeypatch, settings=None):
    monkeypatch.setattr(providers, "provider_key", lambda settings: "fixture-private-key", raising=False)
    return AnthropicProvider(settings or {"model": "fixture-model"})


def test_native_messages_request_has_system_header_version_and_bounded_output(monkeypatch):
    instance = fixture_provider(monkeypatch)
    requests = transport(monkeypatch, Chunks([completed()]))
    assert instance.complete("Return JSON only.", {"question": "Источник?"}) == {"claims": []}
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == URL
    assert request.headers["x-api-key"] == "fixture-private-key"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert "authorization" not in request.headers
    assert json.loads(request.content) == {
        "model": "fixture-model",
        "system": "Return JSON only.",
        "max_tokens": 4096,
        "stream": True,
        "messages": [{"role": "user", "content": '{"question": "Источник?"}'}],
    }


def test_custom_base_is_validated_and_has_exactly_one_messages_route(monkeypatch):
    instance = fixture_provider(monkeypatch, {"model": "fixture", "base_url": "http://localhost:1234/v1/"})
    requests = transport(monkeypatch, Chunks([completed()]))
    assert instance.complete("system", {}) == {"claims": []}
    assert str(requests[0].url) == "http://localhost:1234/v1/messages"
    with pytest.raises(ValueError):
        AnthropicProvider({"base_url": "http://untrusted.example/v1", "model": "fixture"})


def test_missing_model_or_key_never_begins_inference(monkeypatch):
    monkeypatch.setattr(providers, "provider_key", lambda settings: "", raising=False)
    monkeypatch.setattr(anthropic_provider, "complete_json", lambda *args, **kwargs: pytest.fail("Inference"))
    with pytest.raises(ValueError, match="имя модели"):
        AnthropicProvider({}).complete("system", {})
    with pytest.raises(ValueError, match="API-ключ"):
        AnthropicProvider({"model": "fixture"}).complete("system", {})


def test_thinking_signatures_redacted_blocks_and_metadata_never_become_answer(monkeypatch):
    thinking = (
        event(
            "content_block_start",
            index=0,
            content_block={"type": "thinking", "thinking": "", "signature": ""},
        )
        + event(
            "content_block_delta",
            index=0,
            delta={"type": "thinking_delta", "thinking": '{"claims":["UNTRUSTED"]}'},
        )
        + event("content_block_delta", index=0, delta={"type": "signature_delta", "signature": "opaque"})
        + event("content_block_stop", index=0)
        + event("content_block_start", index=1, content_block={"type": "redacted_thinking", "data": "opaque"})
        + event("content_block_stop", index=1)
    )
    expected = {"claims": [{"text": "Источник 🦝"}]}
    wire = (
        b": comment\r\n\r\n"
        + start()
        + event("ping")
        + thinking
        + event("future_metadata", value="ignored")
        + block(json.dumps(expected, ensure_ascii=False), index=2)
        + finish()
    ).replace(b"\n", b"\r\n")
    stream = Chunks([bytes([byte]) for byte in wire])
    transport(monkeypatch, stream)
    assert call() == expected
    assert stream.closed


@pytest.mark.parametrize(
    "wire",
    [
        block() + finish(),
        start() + start() + block() + finish(),
        start() + block() + event("message_stop"),
        start() + block() + finish().removesuffix(event("message_stop")),
        start() + block() + finish().rstrip(),
        start() + block() + finish("max_tokens"),
        start() + block() + finish("tool_use"),
        start() + block() + finish("refusal"),
        start() + block() + finish("pause_turn"),
        start() + block() + finish("stop_sequence"),
        start() + event("content_block_start", index=0, content_block={"type": "tool_use", "input": {}}),
        start()
        + event("content_block_start", index=0, content_block={"type": "server_tool_use", "input": {}}),
        start() + event("content_block_start", index=0, content_block={"type": "refusal", "refusal": "no"}),
        start()
        + event("content_block_start", index=0, content_block={"type": "text", "text": "{}"})
        + finish(),
        start() + block(index=1) + finish(),
        start() + event("content_block_start", index=True, content_block={"type": "text", "text": "{}"}),
        start() + event("content_block_delta", index=0, delta={"type": "text_delta", "text": "{}"}),
        start() + event("content_block_stop", index=0),
        start()
        + event("content_block_start", index=0, content_block={"type": "text", "text": ""})
        + event("content_block_delta", index=1, delta={"type": "text_delta", "text": "{}"}),
        start()
        + event(
            "content_block_start",
            index=0,
            content_block={"type": "thinking", "thinking": "", "signature": ""},
        )
        + event("content_block_delta", index=0, delta={"type": "text_delta", "text": "{}"}),
        start()
        + event("content_block_start", index=0, content_block={"type": "text", "text": ""})
        + event("content_block_delta", index=0, delta={"type": "input_json_delta", "partial_json": "{}"}),
        start()
        + block()
        + event("message_delta", delta={"stop_reason": "end_turn"})
        + block(index=1)
        + finish(),
        start() + block() + event("error", error={"message": "untrusted private detail"}),
        completed('{"claims":[],"claims":["replacement"]}'),
        completed('{"number": NaN}'),
        completed('{"text": "\\ud800"}'),
        completed('{"\\ud800": "invalid key"}'),
        completed('{"nested": [1e309]}'),
        completed('["not an object"]'),
        completed('{"claims":'),
        completed('```json\n{"claims":[]}\n```'),
        b"data: not-json\n\n",
        b"data: \xff\n\n",
        start() + b'event: error\ndata: {"type": "ping"}\n\n' + block() + finish(),
        start() + event("message_stop"),
    ],
    ids=[f"invalid-{index}" for index in range(35)],
)
def test_malformed_interrupted_or_unsafe_stream_does_not_return_partial_json(monkeypatch, wire):
    stream = Chunks([wire])
    requests = transport(monkeypatch, stream)
    with pytest.raises(CompletionProtocolError) as caught:
        call()
    assert "private" not in str(caught.value)
    assert len(requests) == 1 and stream.closed


def full(blocks=None, reason="end_turn"):
    return {
        "type": "message",
        "role": "assistant",
        "stop_reason": reason,
        "stop_sequence": None,
        "content": blocks if blocks is not None else [{"type": "text", "text": '{"claims":[]}'}],
    }


def test_json_fallback_extracts_only_text_from_complete_message(monkeypatch):
    body = full(
        [
            {"type": "thinking", "thinking": '{"bad":true}', "signature": "opaque"},
            {"type": "text", "text": '{"claims":'},
            {"type": "text", "text": "[]}"},
            {"type": "redacted_thinking", "data": "opaque"},
        ]
    )
    transport(monkeypatch, Chunks([json.dumps(body).encode()]), content_type="application/json")
    assert call() == {"claims": []}


@pytest.mark.parametrize(
    "body",
    [
        full(reason="max_tokens"),
        full(reason=None),
        full(reason="refusal"),
        full(reason="tool_use"),
        full([]),
        full([{"type": "tool_use", "input": {}}]),
        full([{"type": "text", "text": None}]),
        full([{"type": "thinking", "thinking": '{"claims":[]}', "signature": "opaque"}]),
        {"type": "error", "error": {"message": "untrusted"}},
        {**full(), "role": "user"},
        {**full(), "stop_sequence": "unrequested"},
    ],
)
def test_json_fallback_rejects_incomplete_message_or_non_text_answer(monkeypatch, body):
    transport(monkeypatch, Chunks([json.dumps(body).encode()]), content_type="application/json")
    with pytest.raises(CompletionProtocolError):
        call()


@pytest.mark.parametrize(
    "wire",
    [
        b":" + b"x" * (64 * 1024) + b"\n\n",
        b"data: " + b"x" * 40_000 + b"\ndata: " + b"y" * 40_000 + b"\n\n",
        b": heartbeat\n\n" * 90_000,
        start() + b"".join(block("x" * 8192, index=i) for i in range(33)) + finish(),
    ],
    ids=["line", "event", "wire", "text"],
)
def test_response_limits_apply_to_anthropic_protocol(monkeypatch, wire):
    transport(monkeypatch, Chunks([wire]))
    with pytest.raises(CompletionProtocolError):
        call()


@pytest.mark.parametrize(
    "content_type,headers", [("text/html", {}), ("text/event-stream", {"Content-Encoding": "gzip"})]
)
def test_unexpected_response_type_or_compression_is_rejected(monkeypatch, content_type, headers):
    transport(monkeypatch, Chunks([completed()]), content_type=content_type, headers=headers)
    with pytest.raises(CompletionProtocolError):
        call()


def test_total_deadline_stops_pings_and_closes_stream(monkeypatch):
    class SlowStream(Chunks):
        async def __aiter__(self):
            while True:
                await asyncio.sleep(0.002)
                yield event("ping")

    stream = SlowStream([])
    requests = transport(monkeypatch, stream)
    started = time.monotonic()
    with pytest.raises(CompletionDeadlineError):
        call(deadline_seconds=0.03)
    assert time.monotonic() - started < 1
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize(
    "error,expected",
    [
        (CompletionDeadlineError("private detail"), "общее время"),
        (httpx.ReadTimeout("private detail"), "передавать данные"),
        (CompletionProtocolError("private detail"), "поток ответа"),
        (httpx.ConnectError("private detail"), "связаться"),
    ],
)
def test_public_errors_are_sanitized_and_not_retried(monkeypatch, error, expected):
    instance = fixture_provider(monkeypatch)
    calls = []

    def complete(*args, **kwargs):
        calls.append(args)
        raise error

    monkeypatch.setattr(anthropic_provider, "complete_json", complete)
    with pytest.raises(ValueError, match=expected) as caught:
        instance.complete("system", {})
    assert "private" not in str(caught.value) and len(calls) == 1


def test_http_status_is_safe_without_response_body_and_not_retried(monkeypatch):
    instance = fixture_provider(monkeypatch)
    stream = Chunks([b"private diagnostic"])
    requests = transport(monkeypatch, stream, status=429)
    with pytest.raises(ValueError, match="HTTP 429") as caught:
        instance.complete("system", {})
    assert "private" not in str(caught.value) and len(requests) == 1


@pytest.mark.asyncio
async def test_sync_provider_contract_inside_active_event_loop(monkeypatch):
    transport(monkeypatch, Chunks([completed()]))
    assert call() == {"claims": []}
