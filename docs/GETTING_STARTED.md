# Getting started

[Documentation](README.md) · [Download releases](https://github.com/SleepyCodeMeow/Racall/releases)

## Install

**0.3 Beta** has separate x64 and ARM64 downloads for Windows, macOS and Linux.
Choose the package matching your operating system and processor: Windows uses an
EXE installer, macOS a DMG/ZIP, and Linux a DEB/AppImage. The [download table](../README.md#-get-started)
links to every package. Python, Node.js and Docker are not required to run them.

The Windows installer is unsigned and macOS packages are not signed/notarized.
Use the checksums attached to the release to verify your download. There is no
automatic updater; close Racall, back up your knowledge folder and install the
new version over the previous one. Existing data and language preferences are retained.

## First notebook

Create a notebook, open Sources and import PDF (with a text layer), UTF-8 TXT/Markdown or DOCX. You can also import a public HTML URL. Files are limited to 25 MB. Wait for the source to become ready, then choose Search and enter a phrase from the document. Open a result to inspect its exact passage.

Notes use Markdown. Edits autosave after a typing pause; wait for Saved before closing. If a file changed outside Racall, review the recovered draft and save a copy or reload the file. Frontmatter and wikilinks are supported. A notebook's folder can be opened in Obsidian; Racall is not an Obsidian plugin. Earlier 0.1 builds require explicit saving.

## Chat history

Use the chat selector to reopen a conversation, or New chat to start another one.
Questions, answers and citation snapshots survive a restart. The active thread
supplies bounded conversation history for follow-up questions; other chats are
not included. Earlier model answers help resolve context but do not become factual
evidence. Rename changes the title; Delete moves the transcript into the notebook's
`trash/chats` folder. There is no chat trash restore interface yet. Interrupted
requests are marked and are not automatically sent again.

## Context and Studio

Use **Context** in Chat, Research or Studio to select ready sources and saved notes.
An empty selection stays empty; unsaved note drafts are not included. Note citations
retain the revision used for that answer, and a reopened chat restores its selection.

Studio creates a summary, study guide or review questions with answers. Research
and Studio show generation stages, support cancellation and require an explicit
retry after interruption. Completed outputs stay in **Reports**; export Markdown
or save an editable copy to **Notes**. See the [full workflow guide](STUDIO.md).

## Connect AI

Settings offers OpenAI, Claude, Ollama Local/Cloud, llama.cpp and custom OpenAI-compatible connections. Save the endpoint, credentials and model in the appropriate provider profile. Local services such as Ollama or llama.cpp must already be running. The model picker lists the saved connection's models; local Ollama weight downloads require explicit confirmation. Racall does not install Ollama. Answers and research require a model that follows complete structured JSON responses; small or incompatible models may fail validation. See [provider setup](PROVIDERS.md) and [models and appearance](WORKBENCH.md).

Embeddings are optional. After configuring an embedding model, rebuild the notebook index. Changing providers does not translate your documents. Review citations rather than treating AI output as verified fact.

## Language

English is the default. Settings → Interface language changes English / Русский immediately and persists the choice. The Windows installer also asks for language; this seeds the first launch only. Existing preferences survive upgrades. System file dialogs use your OS language.

## Data and backups

The exact data path appears in Settings. Defaults:

| OS | Data directory |
| --- | --- |
| Windows | `%APPDATA%/OpenNotebook/knowledge` |
| macOS | `~/Library/Application Support/OpenNotebook/knowledge` |
| Linux | `~/.config/OpenNotebook/knowledge` |

The old working name in the directory is intentional and avoids moving existing data. Close Racall before copying the whole knowledge directory. Original documents, Markdown notes, reports and metadata are stored there; `index.sqlite3` is a rebuildable index. API keys are in the OS keychain and must be entered again after restoring on another computer. Keep backups private.

## Connect another AI client

Select a notebook and open Connect AI to copy its MCP configuration. The stdio server provides read-only access to that notebook. It cannot edit notes or access another notebook. Remote HTTP MCP and OAuth are not included in 0.3.

## Troubleshooting

If AI is unavailable, check the endpoint, model ID, API key or local Ollama process. Import, notes and text search remain usable without a model. For a startup failure, check `backend.log` in the data directory. Before attaching logs to an issue, remove document contents, paths, tokens and other private information. [Report a bug](https://github.com/SleepyCodeMeow/Racall/issues/new/choose).


## Notebook and source maintenance

Use the menu beside a notebook name to rename it or move it to trash. The confirmation explains that its files are retained. **Notebook trash** restores it with the same sources, notes and conversations. Resolve an unsaved-note conflict and wait for ongoing imports/model requests before deleting a notebook.

Open a source and use **Replace file** for an imported document or **Refresh from website** for a web source. Its current working version remains usable while the replacement is processed; a failed replacement shows an error and can be retried. The version selector opens retained originals and passages. Clicking an old answer's citation selects the version used by that answer.

See the [0.3 release notes](releases/0.3.0-beta.1.md) for verification scope and limits.
The [model evaluation guide](MODEL_EVALUATION.md) and [recorded Ollama results](MODEL_EVALUATION_03_2026-10-25.md)
are available for voluntary testing. Model verification can miss unsupported claims;
review the cited passages. Reports from other hardware, operating systems and models
are welcome through [GitHub Issues](https://github.com/SleepyCodeMeow/Racall/issues).
