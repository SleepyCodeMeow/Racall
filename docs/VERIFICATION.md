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


## 0.1 Beta release preparation

- Public source repository: https://github.com/SleepyCodeMeow/Racall.
- Version metadata aligned to `0.1.0-beta.1` (`0.1.0b1` for Python).
- English README with GitHub-hosted navigation, separate Russian README, getting-started guide, changelog, release process and issue templates.
- 26 Python tests pass locally, including transient Windows metadata read/write conflicts; lint, TypeScript and 208-key localization checks pass.
- npm audit reported zero known vulnerabilities at preparation time.
- Packaged Windows app: notebook creation, Markdown import/search, exact citation, note editing/preview, MCP configuration, Ollama settings, English/Russian switching, full restart and installer-language seeding passed. Frozen backend PDF page provenance/original download/authentication passed.
- README rendered on the live GitHub page; all embedded images loaded. Relative README/documentation links resolve.
- Clean GitHub Windows runner exposed a transient metadata read conflict during import. Added bounded retries for Windows sharing/access conflicts and regression coverage; real permission failures still propagate.
- CI is configured to test/package four OS/architecture combinations before publishing a complete prerelease. See Actions for the outcome; configuration alone does not establish success.
- Manual clean install/uninstall on every OS, signing/notarization, and real cloud/Ollama model evaluation remain outstanding. Beta documentation states these limits.

Local rebuilt Windows beta SHA-256: `23f3b79f5c287f18f2ae4f6cc087d20e38a403a7dbe64b83c3384d87a39ba485`. CI artifacts are built separately; use the release-attached checksums for downloaded packages.

All four native CI jobs passed on commit `27330bd`: Windows x64, Linux x64, macOS arm64 and macOS x64, including packaged app, language restart and frozen PDF tests. Evidence: https://github.com/SleepyCodeMeow/Racall/actions/runs/36022117952.


### Published prerelease

`v0.1.0-beta.1` is public: https://github.com/SleepyCodeMeow/Racall/releases/tag/v0.1.0-beta.1.
All four native jobs passed again in build run `36023413535`. Publication initially stopped on Linux architecture filename conventions, then on Ubuntu's older Python lacking `hashlib.file_digest`; both publication-only issues were corrected on main. Recovery workflow `36024957384` verifies the immutable tag commit and all four passing native jobs before reusing their artifacts. No application binaries were substituted or retagged.
Seven packages plus `SHA256SUMS.txt` are attached. The downloaded checksum file and all seven entries match GitHub's server-side asset digests. Windows release artifact SHA-256: `5b78d634948e5f2e87fbb238457186c25a66cfa3c621bc6b597e14ec10df06c1`.


## 0.2 development — first persistence slice, 26 September 2026

This is development evidence, not a published 0.2 release or completion of the entire roadmap.

- 31 Python tests passed: persisted chats/citation snapshots, request replay, interrupted/failed turns, notebook boundaries, legacy Markdown metadata, autosave revisions, lost-response retry, I/O failure recovery and invalid-path rejection without replacing an existing draft.
- Ruff, TypeScript, 240-key EN/RU localization checks and release metadata validation passed. Production frontend and frozen Python service builds passed.
- Windows unpacked application passed `smoke-persistence.cjs`: full app/service restart, restored answer and citation, chat rename/selection, no extra model call on reopen, autosave without pressing Save, newer typing while an older acknowledgement is delayed, cancelling close keeps the service alive, external edits remain intact, later conflict edits update the draft, recovered draft saved as a copy and notebook isolation.
- Existing packaged desktop and language checks passed, including import/search/exact citation, note preview, MCP settings, provider settings, language restart, unchanged user Markdown, installer locale seed and manual preference preservation. JavaScript errors: zero.
- Visually inspected the restored conversation and note conflict view at desktop width. No redesign is claimed.
- The deterministic local model stub establishes persistence behavior, not real cloud/Ollama answer quality. 0.2 macOS/Linux/native installer checks, real-model evaluation and signing/notarization remain separate checks.

Local evidence (ignored generated files):

- `test-results/persistence-1790427093230/result.json`
- `test-results/desktop-1790427130552/result.json`
- `test-results/languages-1790427164391/result.json`

The published 0.1 tag and binaries are unchanged. See [0.2 development notes](releases/0.2.0-beta.1.md) and the [code map](CODE_MAP.md).


## 0.2 candidate engineering — 26 September 2026

- Notebook lifecycle and versioned source maintenance are implemented, with regression coverage for active-operation guards, preserved originals/citations, failed promotion rollback, legacy files, cache repair and isolated parser deadlines/memory limits.
- The existing first-slice CI passed all four platforms on `8ad858d` (run `36243565583`). This result does not establish success of the newer candidate; its extended native/installer CI must pass separately.
- Local Windows candidate maintenance passed: `test-results/maintenance-1790429317240/result.json`.
- Full Windows packaged checks passed: desktop `desktop-1790429567265`, languages `languages-1790429601202`, persistence `persistence-1790429632027`, maintenance `maintenance-1790429673862`. Frozen PDF import/provenance/original/auth checks also passed. These checks use synthetic data and deterministic model responses.
- A later backend regression run exposed a transient CRT EACCES file read without a `winerror` code. The read/write retry predicate now recognizes that Windows-only form, with bounded retries; document creation also uses the reader's store lock. A focused regression covers it. Permanent permission failures still propagate.
- The model evaluation fixture validates offline: four synthetic sources, ten EN/RU questions. Real-provider execution is deferred to the owner by explicit choice.
- Publication is on hold. No 0.2 release tag or GitHub Release has been created. See [release checklist](RELEASE_02_CHECKLIST.md).


### Final 0.2 candidate code: `7a73788`

- 44 backend regression tests passed; Ruff, TypeScript, release metadata checks and 270-key EN/RU checks passed. Production web and frozen backend builds passed.
- An interrupted staged original is rewritten atomically before becoming active; its SHA-256 must match the declared source version. A regression test covers a partial pre-existing staged file.
- The final local Windows package passed the full suite again: `desktop-1790430514014`, `languages-1790430548183`, `persistence-1790430580763`, `maintenance-1790430621341`. Frozen backend PDF provenance, original download and authentication checks passed.
- The owner-facing model evaluation guide now has [Russian instructions](MODEL_EVALUATION.ru.md), with ten questions, expected answers and the old/new source-version check. No real-model requests were made.

- All four native jobs passed on code commit `7a73788d29ce15bcaf7834ed732ffca625050746`: [run 36246042420](https://github.com/SleepyCodeMeow/Racall/actions/runs/36246042420). Each ran backend/static checks, production builds, all packaged smoke scenarios and the frozen PDF check.
- Installer checks passed on disposable native hosts: Windows NSIS install/launch/uninstall with a preserved knowledge sentinel; macOS arm64 and x64 DMG mount/copy/launch; Linux Debian install/launch/remove with preserved data, plus extracted AppImage launch. FUSE mounting, interactive OS security prompts and signing/notarization are not covered.
- The publication job was skipped. The candidate remains on hold; the 0.1 release/tag is unchanged. Owner real-model acceptance and hands-on review remain open by explicit choice. Later documentation-only commits do not change the code validated above.


### Light installer and citation-label follow-up

All four native jobs passed on `4eeb07ea2207cf2711bd881d5d5469cbf049665d`: [run 36248218995](https://github.com/SleepyCodeMeow/Racall/actions/runs/36248218995). This supersedes the earlier code candidate for packaged/installer checks and includes 45 backend tests. Publication was skipped.

The Windows installer now uses a white header with the existing mascot, a white finish-page sidebar and Segoe UI. A real interactive screenshot could not be inspected because the Computer Use runtime failed to initialize (`apply deny-read ACLs`); the separate local HTML illustration is explicitly labelled as a mockup, not an EXE screenshot. Native automated install/uninstall checks passed.

The first real Ollama run did not pass acceptance; see [the model report](OLLAMA_EVALUATION_2026-09-26.md). The attempted real-model recheck after shortening evidence labels was interrupted and has no saved verdict. No additional model inference is being started after the owner reported loss of display and reboot. Owner hands-on review and stable-provider acceptance remain open.
