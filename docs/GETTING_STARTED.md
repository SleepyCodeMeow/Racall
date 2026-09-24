# Getting started

[Documentation](README.md) · [Download releases](https://github.com/SleepyCodeMeow/Racall/releases)

## Install

Choose a package matching your OS and CPU in GitHub Releases. Windows uses an EXE installer; on macOS, open the DMG and copy Racall into Applications, or extract the ZIP. On Linux, install the DEB with your package manager, or mark the AppImage executable and launch it. AppImage may require your distribution's FUSE compatibility package.

These beta builds are unsigned and macOS builds are not notarized. Operating systems may block or warn about them. Use the checksums attached to the release to verify your download. There is no automatic updater in 0.1; install the next release manually after backing up your data.

## First notebook

Create a notebook, open Sources and import PDF (with a text layer), UTF-8 TXT/Markdown or DOCX. You can also import a public HTML URL. Files are limited to 25 MB. Wait for the source to become ready, then choose Search and enter a phrase from the document. Open a result to inspect its exact passage.

Notes use Markdown. Save changes explicitly before closing the app. Frontmatter and wikilinks are supported. A notebook's folder can be opened in Obsidian; Racall is not an Obsidian plugin.

## Connect AI

Settings offers an OpenAI-compatible API or Ollama. For a cloud API, enter the base URL, API key and model ID supported by your provider. For Ollama, start your existing local server and enter an installed model name. Racall does not install Ollama or download models. Answers and research require a model that follows structured JSON responses; small or incompatible models may fail validation.

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

Select a notebook and open Connect AI to copy its MCP configuration. The stdio server provides read-only access to that notebook. It cannot edit notes or access another notebook. Remote HTTP MCP and OAuth are not part of 0.1.

## Troubleshooting

If AI is unavailable, check the endpoint, model ID, API key or local Ollama process. Import, notes and text search remain usable without a model. For a startup failure, check `backend.log` in the data directory. Before attaching logs to an issue, remove document contents, paths, tokens and other private information. [Report a bug](https://github.com/SleepyCodeMeow/Racall/issues/new/choose).
