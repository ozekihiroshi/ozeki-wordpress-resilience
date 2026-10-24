# Save-status final ZIP acceptance — 2026-10-25

Candidate: `ozeki-wordpress-resilience-0.3.1-save-status-final.zip` (7,379,622 bytes, 3,812 files).
SHA256: `43429964fe9ad68b5cc0979ebf3f9d95e760ff03b6c12b20fff1090975ff630b`.

## Results

Fresh installation and overwrite update from the validated recovery-result-final 0.3.1 ZIP passed. Existing dm container/core/DB reused, with unused isolated `owrsszip_20261025_fresh_` / `owrsszip_20261025_upgrade_` namespaces and separate content directories. No new infrastructure or authentication helper. Installation was extraction/activation and file overwrite, not browser Plugin_Upgrader.

Settings, article identity/content, comments, CF7/Flamingo data, WP-Members credentials/settings, TablePress data/IDs/settings, four frozen pending operations and errors, previous recovery result and latest attempt were preserved. The complete installed admin page rendered save status, latest confirmed history and resume-required state without saving/restoring content or resuming the synthetic queue.

Existing S3 formal history: 56 records; SHA256 before/after `590424c54da516c7c93a9e4918c35fc8071c185044354f9a65d692f0d2466c53`. Standard AWS SDK EC2-role authentication, read-only; no S3 writes/deletes. All 3,812 installed files match ZIP bytes in both installations. Vendor unchanged; only Plugin.php and packaged English/Japanese READMEs differ from previous ZIP.

Focused save-status and recovery-result contracts plus PHP lint passed against the extracted final product. Covers empty/unreadable history, pending reasons/missing reasons, stale errors, escaped metadata and omission of payload body, and existing recovery-result states. No new site reconstruction or real S3 outage is claimed. Earlier source-browser display acceptance is recorded in save-status-20261025.

Existing live-site before/after probes identical. No existing members/content modified, no email, scheduled execution, production deployment, PR or formal release. Mail counter zero; Cron execution disabled. Existing timer definitions retained; WordPress first-boot maintenance events are distinguished from execution.

## Limits and issue classification

Confirmed history, local pending operations and recorded errors are separate. S3 read failure is unknown, not empty. Empty queues do not prove that unsupported operations were protected. Old or absent errors are possible; this display is not a durable audit log. Unconfirmed operations remain excluded from recovery. English/Japanese root and packaged README explain these limits and identify this candidate.

Environment: pre-existing duplicate DISABLE_WP_CRON warning from the unchanged live probe; disabled state verified. No product failure observed. Test preparation's pending-count assertion was corrected from five to the actual four existing synthetic entries before execution; no product change needed. Remote CI not yet run for these uncommitted changes. Frozen earlier candidates remain unchanged.
