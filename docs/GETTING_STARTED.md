# Getting started

[Documentation](README.md) · [Download releases](https://github.com/SleepyCodeMeow/Racall/releases)

## Install

The current **0.2 Beta** package is a Windows x64 EXE installer. Linux and macOS packages for 0.2 are not included; platform testing and contributor help are welcome. Earlier 0.1 packages remain in their separately labeled GitHub release. For those older packages, macOS uses a DMG/ZIP and Linux uses a DEB/AppImage.

The Windows installer is unsigned. Use the checksums attached to the release to verify your download. There is no automatic updater; install later releases manually after backing up your data with Racall closed. Earlier macOS packages are not notarized.

## First notebook

Create a notebook, open Sources and import PDF (with a text layer), UTF-8 TXT/Markdown or DOCX. You can also import a public HTML URL. Files are limited to 25 MB. Wait for the source to become ready, then choose Search and enter a phrase from the document. Open a result to inspect its exact passage.

Notes use Markdown. In 0.2, edits autosave after a typing pause; wait for Saved before closing. If a file changed outside Racall, review the recovered draft and save a copy or reload the file. Frontmatter and wikilinks are supported. A notebook's folder can be opened in Obsidian; Racall is not an Obsidian plugin. Earlier 0.1 builds require explicit saving.

## Chat history

Use the chat selector to reopen a conversation, or New chat to start another one. Questions, search results, answers and citation snapshots survive a restart. Rename changes the title; Delete moves the transcript into the notebook's `trash/chats` folder. There is no trash restore interface yet. Interrupted requests are marked and are not automatically sent again. Each AI answer still uses the current question and retrieved sources; storing history does not yet add follow-up question resolution.

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

Select a notebook and open Connect AI to copy its MCP configuration. The stdio server provides read-only access to that notebook. It cannot edit notes or access another notebook. Remote HTTP MCP and OAuth are not included in 0.2.

## Troubleshooting

If AI is unavailable, check the endpoint, model ID, API key or local Ollama process. Import, notes and text search remain usable without a model. For a startup failure, check `backend.log` in the data directory. Before attaching logs to an issue, remove document contents, paths, tokens and other private information. [Report a bug](https://github.com/SleepyCodeMeow/Racall/issues/new/choose).


## Notebook and source maintenance

Use the menu beside a notebook name to rename it or move it to trash. The confirmation explains that its files are retained. **Notebook trash** restores it with the same sources, notes and conversations. Resolve an unsaved-note conflict and wait for ongoing imports/model requests before deleting a notebook.

Open a source and use **Replace file** for an imported document or **Refresh from website** for a web source. Its current working version remains usable while the replacement is processed; a failed replacement shows an error and can be retried. The version selector opens retained originals and passages. Clicking an old answer's citation selects the version used by that answer.

See the [release notes](releases/0.2.0-beta.1.md) for verification scope and limits. The [model evaluation guide](MODEL_EVALUATION.md) is available for voluntary testing; final live-model acceptance was not performed for this Windows beta. No automatic updater is included.
