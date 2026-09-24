# OpenNotebook — техническая спецификация

> Документ предназначен для передачи coding-агенту (Codex, Claude Code, OpenCode и т. п.) как исходная спецификация. Перед реализацией агент обязан проверять актуальные API и версии зависимостей.

## 1. Цель

Создать open-source платформу знаний, объединяющую идеи **NotebookLM + Obsidian + MCP**, но не привязанную к Google, одной LLM или одному агенту.

Это не «чат с PDF», а универсальный **knowledge layer**:

```text
                    OpenNotebook
                 Knowledge Platform
                        │
                  MCP + REST API
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
    ChatGPT           Codex          Claude Code
       │                │                │
       └────────────────┼────────────────┘
                        ▼
                     OpenCode
```

Основные свойства:
- Notebook/Project как пространство знаний.
- Sources: PDF, DOCX, PPTX, Markdown, URL, сайты, YouTube, изображения, аудио, видео, GitHub.
- Grounded Q&A с точными citations.
- Deep Research.
- Notes, Artifacts и Research Memory.
- Obsidian-compatible Markdown.
- MCP для внешних агентов.
- REST API для UI/интеграций.
- Self-hosting.
- Возможность заменить LLM, embeddings, reranker и vector store.

Главный принцип: **knowledge-first, agent-second**. LLM не является владельцем знаний.

## 2. Reference-проекты

### SurfSense
https://github.com/MODSetter/SurfSense

Использовать как reference для NotebookLM-подобного UX, ingestion, RAG, citations, connectors, reports, self-hosting и MCP. Не делать слепой fork. Перед реализацией крупного блока смотреть актуальную реализацию SurfSense и брать только подходящие идеи.

### Hands-On-AI-Engineering
https://github.com/Sumanth077/Hands-On-AI-Engineering

Использовать как cookbook:
- `ai_agents/research_assistant_with_memory`: Planner → Research → Writer → Critic, persistent memory, grounding, evaluation, observability.
- `multimodal/multimodal_rag`: text/URL/PDF/image/audio/video.
- Hybrid RAG.
- GraphRAG Knowledge System.
- YouTube Transcript RAG.
- Grounded Document Agent.
- GitHub Intelligence Agent.

### MCP
https://modelcontextprotocol.io/

MCP проектировать с первого дня как главный внешний интерфейс AI-клиентов.

### Obsidian
Использовать модель обычных Markdown-файлов и wikilinks. Obsidian не является обязательной зависимостью.

## 3. Source of truth

Постоянные пользовательские данные:
- оригинальные файлы;
- Markdown notes;
- metadata;
- relationships;
- notebook configuration.

Восстанавливаемые данные:
- chunks;
- embeddings;
- BM25/full-text index;
- graph index;
- previews/cache.

При потере индексов должна существовать полная операция `reindex`.

## 4. Стек

### Frontend
Next.js, TypeScript, React, Tailwind CSS, shadcn/ui, TanStack Query, PDF.js, CodeMirror/Monaco, React Flow.

### Backend
Python, FastAPI, Pydantic, SQLAlchemy, Alembic.

### Data
- PostgreSQL.
- pgvector для MVP.
- PostgreSQL FTS для keyword retrieval.
- Redis + Celery/Dramatiq/Arq для jobs.
- Local filesystem + S3/MinIO abstraction.

Не вводить отдельную vector DB в MVP без необходимости. Позже adapters для Qdrant/Weaviate/Milvus/OpenSearch.

### Provider abstractions

```python
class LLMProvider: ...
class EmbeddingProvider: ...
class RerankerProvider: ...
class TranscriptionProvider: ...
class VisionProvider: ...
class StorageProvider: ...
class VectorStoreProvider: ...
```

Provider-specific код не размазывать по domain logic.

## 5. Data model

```text
User
Workspace
Notebook
Source
SourceVersion
Document
DocumentSection
Chunk
Note
Artifact
Citation
ResearchSession
ResearchMemory
Tag
Relation
AgentConnection
Job
```

`Source.type`: `pdf, docx, pptx, markdown, text, url, website, youtube, image, audio, video, github_repository, github_file`.

Chunk хранит `source_id`, version, section, text, chunk index, page, offsets, timestamps, repository/path/commit/line range, metadata и embedding.

## 6. Obsidian-compatible storage

```text
notebooks/
└── livekit-platform/
    ├── notebook.yaml
    ├── sources/
    │   ├── documents/
    │   ├── web/
    │   ├── youtube/
    │   ├── github/
    │   └── media/
    ├── notes/
    ├── research/
    ├── artifacts/
    └── attachments/
```

Notes поддерживают YAML frontmatter и `[[wikilinks]]`. Пользователь может открыть папку в Obsidian, VS Code или Git. OpenNotebook работает без Obsidian.

## 7. Ingestion Engine

MVP: PDF, TXT, Markdown, DOCX, URL, YouTube transcript, GitHub repository.

V2: PPTX, images, audio, video, crawler, cloud drives.

```text
Add Source
 ↓
Source Loader
 ↓
Parser
 ↓
NormalizedDocument
 ↓
Structure Extraction
 ↓
Semantic/Token-aware Chunking
 ↓
Metadata enrichment
 ├─ Embeddings
 ├─ Full-text index
 └─ optional graph extraction
```

Все parsers выдают единый NormalizedDocument. Element types: heading, paragraph, list, table, code, quote, image, figure, caption, transcript.

Не использовать production parsing вида `extract all text -> split every N chars`. Сохранять headings, pages, tables, code, captions, timestamps и repository paths.

## 8. Retrieval Engine

```text
Query
 ├─ Semantic/vector search
 └─ Keyword/full-text search
        ↓
   Rank Fusion (RRF)
        ↓
      Reranker
        ↓
    Evidence Pack
```

Позже добавить Knowledge Graph. Retrieval возвращает Evidence objects с provenance.

## 9. Citation Engine

Citation является first-class entity. Модель не должна сама выдумывать `[1]`.

Citation хранит source/version/chunk, page/section, timestamp, repository path, commit/line range и quote span.

- PDF: page + passage.
- Web: URL + passage.
- YouTube: timestamp.
- GitHub: file + commit + lines.

UI по клику открывает первоисточник на релевантном месте.

## 10. Research Engine

```text
Question
 ↓
Planner
 ├─ subquery 1
 ├─ subquery 2
 └─ subquery N
 ↓
Research: Sources + Memory + optional Web
 ↓
Evidence
 ↓
Writer
 ↓
Critic / Grounding Validator
 ├─ fail → targeted research revision
 └─ pass → Result
```

Режимы: `Only my sources` и `My sources + web`. Каждый research step, retrieval и tool call логируется.

## 11. Research Memory

Не путать с chat history. Не сохранять каждый ответ LLM как истину.

Сохранять только findings, прошедшие grounding/validation:

```text
finding
notebook_id
supporting_citations[]
confidence
originating_session
created_at
status
```

Pipeline: `Research result → Grounding validation → accepted? → Research Memory`.

## 12. Notes и Artifacts

Разделять:
- raw sources;
- user notes;
- research memory;
- generated artifacts.

AI может создавать draft, предлагать edit, добавлять citations и связи. Пользовательские notes остаются Markdown.

Artifacts: report, comparison, FAQ, study guide, timeline, research brief, migration plan.

## 13. MCP Server

### Read tools

```text
list_notebooks()
get_notebook()
list_sources()
search_sources()
read_source()
read_section()
get_chunk()
search_notes()
read_note()
search_research_memory()
get_citation()
```

### Write tools

```text
create_note()
update_note()
create_artifact()
update_artifact()
add_tag()
create_relation()
save_research_finding()
```

### Source tools

```text
add_url()
add_youtube()
add_github_repository()
refresh_source()
reindex_source()
```

Delete/destructive tools требуют повышенных permissions/confirmation.

Remote MCP должен поддерживать нормальную user authorization. Permissions должны быть notebook-scoped:

```text
ChatGPT connection
Notebook: LiveKit
[x] read sources
[x] read notes
[ ] edit notes
[ ] add sources
[ ] delete
```

## 14. AI-клиенты

UI:

```text
Connect AI
├─ ChatGPT
├─ Codex
├─ Claude Code
├─ OpenCode
├─ Generic MCP Client
└─ Built-in Agent
```

`Agent runtime` и `Model` не одно и то же.

Для browser ChatGPT основная архитектура: remote MCP/app integration + OAuth, а не browser extension.

```text
ChatGPT browser
 ↓ HTTPS/MCP
OpenNotebook MCP Gateway
 ↓ authorization
Knowledge Service
```

Встроенный chat также использует тот же Knowledge API.

## 15. GitHub source

Repository является source type первого класса.

При ingestion:
1. сохранить repo metadata;
2. branch + commit;
3. file tree;
4. исключить `.git`, binaries, build, cache, `node_modules`;
5. распарсить README/docs/code;
6. сохранить path + commit + line ranges;
7. индексировать;
8. поддержать refresh.

Citation:

```text
src/rtc/reconnect.ts:L84-L147 @ abc123
```

Добавить secret detection. Credential-файлы не индексировать автоматически.

## 16. Multimodal

Image: OCR + vision description + original.

Audio: transcript + timestamps + original.

Video: transcript + timestamps + chapters/scenes + optional keyframes + original.

Retrieval может идти по текстовому representation, но multimodal model при необходимости получает оригинальный media object.

## 17. Knowledge Graph

Не включать GraphRAG в критический путь MVP.

V2/V3: entities, concepts, files, projects, technologies, relations. Graph должен улучшать retrieval/navigation, а не быть декоративной паутиной.

## 18. Security

Обязательно:
- workspace isolation;
- notebook-scoped authorization;
- encrypted secrets;
- OAuth/short-lived tokens;
- audit log;
- MCP tool permissions;
- SSRF protection для URL ingestion;
- file size/type limits;
- archive-bomb protection;
- HTML sanitization;
- prompt-injection-aware retrieval;
- secret detection для GitHub.

**Retrieved document является untrusted data.** Инструкция внутри PDF/сайта не должна превращаться в system/tool instruction.

## 19. Observability и Evaluation

Логировать ingestion jobs, parser, chunks, embedding duration, retrieval queries, evidence, reranker scores, model/tool calls, citation mapping, research revisions, errors, token/cost usage.

Создать eval dataset и метрики:
- retrieval recall;
- citation correctness;
- groundedness;
- completeness;
- hallucination rate;
- latency;
- cost.

Изменение prompt/model/retrieval считается улучшением после eval, а не после одного красивого demo.

## 20. UI

```text
┌──────────────┬───────────────────────┬────────────────┐
│ Navigation   │ Main Workspace        │ Source Detail  │
│ Sources      │ Chat/Note/Research    │ Citation       │
│ Notes        │ Report/Artifact       │ Preview        │
│ Research     │                       │                │
└──────────────┴───────────────────────┴────────────────┘
```

Notebook page: Sources, Chat, Notes, Research, Artifacts, Graph, Settings.

Source viewer обязан позволять перейти от citation к точному месту источника.

## 21. Backend boundaries

Логические модули:

```text
Auth
Notebook
Source
Ingestion
Document
Retrieval
Citation
Research
Memory
Notes
Artifacts
MCP Gateway
Provider
Jobs
```

На старте использовать **modular monolith**, не микросервисы. Сохранять четкие module boundaries, чтобы тяжелые workers можно было вынести позже.

## 22. План разработки

### Phase 0 — Foundation
- monorepo;
- Docker Compose;
- Next.js frontend;
- FastAPI backend;
- PostgreSQL + pgvector;
- Redis;
- migrations;
- authentication;
- tests;
- CI;
- `.env.example`;
- structured logging.

### Phase 1 — Notebook + Markdown
- Workspace/Notebook CRUD;
- файловая структура Notebook;
- Markdown notes;
- YAML frontmatter;
- Obsidian wikilinks;
- source list;
- базовый three-pane UI.

### Phase 2 — Ingestion
- PDF;
- Markdown/TXT;
- DOCX;
- URL;
- NormalizedDocument;
- background jobs;
- semantic chunking;
- embeddings;
- FTS;
- source version/checksum.

### Phase 3 — Grounded Q&A
- hybrid retrieval;
- rank fusion;
- reranker;
- Evidence objects;
- answer generation;
- Citation Engine;
- source viewer;
- evaluation tests.

**После Phase 3 уже должен существовать полезный самостоятельный продукт.**

### Phase 4 — MCP
- MCP server;
- read tools;
- authorization;
- notebook permissions;
- Generic MCP documentation;
- инструкции подключения ChatGPT/Codex/Claude Code/OpenCode;
- write tools только после стабилизации permissions.

### Phase 5 — Research
- Planner;
- parallel subqueries;
- Research worker;
- Writer;
- Critic/Grounding Validator;
- targeted revision loop;
- Research Memory;
- research report;
- observability.

### Phase 6 — GitHub + YouTube
- GitHub ingestion;
- commit/path/line citations;
- repo refresh;
- YouTube transcript;
- timestamp citations.

### Phase 7 — Multimodal
- images;
- OCR;
- audio;
- video;
- multimodal retrieval;
- original media handoff.

### Phase 8 — Advanced
- Knowledge Graph/GraphRAG;
- cloud connectors;
- collaboration;
- plugin architecture;
- advanced artifacts.

## 23. Что НЕ делать в MVP

Не тратить первый релиз на:
- podcast generation;
- presentation generator;
- сложный GraphRAG;
- десятки cloud connectors;
- enterprise RBAC;
- мобильное приложение;
- десятки vector DB;
- fine-tuning;
- собственную LLM;
- декоративную multi-agent команду.

Сначала доказать основную цепочку:

```text
Source
→ Parse
→ Normalize
→ Index
→ Retrieve
→ Cite
→ Research
→ Expose through MCP
```

## 24. Definition of Done первого серьезного релиза

Пользователь должен уметь:

1. создать Notebook;
2. добавить PDF/MD/DOCX/URL;
3. видеть ingestion status;
4. задать вопрос;
5. получить grounded answer;
6. открыть каждую citation в первоисточнике;
7. создать Markdown note;
8. открыть notes как Obsidian-compatible vault;
9. подключить внешний MCP-клиент;
10. дать внешнему агенту поиск/чтение Notebook;
11. запустить Deep Research;
12. сохранить проверенный результат как artifact/research memory;
13. выполнить полный reindex без потери исходных знаний.

## 25. Тестовая стратегия

### Unit tests
- parsers;
- chunking;
- rank fusion;
- citation mapping;
- permission checks;
- Markdown/frontmatter.

### Integration tests
- upload → parse → index → retrieve;
- query → evidence → citation;
- MCP tool → authorization → knowledge service;
- reindex;
- source version refresh.

### Golden/eval tests
Создать небольшой фиксированный corpus с заранее известными ответами и source locations. Проверять не только текст ответа, но и правильность evidence/citations.

### Security tests
- malicious PDF prompt injection;
- SSRF URLs;
- path traversal;
- archive bomb;
- unauthorized notebook access;
- MCP write without permission;
- secret-containing repository.

## 26. Репозиторий

Предлагаемая структура:

```text
open-notebook/
├── apps/
│   ├── web/
│   └── api/
├── packages/
│   ├── domain/
│   ├── ingestion/
│   ├── retrieval/
│   ├── citations/
│   ├── research/
│   ├── providers/
│   └── mcp/
├── workers/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
├── docs/
├── docker/
├── docker-compose.yml
├── .env.example
└── README.md
```

Если Python и TypeScript находятся в одном monorepo, не пытаться искусственно делать один package manager для обоих миров. Держать ясные команды `make dev`, `make test`, `make lint`, `make reindex`.

## 27. Первая задача coding-агента

Перед написанием большого количества кода:

1. Изучить актуальный SurfSense.
2. Изучить перечисленные части Hands-On-AI-Engineering.
3. Проверить актуальную MCP specification/SDK.
4. Проверить актуальные возможности интеграции ChatGPT с remote MCP/apps.
5. Составить ADR по storage/retrieval/MCP/auth.
6. Создать минимальный vertical slice:

```text
Create Notebook
→ Upload one PDF
→ Parse
→ Chunk
→ Embed/index
→ Ask question
→ Retrieve
→ Answer
→ Click citation
```

7. Только после успешного vertical slice расширять source types и research.

Не начинать с десятков экранов UI и не писать весь backend заранее.

## 28. Архитектурные решения, которые нужно оформить ADR

Создать `/docs/adr/`:

```text
0001-modular-monolith.md
0002-postgres-pgvector.md
0003-markdown-source-of-truth.md
0004-normalized-document-format.md
0005-hybrid-retrieval.md
0006-citation-provenance.md
0007-mcp-boundary.md
0008-provider-abstraction.md
0009-research-memory.md
0010-security-trust-boundary.md
```

Каждый ADR: Context, Decision, Alternatives, Consequences.

## 29. UX-принцип

Пользователь должен понимать разницу между:

```text
Source       = первичный материал
Note         = собственная заметка пользователя
Research     = AI-исследование с evidence
Memory       = проверенный долговременный finding
Artifact     = созданный конечный материал
```

Не складывать всё в один бесконечный чат.

## 30. Ключевая продуктовая идея

OpenNotebook не должен конкурировать с ChatGPT, Claude или Codex как еще один AI-чат.

Он должен стать **независимым слоем знаний между пользователем и AI**:

```text
                 USER KNOWLEDGE
                       │
                 OpenNotebook
        ┌──────────────┼──────────────┐
        │              │              │
     Human UI        MCP API       REST API
        │              │              │
     Obsidian     AI Agents      Integrations
```

Пользователь может сегодня работать с ChatGPT, завтра с Claude Code, через год с другим агентом. Его документы, заметки, citations, research memory и структура Notebook остаются на месте.

Именно это отличает проект от обычного NotebookLM clone.

---

# 31. Финальное правило для coding-агента

При разработке всегда соблюдать приоритет:

1. **Correct provenance.**
2. **Reliable retrieval.**
3. **Correct citations.**
4. **User-owned knowledge.**
5. **Clean MCP/API boundary.**
6. **Security.**
7. **Evaluation/observability.**
8. Только затем дополнительные AI-функции и визуальные эффекты.

Если приходится выбирать между «более впечатляющим AI demo» и надежной трассировкой ответа до первоисточника, выбирать второе.

---

## Краткая формула проекта

> **OpenNotebook = NotebookLM-style research + Obsidian-compatible knowledge storage + universal MCP knowledge backend for any AI agent.**

Версия спецификации: 0.1  
Дата: 2026-09-24
