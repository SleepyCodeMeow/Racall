"""Public provider wiring keeps streaming bounds and safe diagnostics."""

import httpx
import pytest
from on_knowledge import providers
from on_knowledge.completion_stream import CompletionDeadlineError, CompletionProtocolError


def provider(monkeypatch):
    monkeypatch.setattr(providers, "get_key", lambda base: "private-test-key")
    instance = providers.OpenAICompatible({"base_url": "http://127.0.0.1:11434/v1", "model": "fixture"})
    monkeypatch.setattr(instance, "request", lambda *args: pytest.fail("Completion used legacy non-streaming path"))
    return instance


def test_completion_uses_bounded_stream_transport_without_reasoning_override(monkeypatch):
    instance = provider(monkeypatch)
    calls = []

    def complete(url, headers, payload):
        calls.append((url, headers, payload))
        return {"claims": []}

    monkeypatch.setattr(providers, "complete_json", complete, raising=False)
    assert instance.complete("System instruction", {"question": "What is known?"}) == {"claims": []}
    assert len(calls) == 1
    url, headers, body = calls[0]
    assert url.endswith("/chat/completions")
    assert headers == {"Authorization": "Bearer private-test-key"}
    assert body["model"] == "fixture" and body["response_format"] == {"type": "json_object"}
    assert body["messages"][0]["content"] == "System instruction"
    assert not {"think", "reasoning_effort", "temperature", "max_tokens"} & set(body)


@pytest.mark.parametrize("error,expected", [
    (CompletionDeadlineError("secret diagnostic"), "общее время"),
    (httpx.ReadTimeout("secret diagnostic"), "передавать данные"),
    (CompletionProtocolError("secret diagnostic"), "поток ответа"),
    (httpx.ConnectError("secret diagnostic"), "связаться"),
])
def test_completion_errors_are_distinct_sanitized_and_not_retried(monkeypatch, error, expected):
    instance = provider(monkeypatch)
    calls = []

    def complete(*args):
        calls.append(args)
        raise error

    monkeypatch.setattr(providers, "complete_json", complete, raising=False)
    with pytest.raises(ValueError) as caught:
        instance.complete("system", {})
    assert expected in str(caught.value)
    assert "secret" not in str(caught.value) and "private-test-key" not in str(caught.value)
    assert len(calls) == 1


def test_completion_http_error_keeps_safe_status_without_provider_body(monkeypatch):
    instance = provider(monkeypatch)
    request = httpx.Request("POST", "http://127.0.0.1:11434/v1/chat/completions")
    response = httpx.Response(401, request=request)

    def complete(*args):
        raise httpx.HTTPStatusError("private provider diagnostic", request=request, response=response)

    monkeypatch.setattr(providers, "complete_json", complete, raising=False)
    with pytest.raises(ValueError, match="HTTP 401") as caught:
        instance.complete("system", {})
    assert "private" not in str(caught.value)
