"""Transport regressions use in-process HTTPX streams, never a real AI endpoint."""

import asyncio
import json
import time

import httpx
import pytest
from on_knowledge import completion_stream

URL = "http://127.0.0.1:11434/v1/chat/completions"
HEADERS = {"Authorization": "Bearer test-provider-key"}
PAYLOAD = {"model": "fixture", "messages": [{"role": "user", "content": "Question"}]}
HTTPX_CLIENT = httpx.AsyncClient


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self):
        self.closed = True


def event(delta=None, *, finish=None, index=0):
    return ("data: " + json.dumps({"choices": [{"index": index, "delta": delta or {},
                                              "finish_reason": finish}]}, ensure_ascii=False) + "\n\n").encode()


def completed(text='{"claims": []}'):
    return event({"content": text}) + event(finish="stop") + b"data: [DONE]\n\n"


def transport(monkeypatch, stream, *, content_type="text/event-stream", status=200, headers=None):
    requests = []

    async def handler(request):
        requests.append(request)
        response_headers = {"Content-Type": content_type, **(headers or {})}
        return httpx.Response(status, headers=response_headers, stream=stream)

    def client(**kwargs):
        assert kwargs["trust_env"] is False
        assert kwargs["timeout"].read == 120
        assert kwargs["timeout"].connect == 15
        return HTTPX_CLIENT(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(completion_stream.httpx, "AsyncClient", client)
    return requests


def call(**kwargs):
    return completion_stream.complete_json(URL, HEADERS, PAYLOAD, **kwargs)


def test_stream_assembles_utf8_content_without_changing_payload_or_reasoning(monkeypatch):
    expected = {"claims": [{"text": "Источник 🦝", "evidence_ids": ["E2"]}]}
    wire = (b": keepalive\r\n\r\n" + event({"role": "assistant", "content": None})
            + event({"reasoning_content": '{"claims": [{"text": "UNTRUSTED THOUGHT"}]}'})
            + event({"reasoning": '{"claims": [{"text": "UNTRUSTED THOUGHT"}]}'})
            + completed(json.dumps(expected, ensure_ascii=False))
            ).replace(b"\n", b"\r\n")
    stream = Chunks([bytes([byte]) for byte in wire])
    requests = transport(monkeypatch, stream)

    assert call() == expected
    assert stream.closed
    assert len(requests) == 1
    sent = json.loads(requests[0].content)
    assert sent == {**PAYLOAD, "stream": True}
    assert "stream" not in PAYLOAD
    assert "think" not in sent and "reasoning_effort" not in sent
    assert requests[0].headers["authorization"] == HEADERS["Authorization"]


def test_multiline_sse_fields_and_usage_are_not_content(monkeypatch):
    wire = (b"event: message\nid: arbitrary\nretry: 1000\n"
            b'data: {"choices": [\n'
            b'data: {"index": 0, "delta": {"content": "{\\"claims\\": []}"}, "finish_reason": null}]}\n\n'
            + event(finish="stop")
            + b'data: {"choices": [], "usage": {"completion_tokens": 4}}\n\n'
            + b"data: [DONE]\n\n")
    transport(monkeypatch, Chunks([wire]))
    assert call() == {"claims": []}


@pytest.mark.parametrize("refusal", ["Provider refused the request.", "", False, {}])
@pytest.mark.parametrize("streaming", [True, False], ids=["sse", "json"])
def test_explicit_refusal_never_accepts_otherwise_valid_json(monkeypatch, refusal, streaming):
    message = {"content": '{"claims": []}', "refusal": refusal}
    wire = (event(message) + event(finish="stop") + b"data: [DONE]\n\n" if streaming else
            json.dumps({"choices": [{"message": message, "finish_reason": "stop"}]}).encode())
    stream = Chunks([wire])
    requests = transport(monkeypatch, stream,
                         content_type="text/event-stream" if streaming else "application/json")
    with pytest.raises(completion_stream.CompletionProtocolError, match="refusal"):
        call()
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize("streaming", [True, False], ids=["sse", "json"])
def test_null_refusal_metadata_allows_normally_completed_json(monkeypatch, streaming):
    message = {"content": '{"claims": []}', "refusal": None}
    wire = (event(message) + event(finish="stop") + b"data: [DONE]\n\n" if streaming else
            json.dumps({"choices": [{"message": message, "finish_reason": "stop"}]}).encode())
    transport(monkeypatch, Chunks([wire]),
              content_type="text/event-stream" if streaming else "application/json")
    assert call() == {"claims": []}


@pytest.mark.parametrize("wire", [
    event({"content": '{"claims": []}'}) + b"data: [DONE]\n\n",
    event({"content": '{"claims": []}'}) + event(finish="stop"),
    completed().replace(b"[DONE]\n\n", b"[DONE]"),
    event({"content": '{"claims": []}'}) + event(finish="length") + b"data: [DONE]\n\n",
    event({"content": '{"claims": []}'}) + event(finish="content_filter") + b"data: [DONE]\n\n",
    event({"tool_calls": [{"function": {"name": "execute"}}]}) + event(finish="tool_calls"),
    event({"function_call": {"name": "execute"}}),
    event({"content": '{"claims": []}'}, index=1) + event(finish="stop"),
    b'data: {"choices": [{"index": 0, "delta": {}}, {"index": 1, "delta": {}}]}\n\n',
    b"data: not-json\n\n",
    b"data: \xff\n\n",
    b'data: {"choices": [{"index": 0, "delta": {"content": "\\ud800"}}]}\n\n',
    event({"content": ["not a string"]}),
    completed('["not an object"]'),
    completed('{"claims":'),
    completed('{"claims": [], "claims": [{"text": "replacement"}]}'),
    completed('{"value": NaN}'),
    b'data: {"error": {"message": "untrusted secret detail"}}\n\n',
    event(finish="stop") + b"data: [DONE]\n\n",
    event({"reasoning_content": '{"claims": []}'}) + event(finish="stop") + b"data: [DONE]\n\n",
    event({"content": '{"claims": []}'}) + event(finish="stop") + event({"content": " "}),
])
def test_incomplete_unsafe_or_malformed_stream_never_returns_partial_json(monkeypatch, wire):
    requests = transport(monkeypatch, Chunks([wire]))
    with pytest.raises(completion_stream.CompletionProtocolError) as error:
        call()
    assert "untrusted secret detail" not in str(error.value)
    assert len(requests) == 1


def test_limits_comment_line_even_when_no_generated_content(monkeypatch):
    transport(monkeypatch, Chunks([b":" + b"x" * (64 * 1024) + b"\n\n" + completed()]))
    with pytest.raises(completion_stream.CompletionProtocolError):
        call()


def test_limits_wire_bytes_even_for_heartbeats(monkeypatch):
    transport(monkeypatch, Chunks([b": heartbeat\n\n" * 90_000, completed()]))
    with pytest.raises(completion_stream.CompletionProtocolError):
        call()


def test_limits_content_across_small_events(monkeypatch):
    wire = b"".join(event({"content": "x" * 8192}) for _ in range(33)) + event(finish="stop")
    transport(monkeypatch, Chunks([wire]))
    with pytest.raises(completion_stream.CompletionProtocolError):
        call()


def test_limits_aggregate_multiline_event(monkeypatch):
    wire = b"data: " + b"x" * 40_000 + b"\ndata: " + b"y" * 40_000 + b"\n\n"
    transport(monkeypatch, Chunks([wire]))
    with pytest.raises(completion_stream.CompletionProtocolError):
        call()


@pytest.mark.parametrize("finish", ["missing", "stop"])
def test_full_json_compatibility_when_server_ignores_stream(monkeypatch, finish):
    choice = {"message": {"content": '{"supported_claim_ids": ["C1"]}'}}
    if finish != "missing":
        choice["finish_reason"] = finish
    stream = Chunks([json.dumps({"choices": [choice]}).encode()])
    requests = transport(monkeypatch, stream, content_type="application/json; charset=utf-8")
    assert call() == {"supported_claim_ids": ["C1"]}
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize("choice", [
    {"finish_reason": "length", "message": {"content": '{"claims": []}'}},
    {"finish_reason": None, "message": {"content": '{"claims": []}'}},
    {"index": 1, "message": {"content": '{"claims": []}'}},
    {"message": {"tool_calls": [{"function": {"name": "execute"}}], "content": '{"claims": []}'}},
    {"message": {"content": "[]"}},
    {"message": {"content": None}},
])
def test_full_json_fallback_still_rejects_incomplete_or_wrong_shape(monkeypatch, choice):
    transport(monkeypatch, Chunks([json.dumps({"choices": [choice]}).encode()]),
              content_type="application/json")
    with pytest.raises(completion_stream.CompletionProtocolError):
        call()


def test_full_json_fallback_has_wire_and_content_limits(monkeypatch):
    content = json.dumps({"claims": [], "message": "x" * (256 * 1024)})
    body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
    transport(monkeypatch, Chunks([body]), content_type="application/json")
    with pytest.raises(completion_stream.CompletionProtocolError):
        call()


def test_unsupported_content_type_or_encoding_rejected(monkeypatch):
    for content_type, headers in [("text/html", {}), ("text/event-stream", {"Content-Encoding": "gzip"})]:
        transport(monkeypatch, Chunks([completed()]), content_type=content_type, headers=headers)
        with pytest.raises(completion_stream.CompletionProtocolError):
            call()


def test_provider_http_error_propagates_without_retry(monkeypatch):
    requests = transport(monkeypatch, Chunks([b"untrusted provider detail"]), status=401)
    with pytest.raises(httpx.HTTPStatusError):
        call()
    assert len(requests) == 1


def test_idle_timeout_propagates_without_retry(monkeypatch):
    class IdleStream(Chunks):
        async def __aiter__(self):
            raise httpx.ReadTimeout("fixture idle timeout")
            yield b""  # Mark this as an async generator.

    stream = IdleStream([])
    requests = transport(monkeypatch, stream)
    with pytest.raises(httpx.ReadTimeout):
        call()
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize("heartbeats", [False, True])
def test_total_deadline_stops_blocked_read_or_endless_heartbeats(monkeypatch, heartbeats):
    class SlowStream(Chunks):
        async def __aiter__(self):
            if not heartbeats:
                await asyncio.Event().wait()
            while True:
                await asyncio.sleep(.002)
                yield b": progress\n\n"

    stream = SlowStream([])
    requests = transport(monkeypatch, stream)
    started = time.monotonic()
    with pytest.raises(completion_stream.CompletionDeadlineError):
        call(deadline_seconds=.03)
    assert time.monotonic() - started < 1
    assert len(requests) == 1 and stream.closed


@pytest.mark.asyncio
async def test_sync_contract_works_inside_an_already_running_event_loop(monkeypatch):
    transport(monkeypatch, Chunks([completed()]))
    assert call() == {"claims": []}


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan"), True])
def test_invalid_deadline_does_not_begin_a_request(value):
    with pytest.raises(ValueError):
        call(deadline_seconds=value)
