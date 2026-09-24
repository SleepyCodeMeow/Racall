<p align="center">
  <img src="assets/brand/raccoon-logo-original.png" width="110" height="110" alt="Racall raccoon mascot" />
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/wordmark-dark.svg" />
    <img src="assets/brand/wordmark-light.svg" width="236" height="110" alt="Racall" />
  </picture>
</p>

<p align="center"><strong>Your notes. Your sources. Connected.</strong></p>
<p align="center">An open-source workspace for connected notes, cited answers, and research with the AI you choose.</p>
<p align="center"><a href="README.md">English</a> · Русский</p>
<p align="center"><a href="docs/README.md">Документация</a> · <a href="https://github.com/SleepyCodeMeow/Racall/releases">Скачать</a> · <a href="#установка">Установка</a> · <a href="#что-работает">Возможности</a> · <a href="docs/ROADMAP.md">План развития</a> · <a href="#разработка">Разработка</a></p>

<p align="center"><img src="assets/brand/racall-desktop-preview.png" alt="Racall: диалог по источникам, заметки и исследования" width="1120" /></p>

# Racall

Открытое приложение для связанных заметок, ответов с цитатами и исследований с выбранным вами AI.
Имя объединяет **raccoon** (енот) и **recall** (вспоминать).

**0.1 Beta**: рабочее ядро спецификации, но не весь план Phase 0–8.
На скриншоте — работающий интерфейс с демонстрационными материалами; цветная подложка добавлена только для оформления README.
Рамка и системные кнопки окна зависят от ОС. Мобильное приложение пока не выпущено.

## Установка

- Windows x64: [скачать установщик EXE](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.1.0-beta.1/Racall-0.1.0-beta.1-win-x64.exe) (NSIS).
- macOS: [DMG для Apple Silicon](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.1.0-beta.1/Racall-0.1.0-beta.1-mac-arm64.dmg) / [DMG для Intel](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.1.0-beta.1/Racall-0.1.0-beta.1-mac-x64.dmg).
- Linux x64: [AppImage](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.1.0-beta.1/Racall-0.1.0-beta.1-linux-x86_64.AppImage) / [DEB](https://github.com/SleepyCodeMeow/Racall/releases/download/v0.1.0-beta.1/Racall-0.1.0-beta.1-linux-amd64.deb).
- Пользователю не нужны Python, Node.js, Docker, PostgreSQL или Redis.
- Сборки беты не подписаны. macOS notarization и Windows code signing требуют сертификатов владельца проекта.
- Все четыре сборки прошли автоматические проверки запуска и основных сценариев. Ручная проверка полной установки/удаления на каждой ОС пока не выполнена.

Откройте приложение → создайте блокнот → «Источники» → импортируйте файл.
Панель источников можно свернуть; нажатие на цитату автоматически открывает нужный фрагмент.
Кнопка «+» у строки вопроса открывает действия с материалами, заметками и исследованиями.
В **Настройки** укажите URL OpenAI-совместимого API, ключ и модель с JSON mode.
Для Ollama выберите соответствующую вкладку и введите имя уже установленной модели.
Приложение не устанавливает Ollama и не скачивает веса автоматически.

Без модели работают импорт, просмотр, Markdown-заметки и текстовый поиск.
Embeddings необязательны: укажите модель embeddings и перестройте индекс.
При облачных embeddings весь извлечённый текст передаётся выбранному провайдеру;
при ответах и исследованиях передаются найденные фрагменты.

## Язык интерфейса

По умолчанию используется **English**. Windows-установщик предлагает **English / Русский**;
выбор применяется к шагам установки и первому запуску Racall.
В приложении: **Settings → Interface language** / **Настройки → Язык интерфейса**.
Переключение применяется сразу и сохраняется после перезапуска. Обновление не заменяет
уже сохранённый выбор. Заметки, документы и язык вопросов при переключении не меняются.

## Что работает

- Блокноты и переносимые файлы знаний.
- PDF с текстовым слоем, UTF-8 TXT/Markdown, DOCX, публичные HTML URL.
- Очередь импорта с состояниями, восстановлением незавершённых импортов после перезапуска.
- Структурные блоки, страницы PDF, заголовки Markdown/DOCX, таблицы DOCX, точные offsets цитат.
- SQLite FTS5 + необязательные provider embeddings + cosine + reciprocal rank fusion.
- Ответы из evidence, проверка допустимых citation IDs и отдельная проверка утверждений моделью.
- Просмотр подсвеченного фрагмента; открытие исходного PDF на странице.
- Markdown с frontmatter, предпросмотром и wikilinks в интерфейсе.
- Исследования по своим источникам: план, поиск, writer, critic, повторный поиск при отклонении.
- Сохранение прошедшего проверку результата в artifact и research memory.
- Read-only MCP по stdio, ограниченный одним блокнотом; готовая конфигурация в «Подключить AI».
- Полный reindex, оригиналы и заметки при этом не изменяются.
- Ключи в системном keyring; API только на loopback с новым токеном при каждом запуске.

AI-проверка не является гарантией истинности вывода. Для важных утверждений проверяйте первоисточник.

## Данные

По умолчанию Electron хранит данные в своей пользовательской папке:
Windows — `%APPDATA%/OpenNotebook/knowledge` (фактический путь показан в настройках);
macOS — `~/Library/Application Support/OpenNotebook/knowledge`;
Linux — `~/.config/OpenNotebook/knowledge`.
Папка `OpenNotebook` сохранена от прежнего рабочего имени, чтобы переименование в Racall не меняло расположение существующих данных. Кнопка «Открыть папку» показывает точное расположение.

```text
knowledge/
  notebooks/<uuid>/
    notebook.yaml
    sources/<uuid>/
      source.json
      original.pdf | original.md | original.txt | original.docx
      document.json
    notes/*.md
    artifacts/*.md
    research/*.json
    memory/*.json
    attachments/
  index.sqlite3       # восстанавливаемый индекс
  preferences.json    # выбранный язык интерфейса
  settings.json       # без API-ключей
  audit.jsonl         # журнал событий без текстов документов/ключей
  backend.log
```

Для резервной копии закройте приложение и скопируйте папку knowledge.
Секреты keyring не входят в копию. После восстановления укажите ключ заново.
Индекс можно перестроить кнопкой внизу панели источников.
Заметки можно редактировать внешним редактором, затем вернуться в приложение.
Откройте папку конкретного блокнота как vault в Obsidian.

## Разработка

Требуются Node.js 24, Python 3.12 и uv.

```sh
npm ci
uv sync --frozen
npm run dev
npm test
npm run typecheck
npm run test:i18n
npm run build
npm run start
npm run dist
```

`dev` запускает Next.js и Electron, который управляет Python-службой.
`start` использует уже экспортированный frontend.
Для headless проверки окна Electron: `node scripts/smoke-desktop.cjs`.
Для проверки распакованного EXE задайте `OPENNOTEBOOK_TEST_EXE`.
Linux CI для такого теста требует Xvfb.

API отдельно:
```sh
# Сначала задайте OPENNOTEBOOK_SESSION_TOKEN (не менее 24 случайных символов).
uv run python apps/api/run.py --data-dir .local-data --port 8765 --web-dir apps/web/out
```
REST требует `Authorization: Bearer <token>`. Не открывайте порт во внешнюю сеть.
Для браузерной отладки токен можно передать один раз в URL fragment `#token=...`;
он очищается из адресной строки и сохраняется только в sessionStorage.

## MCP

В интерфейсе выберите блокнот → «Подключить AI» → скопируйте JSON.
Процесс запускается с `--mcp --data-dir <path> --notebook <uuid>`.
Он предоставляет только выбранный блокнот, не принимает notebook ID от модели
и не имеет write/delete tools. stdout зарезервирован под MCP; логи идут в stderr.
MCP SDK v1.30.0 намеренно зафиксирован, переход на v2 — отдельная миграция.

Браузерный ChatGPT требует remote MCP/OAuth; этот шлюз **ещё не реализован**.
Источник: [официальная документация OpenAI по авторизации MCP](https://developers.openai.com/plugins/build/auth).

## Границы беты

Серверный PostgreSQL/pgvector, Redis, SQLAlchemy/Alembic, OAuth и совместная работа,
MCP write tools, GitHub/YouTube, OCR, медиа, GraphRAG и cloud connectors ещё не реализованы.
Отдельного reranker пока нет. PDF parsing сохраняет страницы и layout-текст, но не
реконструирует сложные таблицы/рисунки. Поиск в больших коллекциях ограничен линейным
сравнением vectors в памяти. Research пока синхронный: закрытие приложения его прерывает.
Диалог в UI не сохраняется как история; важный результат сохраняйте в заметки/отчёт.
Нет удаления, редактирования блокнота и версионированного refresh источников.
Нет заявления о выполнении полного Definition of Done из исходной спецификации.

План и архитектурные решения: [docs/ROADMAP.md](docs/ROADMAP.md), [docs/adr](docs/adr).
