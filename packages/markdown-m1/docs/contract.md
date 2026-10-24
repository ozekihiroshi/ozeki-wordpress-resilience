# M1 minimal contract — 2026-10-24

Authority: completion charter v2.0, corrected D2 responsibility boundary, D3 independent product path, D4 asset-level full history, and the latest explicit M1 scope (which overrides D4 scheduling/Checkpoint requirements for this milestone).

`originals/<asset UUID>/<operation UUID>/source.md` is the full submitted UTF-8 source. `metadata.json` contains requested title, slug, status, dates and origin identifier/URL. A source reference is `{key,version,sha256}`. These are relative to the administrator's configured S3 prefix, never local files.

`history/<20 digit sequence>.json` has schema `owr-md-history-1`, order, original references, confirmed attributes and confirmation time. Sequence is allocated under the writing WordPress's MySQL advisory lock and the S3 history key is create-only. One writing WordPress per prefix is a deployment requirement. A prepared original is not a successful operation. This is an asset event stream, not a file diff or whole-site snapshot.

Supported normal editor request → validate permission, stale token and UTF-8 → acquire single-writer lock → save S3 originals → begin DB transaction → normal WordPress and Markdown Documents save → compare raw source and attributes → durable local pending confirmation and DB commit → create-only formal S3 record. A shutdown before DB commit rolls back. A formal-history error after DB commit retains a visible pending confirmation. Retry checks the current applied state; it never blindly certifies a changed document.

The pending option is an operational outbox, not recovery authority. Formal recovery discovery uses S3 only. If the entire source disappears before its success evidence reaches S3, the unconfirmed last operation cannot be distinguished from an abandoned prepare and is not automatically adopted. There is no claimed distributed atomic transaction.

Reconstruction reads selected history and pinned originals from S3, verifies hashes, then inserts/updates stable document identities in a new WordPress. It compares raw source, title, slug and status before committing. A slug collision fails the restore. Canonical origin URLs are recorded so rendered document links can target the new installation without altering raw files. M1 does not generate Checkpoints.

The ordinary full editor is the integration boundary. Scheduling, imports, arbitrary API/third-party writes and unrelated WordPress operations are allowed but not automatically certified by M1. Product runtime has no dependency on the old research modules. Test fault injection and role signing live only under `tests/`, excluded from the ZIP.
