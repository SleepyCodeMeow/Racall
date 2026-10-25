"""Bounded synchronous completion API with cancellable async HTTP ownership.

Framing, strict JSON and provider state machines live in completion/. No partial
result or automatic inference retry crosses this transport's public boundary.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar, copy_context

import httpx

from .completion.events import response_chunks
from .completion.payloads import CompletionProtocolError, json_object

__all__ = ["CompletionDeadlineError", "CompletionProtocolError", "cancellable_completion", "complete_json"]

_cancellation: ContextVar[Callable[[], None] | None] = ContextVar("completion_cancellation", default=None)


@contextmanager
def cancellable_completion(checkpoint: Callable[[], None]):
    """Interrupt an in-flight request when a generation checkpoint raises.

    Cancellation closes the client connection; providers remain responsible for
    stopping their own computation. No partial completion is returned or retried.
    """
    token = _cancellation.set(checkpoint)
    try:
        yield
    finally:
        _cancellation.reset(token)


class CompletionDeadlineError(TimeoutError):
    """The entire request exceeded its deadline, even if bytes kept arriving."""


async def _complete_json(
    url: str, headers: dict, payload: dict, deadline_seconds: float, idle_seconds: float, protocol: str
) -> dict:
    # Both APIs share request limits and framing; their completion state machines
    # remain separate so one protocol cannot accidentally accept the other.
    if protocol == "anthropic":
        from .anthropic_stream import full_response, stream_response
    else:
        from .completion.openai import full_response, stream_response
    try:
        async with asyncio.timeout(deadline_seconds):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(idle_seconds, connect=15), trust_env=False
            ) as client:
                request_headers = {"Accept-Encoding": "identity", **headers}
                async with client.stream(
                    "POST", url, headers=request_headers, json={**payload, "stream": True}
                ) as response:
                    response.raise_for_status()
                    encoding = response.headers.get("content-encoding", "identity").lower().strip()
                    if encoding not in ("", "identity"):
                        raise CompletionProtocolError(
                            "The provider ignored the uncompressed response request."
                        )
                    media_type = response.headers.get("content-type", "").partition(";")[0].lower().strip()
                    if media_type == "text/event-stream":
                        return await stream_response(response)
                    if media_type == "application/json":
                        body = bytearray()
                        async for chunk in response_chunks(response):
                            body.extend(chunk)
                        return full_response(json_object(bytes(body)))
                    raise CompletionProtocolError("The provider response type is unsupported.")
    except TimeoutError as error:
        raise CompletionDeadlineError("The completion exceeded its total deadline.") from error


async def _controlled_completion(url, headers, payload, deadline_seconds, idle_seconds, protocol):
    checkpoint = _cancellation.get()
    if checkpoint is None:
        return await _complete_json(url, headers, payload, deadline_seconds, idle_seconds, protocol)
    checkpoint()
    task = asyncio.create_task(
        _complete_json(url, headers, payload, deadline_seconds, idle_seconds, protocol)
    )
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=0.2)
            checkpoint()  # Cancellation also wins a result delivered in the same interval.
            if done:
                return task.result()
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def complete_json(
    url: str,
    headers: dict,
    payload: dict,
    *,
    deadline_seconds: float = 300,
    idle_seconds: float = 120,
    protocol: str = "openai",
) -> dict:
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
        return asyncio.run(
            _controlled_completion(url, headers, payload, deadline_seconds, idle_seconds, protocol)
        )
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="completion") as executor:
        return executor.submit(
            copy_context().run,
            asyncio.run,
            _controlled_completion(url, headers, payload, deadline_seconds, idle_seconds, protocol),
        ).result()
