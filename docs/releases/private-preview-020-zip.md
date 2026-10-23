# Private reconstructed-content preview 0.2.0 ZIP validation

The plugin and matching operator kit are identified by [the recorded SHA-256 hashes](../../evidence-public/private-preview-zip-validation.json). Earlier 0.2.0 archives remain preserved; filenames alone do not identify equivalent builds.

Tests ran from the extracted frozen kit. Fresh installation and upgrade from the previous PR #17 console ZIP each passed 62 browser checks. Settings, legacy history, Cron, posts, metadata, pending requests and reports were retained. Reinstallation after reconstruction also retained both preview files and generation reports/requests; both previews remained readable with their original generation and Q. The new external kit read an existing generation and extended its history without changing preserved files. Related tests: 39 material/worker tests, 9 S3 adapter tests, 8 distribution tests and PHP console contracts passed.

These lifecycle tests use a persistent S3 double. The earlier 58-check live S3 trial is [separate evidence](../../evidence-public/site-private-preview-live-s3-validation.json), not a new live S3 test of this ZIP. No production change or automatic publication occurred. The first ZIP trial exposed a UI switch race; final v4 hides the old frame until the selected generation loads and ignores late responses. The test waits for that generation marker. The failed v1 ZIP and logs remain preserved. The final v4 trials had no further failures.

The included adapter correction persists an empty journal before a first request can fail. Existing missing/uncertain journals still fail closed. The earlier WSL IPv6 timeout and process-local IPv4 workaround are environment findings, not plugin requirements; the workaround is not shipped. Historical browser timing corrections are recorded separately in the preview evidence.

The preview is a private target-content snapshot, not live theme rendering. Existing jobs without snapshots are not backfilled; cleanup/expiry is manual. Update both plugin and operator kit while preserving private configuration, journals and bridge history. Temporary draft targets and no public activation remain intentional boundaries.

This result document and evidence were written after freezing. ZIP bytes were rechecked and not modified afterward.
