import json
import math
import os
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType
from typing import Protocol
from urllib.parse import urlsplit

import httpx
import keyring

from .completion_stream import CompletionDeadlineError, CompletionProtocolError, complete_json


class LLMProvider(Protocol):
    def complete(self, system: str, data: dict) -> dict: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


_frozen_keys: ContextVar[Mapping[tuple[str, str], str] | None] = ContextVar("provider_keys", default=None)


def provider_identity(settings: dict) -> tuple[str, str]:
    return settings.get("provider", "openai_compatible"), settings["base_url"].rstrip("/")


@contextmanager
def frozen_provider_keys(keys: Mapping[tuple[str, str], str]):
    """Keep a generation's credentials in its execution context, never on disk.

    An empty key is deliberately frozen too: changing environment/keychain values
    must not change an already started generation. Unknown endpoints fail closed.
    ContextVar isolation keeps other requests and worker threads unaffected.
    """
    snapshot = dict(keys)
    if any(not isinstance(value, str) for value in snapshot.values()):
        raise ValueError("Invalid frozen credential")
    token = _frozen_keys.set(MappingProxyType(snapshot))
    try:
        yield
    finally:
        _frozen_keys.reset(token)


def validate_endpoint(url: str) -> str:
    if not isinstance(url, str) or not url or len(url) > 2000 or any(char.isspace() or ord(char) < 32 for char in url):
        raise ValueError("Неверный URL API")
    try:
        p = urlsplit(url)
        p.port  # Reject malformed/out-of-range ports before constructing a request.
    except ValueError as exc:
        raise ValueError("Неверный URL API") from exc
    if p.username or p.password or p.query or p.fragment:
        raise ValueError("URL API не должен содержать пароль, query или fragment")
    if p.scheme != "https" and not (p.scheme == "http" and p.hostname in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("Используйте HTTPS; HTTP разрешён только для локальной модели")
    if not p.hostname:
        raise ValueError("Неверный URL API")
    return url.rstrip("/")


def get_key(base_url: str) -> str:
    override = os.getenv("OPENNOTEBOOK_API_KEY")
    if override:
        return override
    return _stored_key(base_url)


def _stored_key(base_url: str) -> str:
    try:
        return keyring.get_password("OpenNotebook", base_url) or ""
    except keyring.errors.KeyringError:
        return ""


def provider_key(settings: dict) -> str:
    """Keep legacy overrides while scoping new environment keys to their provider."""
    # Transport historically stripped trailing slashes before keychain lookup.
    # Preserve that key identity without rewriting old embedding index identities.
    provider, base = provider_identity(settings)
    frozen = _frozen_keys.get()
    if frozen is not None:
        if (provider, base) not in frozen:
            raise ValueError("AI connection changed during generation.")
        return frozen[provider, base]
    if provider == "openai_compatible":
        return get_key(base)
    variable = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                "ollama_cloud": "OLLAMA_API_KEY"}.get(provider)
    return _stored_key(base) or (os.getenv(variable, "") if variable else "")


def _authorization(settings: dict) -> dict[str, str]:
    key = provider_key(settings)
    if settings.get("provider") in ("openai", "ollama_cloud") and not key:
        raise ValueError("Укажите API-ключ для выбранного провайдера в настройках AI")
    return {"Authorization": "Bearer " + (key or "ollama")}


def save_key(base_url: str, value: str):
    try:
        if value:
            keyring.set_password("OpenNotebook", base_url, value)
        elif keyring.get_password("OpenNotebook", base_url):
            keyring.delete_password("OpenNotebook", base_url)
    except keyring.errors.KeyringError as exc:
        raise ValueError("Хранилище секретов ОС недоступно. Ключ не сохранён; проверьте Keychain/Credential Manager/Secret Service.") from exc


class OpenAICompatible:
    def __init__(self, settings: dict):
        self.settings = settings
        self.base = validate_endpoint(settings["base_url"])

    def request(self, route: str, body: dict) -> dict:
        try:
            with httpx.Client(timeout=httpx.Timeout(120, connect=15), trust_env=False) as client:
                response = client.post(self.base + route, json=body, headers=_authorization(self.settings))
                if response.status_code >= 400:
                    raise ValueError(f"Провайдер вернул HTTP {response.status_code}. Проверьте URL, ключ и имя модели.")
                return response.json()
        except httpx.HTTPError as exc:
            raise ValueError("Не удалось связаться с AI-провайдером. Проверьте подключение и настройки.") from exc

    def complete(self, system: str, data: dict) -> dict:
        if not self.settings.get("model"):
            raise ValueError("Укажите имя модели в настройках AI")
        body = {
            "model": self.settings["model"], "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
            ], "response_format": {"type": "json_object"},
        }
        try:
            return complete_json(
                self.base + "/chat/completions",
                _authorization(self.settings), body,
            )
        except CompletionDeadlineError as exc:
            raise ValueError("Превышено общее время генерации ответа. Уточните вопрос или выберите более быструю модель.") from exc
        except httpx.ReadTimeout as exc:
            raise ValueError("Модель перестала передавать данные. Проверьте AI-провайдер или повторите запрос.") from exc
        except CompletionProtocolError as exc:
            raise ValueError("Провайдер вернул неполный или некорректный поток ответа. Повторите запрос или выберите другую модель.") from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"Провайдер вернул HTTP {exc.response.status_code}. Проверьте URL, ключ и имя модели.") from exc
        except httpx.HTTPError as exc:
            raise ValueError("Не удалось связаться с AI-провайдером. Проверьте подключение и настройки.") from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            response = self.request("/embeddings", {"model": self.settings["embedding_model"], "input": batch})
            data = sorted(response.get("data", []), key=lambda item: item["index"])
            if len(data) != len(batch):
                raise ValueError("Провайдер вернул неполный набор embeddings")
            for item in data:
                vector = item["embedding"]
                if not vector or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
                    raise ValueError("Провайдер вернул некорректный embedding")
                vectors.append(vector)
        return vectors
