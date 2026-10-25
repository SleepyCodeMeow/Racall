import type { EmbeddingProviderId, ProviderId, ProviderProfile } from '../../lib/api';
import type { MessageKey } from '../../lib/translations';

export const providerDefaults: Record<ProviderId, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com/v1',
  ollama: 'http://127.0.0.1:11434/v1',
  ollama_cloud: 'https://ollama.com/v1',
  llama_cpp: 'http://127.0.0.1:8080/v1',
  openai_compatible: 'http://127.0.0.1:8080/v1',
};

export const providerNames: Record<ProviderId, string> = {
  openai: 'OpenAI',
  anthropic: 'Claude / Anthropic',
  ollama: 'Ollama',
  ollama_cloud: 'Ollama Cloud',
  llama_cpp: 'llama.cpp',
  openai_compatible: 'OpenAI-compatible',
};

export const providerHints: Record<ProviderId, MessageKey> = {
  openai: 'settings.hintOpenAI',
  anthropic: 'settings.hintAnthropic',
  ollama: 'settings.hintOllama',
  ollama_cloud: 'settings.hintOllamaCloud',
  llama_cpp: 'settings.hintLlamaCpp',
  openai_compatible: 'settings.hintCustom',
};

export const embeddingProviders: EmbeddingProviderId[] = [
  'openai',
  'ollama',
  'llama_cpp',
  'openai_compatible',
];

export const needsApiKey = (provider: ProviderId) =>
  provider === 'openai' || provider === 'anthropic' || provider === 'ollama_cloud';

export const providerMode = (provider: ProviderId): MessageKey =>
  needsApiKey(provider)
    ? 'settings.cloudConnection'
    : provider === 'openai_compatible'
      ? 'settings.customConnection'
      : 'settings.localConnection';

export const emptyProfile = (provider: ProviderId): ProviderProfile => ({
  base_url: providerDefaults[provider],
  model: '',
  has_key: false,
});
