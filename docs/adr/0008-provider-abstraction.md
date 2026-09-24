# Provider abstraction

Status: accepted for 0.1 desktop preview

## Context
Нужна смена облака и локальной модели без смены знаний.

## Decision
LLMProvider и EmbeddingProvider protocols, OpenAI-compatible transport. Endpoint/model в настройках, ключ в OS keyring.

## Alternatives
Жёсткая привязка к SDK одного провайдера.

## Consequences
JSON mode обязателен для generation/critic. Ollama использует совместимый /v1. Reranker/transcription/vision/storage adapters добавляются при реализации этих модулей.
