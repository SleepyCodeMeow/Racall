# Проверка версии 0.1.0 — 2026-09-24

Среда: Windows 11 x64, Node 24.15.0, Python 3.12.10.

## Пройдено
- 20 unit/integration/security tests: PDF page/quote offsets, DOCX blocks/tables,
  chunk coverage, FTS/RRF, mock vector retrieval, model compatibility, notebook scope,
  REST bearer auth, CORS, path traversal, private DNS/SSRF, archive expansion,
  Markdown/frontmatter preservation, reindex recovery, critic/citation/memory gates.
- Настоящий MCP stdio handshake + list/search/read/scope, через Python SDK.
- Отдельно тот же MCP handshake выполнен с **упакованным backend EXE**.
- Frozen backend real HTTP: upload двухстраничного PDF, parse, FTS search,
  citation на странице 2, скачивание байт-в-байт исходника, отказ без авторизации.
- Упакованное окно Electron: создание блокнота, импорт MD, поиск, точный quote
  в source viewer, сохранение notes, Markdown/wiki preview, MCP config, Ollama settings.
- Next production static build, TypeScript typecheck, Ruff lint.
- npm audit: 0 vulnerabilities на момент установки.
- Собран NSIS Windows x64 EXE; app metadata и icon включены, подпись выключена явно.

Скриншоты/машинные результаты smoke tests лежат в test-results (не включены в поставку).
Из-за тайм-аута Playwright screenshot у скрытого packaged Electron окна захват
переведён на штатный Electron capturePage. Сам сценарий и DOM-проверки проходят.
Есть одно предупреждение о будущем переходе Starlette TestClient с httpx на httpx2.

## Не проверено / не выполнено
- Реальные облачные и Ollama LLM/embedding вызовы: ключ и рабочая модель не предоставлены.
  Тестовые embeddings, writer и critic не измеряют качество настоящей модели.
- macOS/Linux: конфигурация native CI создана, задания ещё не запускались.
- Полная установка/удаление на чистой Windows VM: проверялось приложение из win-unpacked.
- Code signing, Apple notarization и публичное распространение.
- Полная безопасность произвольных PDF: лимиты процесса parser ещё нужны.
- Полный Definition of Done исходной спецификации не достигнут: см. ROADMAP.

Preview подходит для локального знакомства и обратной связи, не для публичного
многопользовательского сервиса или заявления о завершении всей спецификации.

## Racall: обновление интерфейса 24 сентября 2026

- Светлая компоновка с боковой навигацией, центральным диалогом, меню действий и сворачиваемой панелью источников.
- Next production build и TypeScript прошли после изменений.
- Electron smoke прошёл в режиме разработки и на `release/win-unpacked/Racall.exe`: блокнот, импорт, поиск, открытие точной цитаты из скрытой панели, Markdown, MCP и настройки Ollama.
- Отдельный сценарий `scripts/capture-ui.cjs` использовал настоящий backend с изолированными демонстрационными документами. Проверены меню и Escape, раскрытие источников по цитате, сохранение заметки на ширине 390px, отсутствие горизонтальной прокрутки. Ошибок JavaScript не обнаружено.
- Выполнена визуальная проверка диалога, панели источников и узкого экрана; скриншот для README снят с реального frontend. Оранжевая подложка является только оформлением снимка.
- Новый установщик: `release/Racall-0.1.0-win-x64.exe`, 144180772 байта. SHA-256: `b3816e16ed6bd7c9215b02b9b0cfa0e386feae9d7a00e8f9ad6532c7d43e6635`.
- Оригинальный пользовательский PNG логотипа сохранён без изменений; иконки ОС конвертированы из него.
- Папка данных `OpenNotebook`, прежний appId и keyring namespace сохранены. Обновление установленной версии и полный install/uninstall на чистой машине не проверялись. Установщик не подписан.
- macOS/Linux и мобильное приложение не собирались в рамках этого обновления.

Артефакты: `test-results/desktop-1790261574141/result.json`, `test-results/racall-ui-1790261459560/result.json`.

## English / Русский — 24 сентября 2026

- 208 ключей перевода в общих каталогах EN/RU, типизированные UI-вызовы, одинаковые placeholders и корректные формы числа.
- Английский по умолчанию; язык меняется сразу в настройках и сохраняется в `preferences.json` независимо от порта backend. HTML lang также обновляется.
- NSIS содержит English и Russian, показывает выбор языка и передаёт его первому запуску через `resources/installer-language.json`. Существующая пользовательская настройка имеет приоритет при обновлении.
- Тот же customInstall macro скомпилирован и выполнен отдельно в изолированных каталогах: 1033 создаёт locale=en, 1049 создаёт locale=ru. Полная интерактивная установка/удаление на чистой VM по-прежнему не проверялась.
- 24 pytest-теста, Ruff, TypeScript и production frontend/backend build прошли. Проверены отказ неавторизованному доступу, неподдерживаемые значения, перезапуск и неизменность заметок/настроек провайдера.
- Каталоги, подстановки, склонения, сообщения сервиса и native seeding проверены `npm run test:i18n`.
- Electron language smoke проверяет English → Русский → полный перезапуск → English, неизменный Markdown, локализованную ошибку AI, выбор из установщика и сохранение ручного выбора.
- Найден и исправлен воспроизводимый Windows sharing conflict при atomic replace: ограниченные повторы для winerror 5/32/33, сохранение исходного файла при постоянном отказе, очистка временного файла. Два regression-теста прошли; снимок и импорт нескольких документов после исправления проходят.
- Визуально проверены Settings EN/RU и обновлён английский скриншот README.

Текущий EXE: `Racall-0.1.0-win-x64.exe`, 144123803 байта, SHA-256 `d2f7ba12a1054e14061a33dad18985df9e89229f3705c446aa4485cb44ffce30`. Подписи нет; macOS/Linux не собирались локально.

Финальная упакованная сборка: `test-results/languages-1790263205646/result.json` и `test-results/desktop-1790263237975/result.json` — passed, JavaScript errors: 0. Снимки EN/RU: `test-results/racall-ui-1790263080081`.
