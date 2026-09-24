# MCP boundary

Status: accepted for 0.1 desktop preview

## Context
Локальный доступ и remote authorization — разные задачи.

## Decision
Read-only stdio, один notebook на процесс, ID выбирает пользователь в конфигурации. REST и MCP используют Knowledge/Store. MCP v1.30.0 закреплён.

## Alternatives
Неавторизованный HTTP; browser extension.

## Consequences
Работает с локальными stdio-клиентами. Remote ChatGPT/OAuth и write scopes — отдельный этап.
