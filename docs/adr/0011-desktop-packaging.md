# Native desktop packages

Status: accepted for 0.1 desktop preview

## Context
EXE относится только к Windows; нужны три семейства ОС.

## Decision
Electron + статический Next + PyInstaller onedir. NSIS Windows, DMG/ZIP macOS, AppImage/DEB Linux. Native build matrix.

## Alternatives
Tauri sidecar; Docker-only; browser-only.

## Consequences
Размер Electron больше Tauri, зато не требуется Rust toolchain. macOS/Linux сборки требуют своих runners. Подпись и нотарификация пока не настроены.
