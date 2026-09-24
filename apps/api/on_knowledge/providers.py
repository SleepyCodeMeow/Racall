import json
import math
import os
from typing import Protocol
from urllib.parse import urlsplit

import httpx
import keyring


class LLMProvider(Protocol):
    def complete(self, system: str, data: dict) -> dict: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


def validate_endpoint(url: str) -> str:
    p = urlsplit(url)
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
    try:
        return keyring.get_password("OpenNotebook", base_url) or ""
    except keyring.errors.KeyringError:
        return ""


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
                response = client.post(self.base + route, json=body,
                                       headers={"Authorization": "Bearer " + (get_key(self.base) or "ollama")})
                if response.status_code >= 400:
                    raise ValueError(f"Провайдер вернул HTTP {response.status_code}. Проверьте URL, ключ и имя модели.")
                return response.json()
        except httpx.HTTPError as exc:
            raise ValueError("Не удалось связаться с AI-провайдером. Проверьте подключение и настройки.") from exc

    def complete(self, system: str, data: dict) -> dict:
        if not self.settings.get("model"):
            raise ValueError("Укажите имя модели в настройках AI")
        response = self.request("/chat/completions", {
            "model": self.settings["model"], "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
            ], "response_format": {"type": "json_object"},
        })
        try:
            return json.loads(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Модель не вернула ожидаемый JSON. Выберите модель с JSON mode.") from exc

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
