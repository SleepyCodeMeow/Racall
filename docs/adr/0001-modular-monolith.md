# Модульный монолит

Status: accepted for 0.1 desktop preview

## Context
Нужен переносимый desktop без сетки сервисов.

## Decision
Electron запускает один FastAPI sidecar. Storage, ingestion, providers, knowledge и MCP имеют отдельные модули.

## Alternatives
Микросервисы; всё в Electron.

## Consequences
Простая установка. Тяжёлые парсеры пока выполняются в thread worker, изоляция процессов запланирована.
