from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from typing import Callable
from urllib.parse import urlsplit

import httpx

from ...provider_settings import PROVIDER_DEFAULTS
from ...providers import provider_key, validate_endpoint
from ...storage import ConflictError, Store, identifier, uid, write_json

LIST_LIMIT = 1024 * 1024
LINE_LIMIT = 32 * 1024
PULL_LIMIT = 8 * 1024 * 1024
PULL_SECONDS = 60 * 60
ACTIVE = frozenset({"queued", "running"})
STATUSES = ACTIVE | {"completed", "failed", "cancelled", "interrupted"}
PHASES = {"queued", "manifest", "downloading", "verifying", "writing",
          "completed", "cancelled", "interrupted", "failed"}
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)?(?::[A-Za-z0-9][A-Za-z0-9_.-]*)?\Z")


def _json(value: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = item
        return result

    def invalid_constant(value):
        raise ValueError("Invalid JSON constant")

    result = json.loads(value.decode("utf-8"), object_pairs_hook=pairs,
                        parse_constant=invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("Expected an object")
    return result


def _model_id(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 200 or any(
        ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value
    ):
        raise ValueError("Invalid model ID")
    return value


def _counter(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError("Invalid progress count")
    return value


def _native(base: str) -> str:
    return (base[:-3] if base.endswith("/v1") else base) + "/api"


def _local(base: str) -> bool:
    return urlsplit(base).hostname in {"127.0.0.1", "localhost", "::1"}


class Models:
    """No inference, shell commands, model loading, or automatic download retries.

    Jobs belong to this app process. Only their small public snapshot is persisted;
    endpoints, keys and upstream error bodies never enter the job metadata.
    """

    def __init__(self, store: Store, client_factory: Callable | None = None):
        self.store = store
        self.path = store.root / "model-download.json"
        self.client_factory = client_factory or httpx.AsyncClient
        self.job: dict | None = None
        self.task: asyncio.Task | None = None
        self.closed = False

    def _client(self):
        return self.client_factory(timeout=httpx.Timeout(30, connect=5), trust_env=False,
                                   follow_redirects=False, headers={"Accept-Encoding": "identity"})

    def _profile(self, provider: str | None) -> tuple[str, dict, str, dict]:
        settings = self.store.settings()
        provider = provider if provider is not None else settings["provider"]
        if provider not in PROVIDER_DEFAULTS:
            raise ValueError("Unknown AI provider.")
        profile = {"provider": provider, **settings["profiles"][provider]}
        base = validate_endpoint(profile["base_url"])
        key = provider_key(profile)
        if provider in {"anthropic", "openai", "ollama_cloud"} and not key:
            raise ValueError("Configure an API key before listing cloud models.")
        headers = {"Authorization": "Bearer " + key} if key else {}
        if provider == "anthropic":
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        return provider, profile, base, headers

    async def _list_json(self, client, url: str, headers: dict, params: dict | None = None) -> dict:
        data = bytearray()
        async with client.stream("GET", url, headers=headers, params=params) as response:
            if response.status_code != 200:
                raise ValueError(f"Model provider returned HTTP {response.status_code}.")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ValueError("Model provider returned an invalid model list.")
            async for chunk in response.aiter_raw():
                data.extend(chunk)
                if len(data) > LIST_LIMIT:
                    raise ValueError("Model provider response is too large.")
        try:
            return _json(bytes(data))
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError("Model provider returned an invalid model list.") from None

    async def catalog(self, provider: str | None = None) -> dict:
        provider, profile, base, headers = self._profile(provider)
        native = provider in {"ollama", "ollama_cloud"}
        models = {}
        try:
            async with asyncio.timeout(20), self._client() as client:
                cursor = None
                for _ in range(10):
                    params = {"limit": 1000} if provider == "anthropic" else None
                    if cursor:
                        params["after_id"] = cursor
                    result = await self._list_json(client, _native(base) + "/tags" if native else base + "/models",
                                                   headers, params)
                    entries = result.get("models" if native else "data")
                    if not isinstance(entries, list) or len(entries) > 1000:
                        raise ValueError("Model provider returned an invalid model list.")
                    for item in entries:
                        if not isinstance(item, dict):
                            raise ValueError("Model provider returned an invalid model list.")
                        try:
                            name = _model_id(item.get("model", item.get("name")) if native else item.get("id"))
                            cloud = provider == "ollama_cloud" or (native and (
                                bool(item.get("remote_host")) or name.endswith((":cloud", "-cloud"))
                            ))
                            kind = "cloud" if cloud or provider in {"openai", "anthropic"} else (
                                "local" if native else "server"
                            )
                            entry = {"id": name, "kind": kind, "installed": native and not cloud}
                            if native and "size" in item:
                                entry["size_bytes"] = _counter(item["size"])
                        except ValueError:
                            raise ValueError("Model provider returned an invalid model list.") from None
                        models[name] = entry
                    if len(models) > 1000:
                        raise ValueError("Model provider response is too large.")
                    if provider == "anthropic" and type(result.get("has_more", False)) is not bool:
                        raise ValueError("Model provider returned an invalid model list.")
                    if provider != "anthropic" or result.get("has_more") is not True:
                        break
                    next_cursor = result.get("last_id")
                    if not entries or not isinstance(next_cursor, str) or next_cursor == cursor:
                        raise ValueError("Model provider returned an invalid model list.")
                    try:
                        cursor = _model_id(next_cursor)
                    except ValueError:
                        raise ValueError("Model provider returned an invalid model list.") from None
                else:
                    raise ValueError("Model provider response is too large.")
        except (TimeoutError, httpx.TimeoutException):
            raise ValueError("Model provider request timed out.") from None
        except httpx.HTTPError:
            raise ValueError("Could not connect to the model provider.") from None
        return {"provider": provider, "selected_model": profile["model"],
                "models": sorted(models.values(), key=lambda item: item["id"].casefold()),
                "can_download": provider == "ollama" and _local(base)}

    def _save(self):
        write_json(self.path, self.job)

    def recover(self):
        """A restart never resumes a model download without another user action."""
        if not self.path.exists():
            return
        try:
            if self.path.stat().st_size > 4096:
                return
            raw = _json(self.path.read_bytes())
            model = _model_id(raw["model"])
            if not MODEL_NAME.fullmatch(model) or raw["status"] not in STATUSES or raw["phase"] not in PHASES:
                return
            self.job = {"id": identifier(raw["id"]), "model": model, "status": raw["status"],
                        "phase": raw["phase"], "completed": _counter(raw["completed"]),
                        "total": _counter(raw["total"])}
            if self.job["status"] in ACTIVE:
                self.job.update(status="interrupted", phase="interrupted", completed=0, total=0,
                                error="Model download was interrupted. Please start it again.")
            elif self.job["status"] == "failed":
                self.job["error"] = "Model download failed. Check Ollama and try again."
            self._save()
        except (OSError, KeyError, TypeError, ValueError, UnicodeError, RecursionError):
            self.job = None

    def current(self) -> dict | None:
        return dict(self.job) if self.job else None

    def get(self, job_id: str) -> dict:
        job_id = identifier(job_id)
        if not self.job or self.job["id"] != job_id:
            raise FileNotFoundError("Model download not found.")
        return dict(self.job)

    async def download(self, model: str) -> dict:
        if not isinstance(model, str) or not MODEL_NAME.fullmatch(model) or len(model) > 200 or model.endswith((":cloud", "-cloud")):
            raise ValueError("Invalid Ollama model name.")
        if self.closed:
            raise ConflictError("Model downloads are shutting down.")
        if (self.job and self.job["status"] in ACTIVE) or (self.task and not self.task.done()):
            raise ConflictError("Another model download is already running.")
        # Always use the saved local Ollama profile, independent of the active chat
        # provider. Callers cannot supply a URL, headers or insecure transport flags.
        _, _, base, headers = self._profile("ollama")
        if not _local(base):
            raise ValueError("Downloads require a local Ollama connection.")
        self.job = {"id": uid(), "model": model, "status": "queued", "phase": "queued",
                    "completed": 0, "total": 0}
        self._save()
        self.task = asyncio.create_task(self._pull(_native(base) + "/pull", headers, model))
        return dict(self.job)

    def _progress(self, item: dict) -> bool:
        if "error" in item:
            raise ValueError("Model download failed. Check Ollama and try again.")
        status = item.get("status")
        if not isinstance(status, str) or len(status) > 256:
            raise ValueError("Model download progress was invalid.")
        if status == "success":
            self.job.update(status="completed", phase="completed")
            self._save()
            return True
        if status == "pulling manifest":
            phase = "manifest"
        elif status.startswith("pulling "):
            phase = "downloading"
        elif status.startswith("verifying "):
            phase = "verifying"
        elif status.startswith(("writing ", "removing ")):
            phase = "writing"
        else:
            raise ValueError("Model download progress was invalid.")
        try:
            completed, total = _counter(item.get("completed", 0)), _counter(item.get("total", 0))
            if completed > total:
                raise ValueError("Invalid progress")
        except ValueError:
            raise ValueError("Model download progress was invalid.") from None
        self.job.update(phase=phase, completed=completed, total=total)
        return False

    async def _pull(self, url: str, headers: dict, model: str):
        self.job.update(status="running", phase="manifest")
        self._save()
        try:
            async with asyncio.timeout(PULL_SECONDS), self._client() as client:
                async with client.stream("POST", url, headers=headers, json={"model": model, "stream": True}) as response:
                    if response.status_code != 200:
                        raise ValueError(f"Model provider returned HTTP {response.status_code}.")
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise ValueError("Model download progress was invalid.")
                    buffer, count = bytearray(), 0
                    async for chunk in response.aiter_raw():
                        count += len(chunk)
                        if count > PULL_LIMIT:
                            raise ValueError("Model download progress was invalid.")
                        buffer.extend(chunk)
                        while b"\n" in buffer:
                            line, _, remaining = buffer.partition(b"\n")
                            buffer = bytearray(remaining)
                            if len(line) > LINE_LIMIT:
                                raise ValueError("Model download progress was invalid.")
                            if line.strip() and self._progress(_json(line)):
                                return
                        if len(buffer) > LINE_LIMIT:
                            raise ValueError("Model download progress was invalid.")
                    if buffer.strip() and self._progress(_json(bytes(buffer))):
                        return
                    raise ValueError("Model download progress was invalid.")
        except asyncio.CancelledError:
            if self.job["status"] in ACTIVE:
                self.job.update(status="cancelled", phase="cancelled", completed=0, total=0)
            raise
        except (TimeoutError, httpx.TimeoutException):
            self.job.update(status="failed", phase="failed", error="Model download timed out. You can start it again.")
        except (ValueError, UnicodeError, RecursionError):
            self.job.update(status="failed", phase="failed", error="Model download failed. Check Ollama and try again.")
        except httpx.HTTPError:
            self.job.update(status="failed", phase="failed", error="Could not connect to the model provider.")
        finally:
            self._save()

    async def cancel(self, job_id: str) -> dict:
        self.get(job_id)
        if self.job["status"] in ACTIVE:
            self.job.update(status="cancelled", phase="cancelled", completed=0, total=0)
            self._save()
            if self.task:
                self.task.cancel()
                with suppress(asyncio.CancelledError):
                    await asyncio.wait_for(self.task, 2)
        return dict(self.job)

    async def shutdown(self):
        self.closed = True
        if self.job and self.job["status"] in ACTIVE:
            self.job.update(status="interrupted", phase="interrupted", completed=0, total=0,
                            error="Model download was interrupted. Please start it again.")
            self._save()
            if self.task:
                self.task.cancel()
                with suppress(asyncio.CancelledError):
                    await asyncio.wait_for(self.task, 2)
