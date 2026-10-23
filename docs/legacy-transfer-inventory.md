# Legacy paths and transfer candidates

Status: inventory, **no transfer completed and no historical evidence deleted**.

The two products are independent. Resilience reconstructs from pre-projection originals. Backup for S3 captures and restores an existing site's DB/files. Neither product is a mandatory dependency of the other.

| Area | Destination / treatment | Reason and next gate |
|---|---|---|
| Fixed-version fetch and digest/size verification (`VersionedAssetStore`, `RbrObjectStore`, Python S3 transport) | Retain reusable primitive in Resilience | New immutable-material reconstruction needs these checks. Evaluate sharing separately; avoid cross-plugin runtime dependency. |
| SQL/files collection and isolated full restore (`tools/*collection*`, legacy daily workflow) | Backup for S3 candidate; exclude from new core | Compare with existing `Backup/Recovery/RecoveryPipeline`, collector, manifest, lock and workspace. Port only missing guarantees, with independent tests. |
| Compression and retention | Do not copy wholesale | Backup for S3 already has `Backup/Compression/GzipVerifier`, compressor and `Backup/Retention`. New per-material compression has different scope. |
| Daily restore observations, progress and failure cleanup | Compare for specific improvements | Backup for S3 already has RecoveryObservation/Progress/Pending and media cleanup. A transfer needs a concrete gap, not a duplicate subsystem. |
| Daily/preflight/watchdog admin and systemd experiments | Research archive / optional operational tools | Not mandatory for S3-first material reconstruction; do not expand Backup for S3 into external monitoring. |
| Three-page RBR coordinator/editor/planner and approval preparation | Compatibility/research path | Preserve old receipts and signature semantics. They do not define the generalized material format. |
| Evidence, historical docs, frozen ZIPs | Preserve history | Historical coverage must not be presented as new-path coverage. |

Deletion gate: identify references and stored-format dependencies; verify the replacement or destination; remove from the active distribution first; archive source with a migration map before deleting runtime code. No production site or existing demonstration is migrated implicitly.

The current legacy builder intentionally remains unchanged to avoid silently changing already-reviewed alpha.5 artifacts. A separate minimal-materials package is the active new-path distribution; the broader development kit remains research/compatibility tooling. The new dedicated editor redirects native entry links and uses the shared projection function. General Gutenberg/classic integration and production enrollment remain unfinished; this is not a general-user release.
