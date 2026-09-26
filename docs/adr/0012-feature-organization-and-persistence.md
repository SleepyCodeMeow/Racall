# Feature organization and persistent workspace state

Status: accepted for the first 0.2 development slice, 2026-09-26.

## Decision

Group HTTP routers and interface components by feature. The API application is the composition root; request shapes, stateful operations and note file persistence have named modules. Keep existing Store methods as a thin compatibility facade so retrieval, MCP and callers do not need unrelated changes.

Chat transcripts are atomic JSON files under each notebook's `chats/` folder. They preserve questions, modes, statuses, complete answers and citation snapshots. Persist a running turn before a provider request, then save the outcome. Request IDs make replay safe; startup marks unfinished turns interrupted and never silently calls a provider again. Deleted chats move to `trash/chats/`; no restore UI is included yet.

Notes stay ordinary Markdown. The frontend serializes autosaves and retains newer keystrokes when an older request finishes. A SHA-256 revision detects edits made since a note was loaded. A recovery draft is written under `drafts/` before attempting the Markdown save. A conflict returns HTTP 409, retaining both the external file and draft. Users can save a copy or explicitly discard the draft and reload. Identical retries after a lost response return the existing file without rewriting metadata.

## Reference adaptation

The chat-persistence reference is Open Notebook's [chat graph at `3127f14ea9db`](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/open_notebook/graphs/chat.py), inspected in the [reference review](../REFERENCE_PROJECTS.md). Racall adopts notebook-scoped persisted transcripts and explicit interrupted states using portable atomic JSON. No upstream code, graph framework or checkpointing dependency was copied. Acceptance checks are restart without another model call, exact saved citation content and notebook isolation.

## Compatibility and limits

No destructive migration or database upgrade is required for 0.1 notebooks; new folders are created lazily. The retrieval index remains disposable. Back up the whole knowledge directory with the app closed, including chats and drafts. These files contain user content and are not encrypted by this change.

Autosave starts after a short typing pause. Changes not yet received by the service can still be lost in an abrupt process/OS failure; the editor warns on normal close while dirty. Revision checks detect previously completed external edits, but do not create a filesystem transaction with arbitrary external editors. Avoid simultaneous writes from multiple applications.

Persisted history is not conversational model memory: each answer still retrieves evidence for the current question. Follow-up question resolution, durable research jobs, source refresh/version browsing and thread-trash restoration are separate work.

## Validation

API checks cover legacy Markdown, metadata preservation, restart, lost-response retries, interrupted provider calls, notebook isolation, write errors and conflicts. Desktop checks use a local deterministic model stub, change backend ports across app restarts and exercise delayed saves. Native release checks remain required before publishing 0.2.
