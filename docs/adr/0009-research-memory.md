# Research memory

Status: accepted for 0.1 desktop preview

## Context
История чата не является проверенным знанием.

## Decision
Planner -> searches -> writer -> critic -> при отклонении повторный retrieval. Сохранение artifact/memory только при accepted claims и по действию пользователя.

## Alternatives
Автоматически запоминать каждый ответ.

## Consequences
Memory хранит полные evidence snapshots. Пока нет чтения memory built-in исследователем и отдельной confidence calibration; MCP может читать memory.
