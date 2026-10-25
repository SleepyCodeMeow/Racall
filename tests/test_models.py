import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from on_knowledge.features.models import service as model_service
from on_knowledge.features.models.router import create_router
from on_knowledge.features.models.service import Models
from on_knowledge.provider_settings import normalize_settings, persistent_settings
from on_knowledge.storage import ConflictError, Store, write_json


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks, *, wait=False):
        self.chunks = chunks
        self.wait = wait
        self.closed = False
        self.started = asyncio.Event()

    async def __aiter__(self):
        self.started.set()
        for chunk in self.chunks:
            yield chunk
        if self.wait:
            await asyncio.Event().wait()

    async def aclose(self):
        self.closed = True


def response(data=None, *, stream=None, status=200, headers=None):
    if stream is None:
        stream = Stream([json.dumps(data).encode()])
    return httpx.Response(status, stream=stream, headers=headers)


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path)
    settings = normalize_settings({"provider": "ollama"})
    settings["profiles"]["ollama"]["model"] = "selected:latest"
    write_json(tmp_path / "settings.json", persistent_settings(settings))
    return store


def make_service(store, monkeypatch, handler, key=""):
    calls = []

    async def dispatch(request):
        calls.append(request)
        return handler(request)

    monkeypatch.setattr(model_service, "provider_key", lambda settings: key)
    service = Models(
        store, lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(dispatch), **kwargs)
    )
    return service, calls


@pytest.mark.asyncio
async def test_local_catalog_lists_downloaded_and_cloud_without_generation_or_settings_writes(
    store, monkeypatch
):
    before = (store.root / "settings.json").read_bytes()
    service, calls = make_service(
        store,
        monkeypatch,
        lambda request: response(
            {
                "models": [
                    {"model": "z:latest", "size": 4096},
                    {"name": "a:cloud", "size": 0},
                    {"model": "remote:latest", "remote_host": "https://cloud.invalid"},
                ]
            }
        ),
    )
    result = await service.catalog()
    assert result == {
        "provider": "ollama",
        "selected_model": "selected:latest",
        "can_download": True,
        "models": [
            {"id": "a:cloud", "kind": "cloud", "installed": False, "size_bytes": 0},
            {"id": "remote:latest", "kind": "cloud", "installed": False},
            {"id": "z:latest", "kind": "local", "installed": True, "size_bytes": 4096},
        ],
    }
    assert len(calls) == 1 and calls[0].method == "GET"
    assert str(calls[0].url) == "http://127.0.0.1:11434/api/tags"
    assert not calls[0].content and "authorization" not in calls[0].headers
    assert (store.root / "settings.json").read_bytes() == before


@pytest.mark.parametrize(
    "provider,url,kind",
    [
        ("openai", "https://api.openai.com/v1/models", "cloud"),
        ("ollama_cloud", "https://ollama.com/api/tags", "cloud"),
        ("llama_cpp", "http://127.0.0.1:8080/v1/models", "server"),
        ("openai_compatible", "https://api.openai.com/v1/models", "server"),
    ],
)
@pytest.mark.asyncio
async def test_catalog_provider_endpoints_and_auth(store, monkeypatch, provider, url, kind):
    payload = (
        {"models": [{"name": "remote-model", "size": 0}]}
        if provider == "ollama_cloud"
        else {"data": [{"id": "remote-model", "ignored_secret": "hidden"}]}
    )
    service, calls = make_service(store, monkeypatch, lambda request: response(payload), key="catalog-secret")
    result = await service.catalog(provider)
    assert str(calls[0].url) == url
    assert calls[0].headers["authorization"] == "Bearer catalog-secret"
    assert result["models"][0]["kind"] == kind and not result["can_download"]
    assert "secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_anthropic_native_headers_and_cursor_pagination(store, monkeypatch):
    def handler(request):
        assert request.url.path == "/v1/models"
        assert request.headers["x-api-key"] == "claude-secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert "authorization" not in request.headers
        assert request.url.params["limit"] == "1000"
        if request.url.params.get("after_id"):
            assert request.url.params["after_id"] == "model-a"
            return response({"data": [{"id": "model-b"}], "has_more": False})
        return response({"data": [{"id": "model-a"}], "has_more": True, "last_id": "model-a"})

    service, calls = make_service(store, monkeypatch, handler, key="claude-secret")
    result = await service.catalog("anthropic")
    assert [item["id"] for item in result["models"]] == ["model-a", "model-b"]
    assert len(calls) == 2


@pytest.mark.parametrize("provider", ["openai", "anthropic", "ollama_cloud"])
@pytest.mark.asyncio
async def test_cloud_key_required_before_network(store, monkeypatch, provider):
    service, calls = make_service(store, monkeypatch, lambda request: pytest.fail("unexpected request"))
    with pytest.raises(ValueError, match="Configure an API key"):
        await service.catalog(provider)
    assert calls == []


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"models": {}},
        {"models": [None]},
        {"models": [{"name": ""}]},
        {"models": [{"name": "model", "size": True}]},
        {"models": [{"name": "model", "size": -1}]},
        {"models": [{"name": "secret\nheader"}]},
        {"models": [{"name": "\ud800"}]},
    ],
)
@pytest.mark.asyncio
async def test_malformed_catalog_is_safely_rejected(store, monkeypatch, payload):
    service, _ = make_service(store, monkeypatch, lambda request: response(payload))
    with pytest.raises(ValueError, match="invalid model list"):
        await service.catalog()


@pytest.mark.parametrize("status", [301, 401, 403, 404, 500])
@pytest.mark.asyncio
async def test_http_failure_never_follows_redirects_or_returns_body(store, monkeypatch, status):
    service, calls = make_service(
        store,
        monkeypatch,
        lambda request: response(
            {"error": "sensitive-upstream-url-and-key"},
            status=status,
            headers={"Location": "https://different.invalid/private"},
        ),
    )
    with pytest.raises(ValueError, match=f"HTTP {status}") as caught:
        await service.catalog()
    assert "sensitive" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_catalog_body_limit_and_encoding(store, monkeypatch):
    monkeypatch.setattr(model_service, "LIST_LIMIT", 20)
    service, _ = make_service(store, monkeypatch, lambda request: response({"models": [{"name": "large"}]}))
    with pytest.raises(ValueError, match="too large"):
        await service.catalog()
    service, _ = make_service(
        store, monkeypatch, lambda request: response({}, headers={"Content-Encoding": "gzip"})
    )
    with pytest.raises(ValueError, match="invalid model list"):
        await service.catalog()


@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx.ConnectError("private-endpoint-secret"), "Could not connect"),
        (httpx.ReadTimeout("private-endpoint-secret"), "timed out"),
    ],
)
@pytest.mark.asyncio
async def test_catalog_network_error_redaction(store, monkeypatch, error, expected):
    def handler(request):
        raise error

    service, calls = make_service(store, monkeypatch, handler)
    with pytest.raises(ValueError, match=expected) as caught:
        await service.catalog()
    assert "secret" not in str(caught.value) and len(calls) == 1


@pytest.mark.asyncio
async def test_catalog_total_deadline_bounds_continuous_stream(store, monkeypatch):
    class Endless(Stream):
        async def __aiter__(self):
            while True:
                yield b" "
                await asyncio.sleep(0.01)

    stream = Endless([])
    original = asyncio.timeout
    monkeypatch.setattr(model_service.asyncio, "timeout", lambda seconds: original(0.04))
    service, _ = make_service(store, monkeypatch, lambda request: response(stream=stream))
    with pytest.raises(ValueError, match="timed out"):
        await service.catalog()
    assert stream.closed


@pytest.mark.parametrize(
    "name",
    [
        "../model",
        "model;echo",
        "https://host/model",
        "model:cloud",
        "model-cloud",
        "model\nother",
        "model:tag:extra",
        "name//model",
        "name/../model",
        "-flag",
        "x" * 201,
    ],
)
@pytest.mark.asyncio
async def test_invalid_download_names_never_make_requests(store, monkeypatch, name):
    service, calls = make_service(store, monkeypatch, lambda request: pytest.fail("unexpected request"))
    with pytest.raises(ValueError, match="Invalid Ollama model name"):
        await service.download(name)
    assert calls == [] and service.job is None


@pytest.mark.asyncio
async def test_download_only_targets_saved_local_ollama_even_if_cloud_is_active(store, monkeypatch):
    settings = store.settings()
    settings["provider"] = "anthropic"
    settings["profiles"]["ollama"]["base_url"] = "http://localhost:22334/proxy/v1"
    write_json(store.root / "settings.json", persistent_settings(settings))
    stream = Stream([b'{"status":"success"}\n'])
    service, calls = make_service(
        store, monkeypatch, lambda request: response(stream=stream), key="local-secret"
    )
    job = await service.download("namespace/test-model:Q4_K_M")
    assert job["status"] == "queued"
    await service.task
    assert service.get(job["id"])["status"] == "completed"
    assert len(calls) == 1 and calls[0].method == "POST"
    assert str(calls[0].url) == "http://localhost:22334/proxy/api/pull"
    assert json.loads(calls[0].content) == {"model": "namespace/test-model:Q4_K_M", "stream": True}
    persisted = service.path.read_text()
    assert "local-secret" not in persisted and "localhost" not in persisted and stream.closed


@pytest.mark.asyncio
async def test_remote_ollama_profile_cannot_download(store, monkeypatch):
    settings = store.settings()
    settings["profiles"]["ollama"]["base_url"] = "https://remote.invalid/v1"
    write_json(store.root / "settings.json", persistent_settings(settings))
    service, calls = make_service(store, monkeypatch, lambda request: pytest.fail("unexpected request"))
    with pytest.raises(ValueError, match="local Ollama"):
        await service.download("model:latest")
    assert not calls


@pytest.mark.asyncio
async def test_download_progress_counts_are_per_layer_and_shutdown_is_bounded(store, monkeypatch):
    stream = Stream(
        [
            b'{"status":"pulling manifest"}\n',
            b'{"status":"pulling sha256:first","completed":20,"total":100}\n',
            b'{"status":"pulling sha256:second","completed":2,"total":10}\n',
        ],
        wait=True,
    )
    service, _ = make_service(store, monkeypatch, lambda request: response(stream=stream))
    job = await service.download("model")
    await stream.started.wait()
    assert service.current()["completed"] == 2 and service.current()["total"] == 10
    assert service.current()["phase"] == "downloading"
    await asyncio.wait_for(service.shutdown(), 1)
    assert stream.closed and service.task.done()
    assert service.current()["status"] == "interrupted"
    recovered = Models(store)
    recovered.recover()
    assert recovered.current()["status"] == "interrupted" and recovered.task is None
    assert recovered.get(job["id"])["model"] == "model"


@pytest.mark.asyncio
async def test_cancel_closes_stream_and_only_one_job_can_run(store, monkeypatch):
    stream = Stream([b'{"status":"pulling manifest"}\n'], wait=True)
    service, calls = make_service(store, monkeypatch, lambda request: response(stream=stream))
    job = await service.download("model")
    await stream.started.wait()
    with pytest.raises(ConflictError, match="already running"):
        await service.download("other-model")
    cancelled = await asyncio.wait_for(service.cancel(job["id"]), 1)
    assert cancelled["status"] == "cancelled" and stream.closed
    assert service.task.done() and len(calls) == 1
    assert (await service.cancel(job["id"])) == cancelled


@pytest.mark.asyncio
async def test_cancel_queued_job_does_not_start_http_request(store, monkeypatch):
    service, calls = make_service(store, monkeypatch, lambda request: pytest.fail("unexpected request"))
    job = await service.download("model")
    result = await service.cancel(job["id"])
    assert result["status"] == "cancelled" and not calls


@pytest.mark.parametrize(
    "chunks",
    [
        [b'{"status":"pulling manifest"}\n'],
        [b"not-json\n"],
        [b'{"error":"private-upstream-secret"}\n'],
        [b'{"status":"pulling layer","completed":101,"total":100}\n'],
        [b'{"status":"pulling layer","completed":true,"total":100}\n'],
        [b'{"status":"pulling layer","completed":NaN,"total":100}\n'],
        [b'{"status":"success","status":"failure"}\n'],
        [b'{"status":"unknown-private-status"}\n'],
    ],
)
@pytest.mark.asyncio
async def test_invalid_or_incomplete_download_fails_without_raw_errors(store, monkeypatch, chunks):
    stream = Stream(chunks)
    service, calls = make_service(store, monkeypatch, lambda request: response(stream=stream))
    await service.download("model")
    await service.task
    assert service.current()["status"] == "failed" and stream.closed
    assert "private" not in service.path.read_text() and len(calls) == 1


@pytest.mark.asyncio
async def test_download_supports_split_utf8_and_final_success_without_newline(store, monkeypatch):
    stream = Stream(
        [
            b'{"status":"pulling mani',
            b'fest"}\n{"status":"verifying sha256 digest"}\n',
            b'{"status":"writing manifest"}\n{"status":"success"}',
        ]
    )
    service, _ = make_service(store, monkeypatch, lambda request: response(stream=stream))
    await service.download("model")
    await service.task
    assert service.current()["status"] == "completed" and stream.closed


@pytest.mark.asyncio
async def test_download_line_and_total_wire_limits(store, monkeypatch):
    monkeypatch.setattr(model_service, "LINE_LIMIT", 20)
    stream = Stream([b"x" * 21])
    service, _ = make_service(store, monkeypatch, lambda request: response(stream=stream))
    await service.download("model")
    await service.task
    assert service.current()["status"] == "failed" and stream.closed
    monkeypatch.setattr(model_service, "PULL_LIMIT", 10)
    stream = Stream([b" " * 11])
    service, _ = make_service(store, monkeypatch, lambda request: response(stream=stream))
    await service.download("model")
    await service.task
    assert service.current()["status"] == "failed" and stream.closed


@pytest.mark.parametrize("status", [401, 404, 500])
@pytest.mark.asyncio
async def test_download_http_errors_are_redacted_and_not_retried(store, monkeypatch, status):
    service, calls = make_service(
        store, monkeypatch, lambda request: response({"error": "private-key"}, status=status)
    )
    await service.download("model")
    await service.task
    assert service.current()["status"] == "failed"
    assert "private-key" not in service.path.read_text() and len(calls) == 1


@pytest.mark.asyncio
async def test_download_continuous_progress_still_has_wall_deadline(store, monkeypatch):
    class Endless(Stream):
        async def __aiter__(self):
            while True:
                yield b'{"status":"pulling manifest"}\n'
                await asyncio.sleep(0.01)

    stream = Endless([])
    monkeypatch.setattr(model_service, "PULL_SECONDS", 0.04)
    service, _ = make_service(store, monkeypatch, lambda request: response(stream=stream))
    await service.download("model")
    await service.task
    assert service.current()["status"] == "failed" and "timed out" in service.current()["error"]
    assert stream.closed


@pytest.mark.parametrize("state", ["running", "queued"])
def test_recovery_marks_unfinished_job_without_requests_or_replaying_secrets(store, state):
    write_json(
        store.root / "model-download.json",
        {
            "id": "a0cc1733-51ab-4c24-a6c1-5748c4c5d55b",
            "model": "saved-model",
            "status": state,
            "phase": "manifest",
            "completed": 3,
            "total": 10,
            "error": "old-private-secret",
            "endpoint": "https://private.invalid",
        },
    )
    service = Models(store, lambda **kwargs: pytest.fail("unexpected request"))
    service.recover()
    assert service.current()["status"] == "interrupted" and service.task is None
    assert "private" not in service.path.read_text()


def test_recovery_rejects_invalid_oversized_or_unexpected_metadata(store):
    path = store.root / "model-download.json"
    for content in ("{", "x" * 4097, '{"id":"not-id"}', "[]"):
        path.write_text(content)
        service = Models(store)
        service.recover()
        assert service.current() is None


def test_router_contract_and_body_validation(store, monkeypatch):
    service, _ = make_service(store, monkeypatch, lambda request: response({"models": []}))
    app = FastAPI()
    app.include_router(create_router(service))

    @app.exception_handler(ValueError)
    async def bad_request(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    with TestClient(app) as client:
        assert client.get("/api/models/downloads").json() == {"job": None}
        assert client.get("/api/models?provider=ollama").json()["provider"] == "ollama"
        assert client.get("/api/models?provider=unknown").status_code == 400
        for body in ({"model": "x", "url": "https://untrusted.invalid"}, {"model": 1}, {}, {"model": "../x"}):
            assert client.post("/api/models/downloads", json=body).status_code in {400, 422}
