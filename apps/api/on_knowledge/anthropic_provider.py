"""Claude Messages API adapter for the shared strict JSON provider contract."""

import json

import httpx

from .completion_stream import CompletionDeadlineError, CompletionProtocolError, complete_json


class AnthropicProvider:
    def __init__(self, settings: dict):
        from .providers import validate_endpoint

        self.settings = settings
        self.base = validate_endpoint(settings.get("base_url") or "https://api.anthropic.com/v1")

    def complete(self, system: str, data: dict) -> dict:
        from .providers import provider_key

        if not self.settings.get("model"):
            raise ValueError("Укажите имя модели в настройках AI")
        key = provider_key(self.settings)
        if not key:
            raise ValueError("Укажите API-ключ для выбранного провайдера в настройках AI")
        body = {
            "model": self.settings["model"],
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": json.dumps(data, ensure_ascii=False)}],
        }
        try:
            return complete_json(
                self.base + "/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
                body,
                protocol="anthropic",
            )
        except CompletionDeadlineError as exc:
            raise ValueError(
                "Превышено общее время генерации ответа. Уточните вопрос или выберите более быструю модель."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise ValueError(
                "Модель перестала передавать данные. Проверьте AI-провайдер или повторите запрос."
            ) from exc
        except CompletionProtocolError as exc:
            raise ValueError(
                "Провайдер вернул неполный или некорректный поток ответа. Повторите запрос или выберите другую модель."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Провайдер вернул HTTP {exc.response.status_code}. Проверьте URL, ключ и имя модели."
            ) from exc
        except httpx.HTTPError as exc:
            raise ValueError(
                "Не удалось связаться с AI-провайдером. Проверьте подключение и настройки."
            ) from exc
