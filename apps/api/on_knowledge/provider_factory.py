"""Select the completion protocol without coupling retrieval to a chat vendor."""

from .provider_settings import normalize_settings
from .providers import LLMProvider, OpenAICompatible


def completion_provider(settings: dict) -> LLMProvider:
    selected = normalize_settings(settings)
    if selected["provider"] == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(selected)
    return OpenAICompatible(selected)
