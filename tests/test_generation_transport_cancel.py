"""Cancellation uses synthetic HTTP streams; no model or network is required."""

import asyncio
import threading

import httpx
import pytest
from on_knowledge import completion_stream

CLIENT = httpx.AsyncClient
URL = "http://127.0.0.1:11434/v1/chat/completions"


class Cancelled(Exception):
    pass


def test_already_cancelled_generation_never_opens_a_client(monkeypatch):
    def checkpoint():
        raise Cancelled()

    def unexpected(**kwargs):
        pytest.fail("Cancelled generation attempted provider I/O")

    monkeypatch.setattr(completion_stream.httpx, "AsyncClient", unexpected)
    with completion_stream.cancellable_completion(checkpoint), pytest.raises(Cancelled):
        completion_stream.complete_json(URL, {}, {})


@pytest.mark.parametrize("waiting_for_headers", [False, True])
@pytest.mark.parametrize("async_caller", [False, True])
def test_cancel_interrupts_idle_transport_and_preserves_callback_across_threads(
    monkeypatch,
    waiting_for_headers,
    async_caller,
):
    cancelled = threading.Event()
    closed = threading.Event()
    calls = []

    class Idle(httpx.AsyncByteStream):
        async def __aiter__(self):
            cancelled.set()
            await asyncio.sleep(30)
            yield b"unreachable"

        async def aclose(self):
            closed.set()

    async def handler(request):
        calls.append(request)
        if waiting_for_headers:
            cancelled.set()
            try:
                await asyncio.sleep(30)
            finally:
                closed.set()
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=Idle())

    monkeypatch.setattr(
        completion_stream.httpx,
        "AsyncClient",
        lambda **kwargs: CLIENT(**kwargs, transport=httpx.MockTransport(handler)),
    )

    def checkpoint():
        if cancelled.is_set():
            raise Cancelled()

    def call():
        with completion_stream.cancellable_completion(checkpoint), pytest.raises(Cancelled):
            completion_stream.complete_json(URL, {}, {}, deadline_seconds=2)

    async def run():
        call()

    if async_caller:
        asyncio.run(run())
    else:
        call()
    assert closed.is_set()
    assert len(calls) == 1  # Cancellation must not replay a billable request.


def test_cancellation_wins_an_already_delivered_result_and_scope_is_restored(monkeypatch):
    received = threading.Event()

    class Complete(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"choices": [{"message": {"content": "{\\"claims\\": []}"}}]}'

    async def handler(request):
        received.set()
        return httpx.Response(200, headers={"Content-Type": "application/json"}, stream=Complete())

    monkeypatch.setattr(
        completion_stream.httpx,
        "AsyncClient",
        lambda **kwargs: CLIENT(**kwargs, transport=httpx.MockTransport(handler)),
    )

    def checkpoint():
        if received.is_set():
            raise Cancelled()

    with completion_stream.cancellable_completion(checkpoint), pytest.raises(Cancelled):
        completion_stream.complete_json(URL, {}, {})
    assert completion_stream.complete_json(URL, {}, {}) == {"claims": []}
