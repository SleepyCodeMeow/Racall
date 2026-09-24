# Racall licensing

Racall uses different licenses for different components. This is a component split, not a choice of either license for every file.

| Scope | License |
| --- | --- |
| `apps/api/**` — Python knowledge service and MCP | Apache-2.0 |
| `tests/**`, `scripts/**` — tests and developer/release tools | Apache-2.0 |
| `apps/web/**` — web interface | AGPL-3.0-only |
| `apps/desktop/**` — Electron desktop application | AGPL-3.0-only |
| `apps/shared/**` — resources shared by the interface and desktop app | AGPL-3.0-only |
| `installer/**` — application installer customization | AGPL-3.0-only |
| Other first-party files, including documentation and brand assets, unless separately marked | Apache-2.0 |

The full terms are in [LICENSE](LICENSE) (Apache 2.0) and [COPYING](COPYING) (GNU AGPL version 3). Scope takes precedence over the location of the license texts. Third-party code and dependencies retain their own licenses; these project licenses do not relicense them. Preserve applicable notices, including [NOTICE](NOTICE).

## What this means

Both licenses permit use, modification, contributions, commercial use and sale under their conditions. There is no noncommercial or no-sale restriction.

Apache 2.0 permits redistribution, including proprietary derivatives, subject to its notice and other requirements. AGPLv3 requires corresponding source when distributing covered versions and, under section 13, an offer of corresponding source to users interacting remotely with a modified covered version. Private modification alone does not require publishing code to the whole world. The full license texts govern.

SleepyCodeMeow is the project founder and maintainer. Contributors retain rights in their contributions; submitting a change does not transfer copyright. Copyright, patent rights and branding are distinct: these license files do not establish a patent or grant permission to imply official endorsement.

## Previously published MIT material

The existing tag `v0.1.0-beta.1`, its source archive and its published installers were released under MIT. They have not been rebuilt, relabeled, replaced or retagged by this licensing update. A copy of those original terms is preserved in [docs/licensing/MIT-legacy.txt](docs/licensing/MIT-legacy.txt).

This update to the current branch does not revoke MIT permissions already granted. Material previously available under MIT remains available under those grants, including when unchanged material appears in a later tree. The component licenses above govern contributions and revisions offered under them, subject to those existing rights.

The application version remains unchanged at the owner's request. For the precise terms of a particular checkout, consult its commit's licensing files; do not infer the license solely from the version number. Download links in the README still point to the original MIT release.

## Distribution and contribution

Keep license texts and notices with distributions. For a build from the current branch, the packaging configuration includes these documents under `resources/legal`. Redistributors of AGPL-covered code must also meet the corresponding-source requirements; merely bundling license text is not sufficient. Keep the source and build instructions for the exact distributed revision available as required by the license.

Contributions are accepted under the license of the component being changed. See [CONTRIBUTING.md](https://github.com/SleepyCodeMeow/Racall/blob/main/CONTRIBUTING.md). A change touching both components licenses each part under the corresponding component terms, rather than giving a free choice between them.
