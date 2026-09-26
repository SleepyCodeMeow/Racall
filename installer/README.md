# Windows installer

Racall uses a light first screen with a searchable language list (English by default, Russian available), the existing mascot at the upper right, and an optional **Change folder** button. A normal current-user installation proceeds directly to installation progress, then the standard finish screen. Existing machine-wide installations retain their scope/elevation handling.

The first screen runs as a small bundled NSIS helper during the parent installer's initialization. This is necessary because NSIS fixes its language table after `.onInit`. Selecting a language updates the helper's text immediately; clicking Install returns the language and directory through an INI file in the parent's temporary plugin directory. The parent then initializes its complete native translation and starts installation. Cancel exits before installation. No additional executable must be downloaded.

Required space comes from the parent install section's unpacked size; free space is queried from Windows for the chosen drive. The UI never uses a fixed product-size estimate. The application seeds a missing profile from the installer choice; an existing saved preference takes precedence. Silent installs skip the helper and accept `/LANGUAGE=1033` or `/LANGUAGE=1049`.

## Find the code

- `catalog.json`: language names, search aliases, NSIS identifiers and first-screen translations.
- `catalog.nsh`: generated catalog; do not edit directly.
- `welcome.nsh`: searchable native controls, immediate translation, folder picker and disk space.
- `welcome-ui.nsi`: builds the small first-screen executable (no installation commands).
- `selection.nsh`: compiles/bundles the helper, reads its selection before NSIS translation initialization and skips the redundant current-user scope page.
- `languages.nsh`: command-line locale and first-run seed written beside the application.
- `appearance.nsh`: white surfaces, neutral text, Segoe UI and product-only footer.
- `assets/header.bmp`: 150 × 57; `assets/sidebar.bmp`: 164 × 314; both 24-bit RGB.
- `../scripts/build_installer_assets.py`: regenerates bitmaps from `assets/icon.png`.
- `../scripts/check-installer-ui.ps1`: native UI test; the helper writes only a test selection file and cannot install Racall. Screenshots use a labelled 512 MiB test payload and real disk free space.
- `../package.json` → `build.nsis`: resource paths and standard installer options.

## Add a language

Add the application's translation first, following [Localization](../docs/LOCALIZATION.md). Add an entry to `catalog.json`, including all text keys, native name, useful search aliases, the Windows language ID, electron-builder locale and NSIS language name. Add its locale to `build.nsis.installerLanguages`. Then run:

```powershell
uv run python scripts/build_installer_catalog.py
npm run check:installer-catalog
```

The generator checks unique language identifiers, English ordering, application catalog availability and installer-language parity. Extend native UI coverage for the new language. `pwsh -NoProfile -File scripts/check-installer-ui.ps1` requires Windows and the NSIS compiler cached by a preceding electron-builder run. CI also verifies actual installation/uninstallation and EN/RU seed files on disposable hosts.

Resource dimensions follow [electron-builder](https://www.electron.build/v26/docs/features/icons-and-images/) and [NSIS Modern UI](https://nsis.sourceforge.io/Docs/Modern%20UI%202/Readme.html). Preserve the mascot and white bitmap backgrounds. Windows still controls the title bar and native folder dialog styling/language.
