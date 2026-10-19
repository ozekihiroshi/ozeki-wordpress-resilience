# Backup Core contract v0.1

This first implementation extracts PHP MySQL dumping only. Storage contracts below describe existing M1 behavior and requirements for a later extraction; they are not implemented by Backup Core 0.1.0.

## Database dump

Input: DatabaseConnection(host, port, databaseName, username, password, optional socket). Output: DumpResult with a caller-owned local path, positive size, database name, mysql engine and DateTimeImmutable creation time. SQL is uncompressed. SHA-256 and compression belong to the caller in this version.

The dumper uses its own mysqli connection with utf8mb4, REPEATABLE READ and a consistent snapshot. It does not load WordPress or alter a WordPress connection. Snapshot guarantees apply only to supporting storage engines; this is not a transaction spanning DB and media. Existing limitations on views/triggers/routines and concurrent schema changes are unchanged.

Files are exclusively created and POSIX mode 0600 is verified. A failed dump removes the incomplete file and rolls back/ closes its connection. On success the caller must consume and unlink the file in finally. No automatic retry is made. Error chains are diagnostic data and must not be dumped to public logs.

Public methods and injected reader interfaces retain their existing signatures. Legacy class aliases preserve constructor and method calls; get_class(), reflection names and serialized class names now identify version-scoped classes. The component does not promise compatibility for persisted serialized service objects.

## Storage boundary for subsequent extraction

A successful upload receipt identifies bucket, region, key, non-null Version ID, bytes and SHA-256. A conditional write must not replace an existing object. Indeterminate writes must be reconciled before retry. A retrieval consumes an independently supplied expected version/size/hash, verifies every byte and publishes only after success, without overwriting an existing destination. No receipt asserts authenticity, independent IAM authority or successful restoration.

## Product boundary

Schedules, retention, UI, IAM policy, backup-set consistency and recovery readiness belong to each product. Resilience aggregates required assets and produces restoration observations. A provider reporting a successful DB dump does not certify an entire site's recoverability. Legacy formats must be validated by adapters and missing fixed versions must remain unresolved.

## Distribution

Canonical code lives in packages/backup-core. The legacy product contains a generated, hash-verified libs/backup-core copy plus compatibility aliases. tools/vendor-backup-core.py refuses drift or unrelated existing files. Both distributions include the version-scoped code and license; no runtime installation of another plugin is needed. S3 and gzip remain outside this first shared component.
