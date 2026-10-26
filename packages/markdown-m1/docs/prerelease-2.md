# GitHub Pre-release v0.3.1-pre.2 — prepared, not published

[日本語](prerelease-2-ja.md)

Trial distribution for technical WordPress maintainers; not a stable release or WordPress.org submission. Proposed tag: `v0.3.1-pre.2`. Installable filename: `ozeki-wordpress-resilience-0.3.1-pre.2.zip`; plugin display version remains 0.3.1. Identify by filename and the accompanying SHA-256. No release/tag is created by this preparation.

## What this candidate provides

Compared with published pre.1, this includes fixed-version readback of every initial-snapshot/complete-Checkpoint resource before manifest confirmation, weekly/monthly/yearly GFS settings, independent capture even without updates, retention-aware manual and scheduled cleanup, and correct handling of genuinely unset Object Lock configuration. It preserves the supported content/adapters and original/metadata separation described in the README.

Baseline is the administrator-approved first independent recovery point. Normal Checkpoints use protected S3 assets and confirmed history, not unrecorded live WordPress changes. Current-site recapture is a separate new Baseline. Retained Checkpoints and required subsequent history enable reconstruction without the source environment.

## Evidence and conditions

The executable files and dependencies are byte-identical to the tested gfs-lock-read candidate. Only documentation is updated. Its fresh installation/update checks preserved settings, pending fixtures, history and recovery results; those checks are reused, not claimed as a new installation trial of these ZIP bytes.

Real S3 trials verified capture/readback, retained Checkpoint plus tail-history recovery, browser-confirmed deletion of 17 obsolete versions, scheduled deletion of 14 versions while retaining active weekly points, and dm recovery from the remaining scheduled Checkpoint. Injected first-PUT failure confirmed no manifest/deletion, an unchanged 28-version inventory, failure reporting and a next reservation. This injection is not an actual AWS outage.

Use a versioned bucket, correctly scoped read/write/version-list/lock-inspection permissions, and fixed-version delete permission only where cleanup is intended. S3 deletion protection is optional; existing bucket/object locks still apply and are never bypassed. Preserve the latest point, active GFS points, boundary point and required history/resources. Manual cleanup removes policy-eligible expired resources, not arbitrary retained points or whole-store resets.

## Not promised

No complete malware removal, universal plugin compatibility or unconditional recovery. Supported reconstruction requires a prepared compatible WordPress and appropriate access. Unknown captured information is retained without unrestricted automatic application. Unconfirmed operations are excluded.

Scheduled tests used actual due times and the standard server-invoked wp-cron.php, not HTTP loopback. Long-term recurrence, natural monthly/yearly expiry, real locked-object deletion and interrupted deletion remain unverified. WP-Cron is not an exact-time guarantee; failure stops and requires cause investigation. No automatic recovery continuation, DNS switching or mail replay is promised.

See [setup and recovery](start-here.md), [GFS operations and historical evidence](gfs-checkpoints.md), and [browser/scheduled acceptance](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/e87ba0b38898331252098d17bc16f649f5a16252/docs/releases/cleanup-browser-scheduled-acceptance.md).
