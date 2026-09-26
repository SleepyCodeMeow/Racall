# Localization

Racall defaults to English and supports Russian. Language is a per-profile preference, independent of the AI provider configuration or OS language.

## Storage and startup

`<knowledge directory>/preferences.json` stores `{ "locale": "en" }` or `{ "locale": "ru" }`.
Authenticated `GET /api/preferences` and `PUT /api/preferences` read and update it. Writes are atomic and serialized. Unsupported locale values are rejected; missing or malformed preferences fall back to English.

The Windows NSIS installer includes English and Russian with a searchable language list on its first screen. `installer/languages.nsh` writes the selected locale to `<install directory>/resources/installer-language.json`. It does not write to the installing administrator's personal profile.

On startup, `apps/desktop/locale.cjs` seeds a missing profile preference from that file. Existing preferences always win. macOS, Linux and development launches default to English when no installation choice exists. Native startup errors read the same saved preference. Windows silent installation can provide `/LANGUAGE=1033` or `/LANGUAGE=1049`.

The renderer fetches its preference before showing the interface. It does not rely on localStorage or the dynamically allocated localhost port. Changing language updates translations and the HTML `lang` attribute without restarting the app. It does not rewrite source files, note content or model-generated claims.

## Translation catalogs

- `apps/shared/locales/en.json` is the canonical typed catalog.
- `apps/shared/locales/ru.json` has the same keys and placeholders.
- `apps/web/lib/translations.ts` handles lookup, interpolation and Intl plural rules.
- `apps/web/lib/i18n.tsx` provides the reactive language context.
- `localizeMessage` adapts existing service-owned diagnostic strings. Never apply it to user documents or AI-generated claims. New diagnostics should have stable catalog keys.

## Adding a language

1. Add a catalog with every canonical key and the same interpolation placeholders.
2. Register its locale and native name in `translations.ts` and its catalog in `apps/desktop/locale.cjs`.
3. Extend the validated preferences locale set in `apps/api/on_knowledge/app.py`.
4. If offering it during Windows installation, add the language and translated first-screen text to `installer/catalog.json`, add its locale to `package.json` → `build.nsis.installerLanguages`, and regenerate `installer/catalog.nsh` with `uv run python scripts/build_installer_catalog.py`. See [installer internals](../installer/README.md).
5. Include catalog and placeholder parity tests; review plurals, keyboard labels, small screens and native messages.

Avoid concatenating sentence fragments with variables. Use complete message keys and named placeholders. Product names and protocol names remain unchanged. OS-owned dialogs, such as file pickers, follow the operating system's own language.

## Verification

`npm run test:i18n` checks catalogs, placeholders, plural rules, service diagnostics, English defaults, installer preference seeding and preservation of saved choices.

`npm test` includes authenticated preference writes, unsupported values, process recreation and unchanged provider settings/documents.

`node scripts/smoke-languages.cjs` verifies live switching, full Electron restart, translated provider errors and unchanged notes. With `OPENNOTEBOOK_TEST_EXE` pointing to a packaged app, it additionally exercises the installer language seed and upgrade precedence using isolated profiles, restoring its temporary seed file afterwards.

`npm run check:installer-catalog` validates the generated installer catalog. On Windows, `pwsh -NoProfile -File scripts/check-installer-ui.ps1` exercises the real first-screen helper without installing the application.
