# Trust boundary

Status: accepted for 0.1 desktop preview

## Context
Документы недоверенны; API локального приложения нельзя публиковать как сервер.

## Decision
Loopback bearer token per launch, sandboxed renderer, no Node, ограниченный IPC. OS keyring. URL DNS validation + pinned socket per redirect. File/type/zip limits. Structured evidence never promoted to system prompt.

## Alternatives
Доверять localhost без токена; plaintext keys.

## Consequences
Desktop single-user модель угроз. Нужны process resource limits для сложных PDF и OAuth/workspace isolation перед network deployment. Prompt instructions + critic уменьшают, но не устраняют prompt injection.
