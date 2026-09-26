# Проверка первичных источников — 2026-09-24

- [SurfSense](https://github.com/MODSetter/SurfSense), [local architecture](https://github.com/MODSetter/SurfSense/blob/main/surfsense_local/README.md):
  изучена desktop-композиция Electron + Python sidecar, локальное хранение, queue lifecycle.
  Это reference, код не копировался и fork не выполнялся.
- [Research assistant cookbook](https://github.com/Sumanth077/Hands-On-AI-Engineering/tree/main/ai_agents/research_assistant_with_memory):
  изучены Planner/Research/Writer/Critic и ограниченное сохранение memory.
- [Multimodal reference](https://github.com/Sumanth077/Hands-On-AI-Engineering/tree/main/multimodal/multimodal_rag):
  оставлен для следующего этапа, мультимодальность не входит в desktop preview.
- [MCP Python SDK v1](https://py.sdk.modelcontextprotocol.io/v1/):
  зафиксирован mcp 1.30.0 с FastMCP; v2.2.0 уже доступен, миграция не смешана с первым slice.
- [OpenAI MCP auth](https://developers.openai.com/plugins/build/auth):
  remote integration требует самостоятельного auth gateway. Не выдаём stdio за browser integration.
- [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports):
  Next export обслуживается локальным FastAPI, runtime Node-сервер в установщике не нужен.
- [Electron Builder multi-platform](https://www.electron.build/multi-platform-build.html):
  backend собирается на целевой ОС/архитектуре; в CI отдельные native runner jobs.

Версии проверены через npm registry и pip index, конкретное дерево зафиксировано
в package-lock.json и uv.lock. Не утверждается, что референсы гарантируют качество
созданного здесь приложения: для этого существуют собственные тесты.

## Сравнение альтернатив — 2026-09-26

В [REFERENCE_PROJECTS.md](REFERENCE_PROJECTS.md) добавлен разбор Open Notebook, SurfSense и Open-NotebookLM: зафиксированные коммиты, изученные файлы, ограничения проверки и порядок применения идей в Racall. Выполнено чтение исходников; приложения не запускались, чужой код в Racall не переносился.
