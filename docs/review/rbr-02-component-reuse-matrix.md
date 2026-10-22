# RBR 02 — Component reuse matrix

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

A = unchanged narrow primitive; B = adapt; C = retain as research/evidence; D = optional later extension; E = unnecessary candidate (no deletion authorized). Reusing a contract is not claiming unchanged code works in the plugin.

| Mechanism / source | Class | Treatment in the standard product |
|---|---|---|
| SHA-256, exact version comparison in [VersionedAssetStore](../../src/VersionedAssetStore.php) | A primitive / B integration | Preserve byte/version checks; supply authenticated transport, configurable storage and retention policy. Class currently permits only null/35-day retention. |
| Lab [S3 adapter](../../tools/queue-s3-adapter.py) | C | Preserve real-S3 evidence; do not require community/dm SSH authorization in normal installation. |
| [Typed extraction and issues](../../tools/portable-content.py) | B | Reuse supported-node/loss semantics; adapt to pre-save inputs, stable asset IDs and PHP execution. Python remains a reference/optional tool. |
| [PHP collector](../../tools/portable-content-export.php) | B | Initial-enrollment/import helper; cannot implement save-before-WP by simply scheduling this collector. |
| [Static preview](../../tools/portable-preview.py) | B/C | Keep diagnostic preview and normalization rules. Add a distinct WP target adapter; Docker decoder is not a shared-hosting prerequisite. |
| [RAM schema](../../schemas/recovery-asset-manifest.schema.json), [Recovery Set](../../schemas/recovery-set.schema.json) | B/C | Reuse identity/hash/size/fixed locator/evidence concepts, not old E1/procedure/minimum-eight-assets constraints. New Profile and generation schemas. |
| Existing recovery bootstrap/full DB-file [restore](../../tools/first-site-daily-restore.py) | C; optional D | Preserve old restore research. Not the content reconstruction engine or mandatory installer. |
| [Current trust checkpoint](../../tools/current-recovery-trust.py), signatures | B/D | Retain old recovery gates unchanged. New product needs original/generation provenance and hold decisions; root-owned /etc checkpoint and SSH administration are not standard requirements. |
| [Result registration](../../tools/first-site-restore-observations.py) | B | Reuse explicit attempted/failed/unknown/completed and deduplication semantics; new data model and WP job storage required. |
| Daily acquisition / approval orchestration | C/B | Do not run old DB/file capture for every edit. Adapt useful receipts/reconciliation concepts to ingestion jobs. |
| Watchdog, external notification, systemd, SSH deployment | D | Optional operations extensions; not prerequisites for saving or recovering originals. |
| [DailyAdmin](../../src/DailyAdmin.php) and plugin administration | B | Reuse permissions/escaping/status presentation patterns; create ingestion/Profile/recovery pages, not just relabel old restore statuses. |
| [Same-host preflight](../../tools/same-host-preflight.py), runtime contract | C/B | Keep laboratory containment; replace production readiness assumptions with hosting/storage/format checks relevant to the new plugin. |
| [backup-core provenance](../../packages/backup-core/UPSTREAM.json) | C / A narrow I/O helpers | SQL dump code remains useful to Restore research, not a required Reconstruct dependency. No changes to Backup for S3. |
| External deployment configuration generation | D | Optional controller integration, not ordinary WordPress setup. |

No whole subsystem is classified E for immediate removal. Keep historical contracts/evidence; simplify the standard dependency graph rather than deleting history.

## New capability inventory

N1: S3-first upload/editor save coordinator, intent IDs and reconciliation.
N2: Stable asset identity, Profile, versioned relations and complete-generation manifest.
N3: Plugin-native storage/authentication setup and independent recovery access pack.
N4: Native reconstruction engine with WP target mapping, resumable jobs and bounded work batches.
N5: Requirements-driven verification and separate publication approval.
N6: Incident freeze/hold/quarantine and recovery-time reading of those records.
N7: Normal/Recovery Mode UI, save-status reporting and version selection.

Unknown: PHP packaging/reuse cost and exact API hooks. Existing functions/tests establish narrower contracts only; no new compatibility claims are made here.
