# Desktop SQLite и будущий PostgreSQL

Status: accepted for 0.1 desktop preview

## Context
Спецификация предлагает PostgreSQL/pgvector; пользователь требует обычную установку.

## Decision
Desktop использует SQLite FTS5, JSON vectors и cosine search. PostgreSQL-профиль отложен и не объявлен реализованным.

## Alternatives
Встраивать PostgreSQL и Redis; требовать Docker.

## Consequences
Нет внешних служб. Vector retrieval линейный, рассчитан на небольшие личные коллекции. Переезд на pgvector потребует адаптера и миграций.
