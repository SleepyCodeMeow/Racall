# NormalizedDocument

Status: accepted for 0.1 desktop preview

## Context
Парсеры должны сохранять происхождение текста.

## Decision
Pydantic elements: тип, текст, страница, раздел, строки. Chunk хранит element index и offsets; границы основаны на блоках и словах.

## Alternatives
Фиксированные окна символов.

## Consequences
Точные quote spans. PDF tables/figures пока требуют более сильного parser; page/layout text не выдаётся за полноценный document understanding.
