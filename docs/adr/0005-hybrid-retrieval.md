# Hybrid retrieval

Status: accepted for 0.1 desktop preview

## Context
Поиск нужен и без настроенного провайдера.

## Decision
FTS5 BM25 всегда доступен. При embedding model — provider vectors, cosine, RRF. Модель и endpoint записываются с vector; несовместимые vectors не смешиваются.

## Alternatives
Только vector; отдельная vector DB.

## Consequences
Работает offline keyword mode. После смены embedding model нужен reindex. Reranker не реализован.
