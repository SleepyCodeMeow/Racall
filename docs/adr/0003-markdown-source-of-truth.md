# Файлы как источник истины

Status: accepted for 0.1 desktop preview

## Context
Индекс не должен владеть пользовательскими знаниями.

## Decision
Оригиналы, source.json, notebook.yaml, notes, artifacts, research и memory — файлы. SQLite можно перестроить из оригиналов.

## Alternatives
Хранить всё в БД.

## Consequences
Прозрачный backup. Внешние изменения notes читаются заново. Индекс не гарантирует атомарности с файлами; startup recovery исправляет неполный ingestion.
