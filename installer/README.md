# Windows installer

Racall uses a light first screen with a compact language dropdown (English by default, Russian available), a short introduction and the existing mascot at the upper right. The first-screen layout follows the supplied Ollama reference: 837 × 637 at 96 DPI, a white body, a product title at the upper left, a logo at the upper right and a gray footer with Install and Cancel. Introductory text, the continuation instruction and the language row are spaced equally. Text uses 16-pixel Segoe UI at 96 DPI; the mascot has the reference's approximately 66-pixel visible height, preserving its own aspect ratio. The native caption shows `Setup — Racall version 0.2 Beta` (localized in Russian), with the Racall icon. The label is generated from `apps/shared/release.json`, rather than hard-coded in the installer. On opening, the installer reads the Windows app-theme preference and opts its native caption into dark mode when appropriate; the content stays white. The standard desktop frame supplies the reference caption height (31 pixels at 96 DPI on the tested Windows 11 machine). Windows calculates the outer borders from a 835 � 605 client area; the visible DWM frame is 837 � 637 on that machine. The Size system command is removed to keep the wizard fixed-size, while native minimize and close remain available. Unsupported DWM versions retain standard window rendering. There is no separate search, folder picker or disk-space summary on this screen; the standard current-user location is selected automatically. A normal current-user installation proceeds directly to installation progress, then the standard finish screen. Existing machine-wide installations retain their scope/elevation handling.

The first screen runs as a small bundled NSIS helper during the parent installer's initialization. This is necessary because NSIS fixes its language table after `.onInit`. Selecting a language updates the helper's text immediately; clicking Install returns the language and directory through an INI file in the parent's temporary plugin directory. The parent then initializes its complete native translation and starts installation. Cancel exits before installation. No additional executable must be downloaded.

A disk-space check runs when Install is clicked, using the parent section size and Windows free-space information. A localized error appears only if space is insufficient. The application seeds a missing profile from the installer choice; an existing saved preference takes precedence. Silent installs skip the helper and accept `/LANGUAGE=1033` or `/LANGUAGE=1049`.

## Find the code

- `catalog.json`: language names, NSIS identifiers and first-screen translations.
- `catalog.nsh`: generated catalog; do not edit directly.
- `welcome.nsh`: native language dropdown, immediate translation and the disk-space guard.
- `layout.nsh`: reference first-screen geometry with DPI scaling, equal row spacing and native footer controls.
- `welcome-ui.nsi`: builds the small first-screen executable (no installation commands).
- `selection.nsh`: compiles/bundles the helper, reads its selection before NSIS translation initialization and skips the redundant current-user scope page.
- `languages.nsh`: command-line locale and first-run seed written beside the application.
- `appearance.nsh`: white surfaces, neutral text, Segoe UI, the versioned caption and Windows title-bar theme integration.
- `assets/welcome.bmp`: 221 × 84, rendered directly from the full-resolution icon for the larger first-screen mascot.
- `assets/header.bmp`: 150 × 57; `assets/sidebar.bmp`: 164 × 314; both 24-bit RGB.
- `../scripts/build_windows_icon.py`: regenerates `assets/icon.ico` with tight artwork bounds and native 16/20/24/32/40/48/64/128/256-pixel frames for Windows captions, taskbar and Explorer. The shared PNG and large installer artwork keep their existing presentation padding.
- `../scripts/build_installer_assets.py`: regenerates bitmaps from `assets/icon.png`.
- `../scripts/check-installer-ui.ps1`: native UI test; the helper writes only a test selection file and cannot install Racall. The fixture supplies a 512 MiB payload size to the hidden disk-space guard.
- `../package.json` → `build.nsis`: resource paths and standard installer options.

## Add a language

Add the application's translation first, following [Localization](../docs/LOCALIZATION.md). Add an entry to `catalog.json`, including all text keys, native name, the Windows language ID, electron-builder locale and NSIS language name. Add its locale to `build.nsis.installerLanguages`. Then run:

```powershell
uv run python scripts/build_installer_catalog.py
npm run check:installer-catalog
```

The generator checks unique language identifiers, English ordering, application catalog availability and installer-language parity. Extend native UI coverage for the new language. `pwsh -NoProfile -File scripts/check-installer-ui.ps1` requires Windows and the NSIS compiler cached by a preceding electron-builder run. CI also verifies actual installation/uninstallation and EN/RU seed files on disposable hosts.

Resource dimensions follow [electron-builder](https://www.electron.build/v26/docs/features/icons-and-images/) and [NSIS Modern UI](https://nsis.sourceforge.io/Docs/Modern%20UI%202/Readme.html). Preserve the mascot and white bitmap backgrounds. Windows still controls the title bar and native control styling.

Title-bar integration uses Windows [DwmSetWindowAttribute / DWMWA_USE_IMMERSIVE_DARK_MODE](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute); it does not change system theme settings or draw replacement caption buttons.

## Preview installation progress without installing

Compile `preview-progress.nsi` with the same NSIS compiler and `/DPROJECT_DIR=<repository path>` used for `welcome-ui.nsi`, then run `build/Racall-progress-preview.exe`. Pass `/LANGUAGE=1049` for Russian; English is the default.

This standalone fixture uses the production Modern UI installation page, caption, icon, header bitmap and fonts. Its section contains only a wait loop: no application payload, registry writes, shortcuts, profile changes or application launch. A matching native progress control holds a sample 42% value independently of NSIS's instruction counter. `Preview` in the caption and `(preview only)` in the sample filename distinguish it from a real installation. Cancel or the window close button exits immediately. The fixture is not included in release packages.
