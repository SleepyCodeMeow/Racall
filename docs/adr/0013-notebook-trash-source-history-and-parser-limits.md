# Recoverable notebooks, immutable source versions and bounded parsers

Status: implemented for the 0.2 candidate, 2026-09-26.

## Notebook lifecycle

Rename changes notebook metadata under the shared store lock. Delete is a reversible directory rename into `knowledge/trash/notebooks/<id>`, retaining the same notebook ID and all content. Restore moves it back and checks index recovery. There is no permanent-delete endpoint. UUID validation and containment checks protect move destinations. The frontend waits for registered editors to save before switching/deleting; a conflict blocks the action. A counted notebook operation prevents deletion while import/model/research work uses its paths, without holding a lock during provider requests.

## Source versions

Content SHA-256 identifies a source version. New originals, normalized documents and version metadata live under `sources/<source-id>/versions/<hash>/`; `source.json` selects the current version. Legacy root-level originals remain readable and are copied into history before replacement. Existing originals are not silently deleted.

A replacement is recorded as `pending_version`. Its parser and embeddings complete before the current version advances. Search-index replacement uses a SQLite transaction alongside the atomic metadata update, under the store lock. A failed promotion restores the prior pointer and rolls back index changes. Filesystem writes and SQLite are not one crash-atomic transaction: startup compares the selected version with the index and rebuilds missing/mismatched cache data. Search never presents mismatched-version chunks as current evidence. A failed pending version is not silently retried when merely repairing the active index.

Historical citation views request the exact version's document and original file. Highlighting also verifies the saved quote at its stored offsets. All version files are retained; storage grows with revisions. Versions are content snapshots, not a collaborative editing or filesystem synchronization protocol.

## Parser supervision

File parsing and public-page extraction run as one-shot child processes of the Python service. The parent enforces a 60-second wall-clock deadline and samples resident memory every 50 ms with psutil, terminating workers above 512 MiB. Linux additionally applies a 1 GiB address-space limit. JSON output is capped at 64 MiB. The worker has an orphan/deadline watchdog; it does not receive the desktop HTTP authentication token.

This is resource containment, not an OS security sandbox. Brief memory overshoot between samples is possible. Network requests for public-page ingestion retain the existing DNS pinning, address validation, redirect and byte limits. Failed workers return actionable errors and leave the API process responsive.

## Reference adaptation

The [SurfSense desktop queue at `014e47a7efa1`](https://github.com/MODSetter/SurfSense/blob/014e47a7efa18f7e5c4f726cb8640b0a9e9ba94e/surfsense_local/backend/shared/queue.py) and artifact model paths reviewed in [REFERENCE_PROJECTS.md](../REFERENCE_PROJECTS.md) informed the separation of import work and retained deliverables. Racall keeps its single ingestion queue, portable files and SQLite cache; it adds bounded one-shot parsers without copying upstream code or introducing the upstream queue/database stack.

The process supervisor uses the maintained [psutil memory API](https://psutil.readthedocs.io/stable/). Explicit worker CLI arguments avoid frozen multiprocessing spawn/import ambiguity across operating systems.

## Checks

Regression tests exercise legacy sources, source identity across URL refresh, historical originals/quotes, injected promotion failure with index rollback, repair after cache loss, notebook restoration, busy-state protection, parser resource limits and the publication hold. Desktop maintenance checks exercise the actual controls and restart. Native installer checks run only on disposable CI hosts; real-model evaluation remains an owner-run acceptance step.
