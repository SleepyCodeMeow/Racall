# Citation provenance

Status: accepted for 0.1 desktop preview

## Context
Модель может придумывать ссылки.

## Decision
Evidence содержит source/version/hash, page/section/offsets. Сервис присваивает номера только реально возвращённым chunk IDs. UI открывает исходный блок и выделяет span.

## Alternatives
Разбирать свободный текст с [1].

## Consequences
Проверяемая трассировка; critic отдельно оценивает поддержку утверждения, но не даёт математической гарантии истинности.
