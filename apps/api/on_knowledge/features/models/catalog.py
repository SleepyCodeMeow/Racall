"""Read-only provider model discovery, pagination and public catalog entries."""

from __future__ import annotations

import asyncio

import httpx

from .protocol import counter, decode_json, model_id

LIST_LIMIT = 1024 * 1024


async def _list_json(client, url: str, headers: dict, params: dict | None, limit: int) -> dict:
    data = bytearray()
    async with client.stream("GET", url, headers=headers, params=params) as response:
        if response.status_code != 200:
            raise ValueError(f"Model provider returned HTTP {response.status_code}.")
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise ValueError("Model provider returned an invalid model list.")
        async for chunk in response.aiter_raw():
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError("Model provider response is too large.")
    try:
        return decode_json(bytes(data))
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("Model provider returned an invalid model list.") from None


def _entry(item: dict, provider: str, native: bool) -> dict:
    if not isinstance(item, dict):
        raise ValueError("Model provider returned an invalid model list.")
    try:
        name = model_id(item.get("model", item.get("name")) if native else item.get("id"))
        cloud = provider == "ollama_cloud" or (
            native and (bool(item.get("remote_host")) or name.endswith((":cloud", "-cloud")))
        )
        kind = "cloud" if cloud or provider in {"openai", "anthropic"} else ("local" if native else "server")
        entry = {"id": name, "kind": kind, "installed": native and not cloud}
        if native and "size" in item:
            entry["size_bytes"] = counter(item["size"])
        return entry
    except ValueError:
        raise ValueError("Model provider returned an invalid model list.") from None


async def discover_models(
    provider: str, url: str, headers: dict, client_factory, *, response_limit: int
) -> list[dict]:
    native = provider in {"ollama", "ollama_cloud"}
    models = {}
    try:
        async with asyncio.timeout(20), client_factory() as client:
            cursor = None
            for _ in range(10):
                params = {"limit": 1000} if provider == "anthropic" else None
                if cursor:
                    params["after_id"] = cursor
                result = await _list_json(client, url, headers, params, response_limit)
                entries = result.get("models" if native else "data")
                if not isinstance(entries, list) or len(entries) > 1000:
                    raise ValueError("Model provider returned an invalid model list.")
                for item in entries:
                    entry = _entry(item, provider, native)
                    models[entry["id"]] = entry
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
                    cursor = model_id(next_cursor)
                except ValueError:
                    raise ValueError("Model provider returned an invalid model list.") from None
            else:
                raise ValueError("Model provider response is too large.")
    except (TimeoutError, httpx.TimeoutException):
        raise ValueError("Model provider request timed out.") from None
    except httpx.HTTPError:
        raise ValueError("Could not connect to the model provider.") from None
    return sorted(models.values(), key=lambda item: item["id"].casefold())
