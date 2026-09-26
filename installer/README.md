# Windows installer appearance

The assisted NSIS wizard stays light, with the existing Racall mascot in the upper-right header. The finish/uninstall sidebar uses the same logo on white instead of the stock NSIS artwork. Native controls, keyboard navigation, EN/RU language selection, installation-directory choice and user-data preservation remain in the standard installer flow.

- `appearance.nsh`: neutral text/background colors, Segoe UI and product-only footer.
- `languages.nsh`: installer language selection and first-run seeding.
- `assets/header.bmp`: 150 × 57, 24-bit RGB.
- `assets/sidebar.bmp`: 164 × 314, 24-bit RGB.
- `../scripts/build_installer_assets.py`: regenerate both bitmaps from `assets/icon.png` with `uv run python scripts/build_installer_assets.py`.
- `../package.json` → `build.nsis`: resource paths and standard wizard options.

Resource dimensions follow [electron-builder](https://www.electron.build/v26/docs/features/icons-and-images/) and the [NSIS Modern UI](https://nsis.sourceforge.io/Docs/Modern%20UI%202/Readme.html). Keep the bitmap background white; do not redraw or recolor the mascot. The native title bar and buttons can still follow Windows system styling.
