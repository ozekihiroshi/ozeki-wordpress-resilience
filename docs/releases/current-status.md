# Current implementation and remaining work

Snapshot: October 22, 2026, after PR #7 merged into main `5cd2564`. Both PR CI jobs (PHP 8.1/8.3) passed. Version `0.1.0-dev.1` remains an experimental prototype, not a production release. English is the primary README; [RAADME-jp.md](../../RAADME-jp.md) is the Japanese companion.

## Implemented and checked

| Area | Dedicated evidence | Remaining operational boundary |
|---|---|---|
| Capture and storage | Admission checks, write coordination, DB/file pairing, daily processing, fixed S3 versions and retention | Fit to every real site write path, remote capture backend and production rollout |
| Approval and recovery | Independent signatures, fixed-version retrieval, isolated restore, result registration and interrupted cleanup | Clean-generation selection, credential rotation and safe production republication |
| Current trust | Mandatory independent local checkpoint; stale/revoked bundles rejected; reviewed atomic updates and pinned SSH deployment | Trusted administrator/code/clock, manual refresh and per-host reconciliation; no root-resistant rollback or global immediate revocation |
| Status and monitoring | Read-only WordPress screens, SSH reporting, systemd restart/reboot, watchdog, test notifications | Independent physical failure domains and production monitoring placement |
| Setup and distribution | Configuration drafts, read-only deployment plan, dedicated placement, frozen ZIP installation/overwrite and state retention | No automatic complete production deployment or registry provisioning |

Trust lifecycle operations and their boundaries are described in [key lifecycle](../guides/trust-lifecycle.md), [current registry](../guides/current-recovery-trust.md), [SSH deployment](../guides/trust-registry-ssh.md) and [recurring operations](../guides/trust-recurring-operations.md). Local generation enforcement is now implemented; earlier lifecycle evidence showing old-bundle acceptance describes the historical signature primitive, not the current mandatory recovery entry.

## Observation is a separate assessment

Three generated-data daily slots (October 19–21) completed storage, pending-approval observation, test signing and fixed-version isolated restoration. Maximum three stored sets reached: do not add saves or repeat restores to refresh evidence.

Latest checked audit: October 22 10:16:22 JST, 123 samples; three approved sets totaling 89,527,925 bytes; uncertain PUTs 0; 15 trust files unchanged; unresolved trial incidents 0; undelivered trial notifications 0. No new capacity/continuity issue or gap longer than two hours. This is a dated snapshot, not live telemetry.

Earliest 72-hour threshold: **October 22, 2026 15:55:56 JST**. It has not yet been reached at this snapshot. Existing gaps of 4h26m33s and 4h24m8s remain. Daily success, elapsed time and observation coverage must be evaluated separately. Periodic audits are not continuous observation. Features added later, including PR #7, do not inherit 72-hour coverage from the older running trial.

On actual observation completion, restore battery sleep to three minutes while retaining AC no-sleep, using the recorded restoration procedure; stop follow-up only after final assessment and power restoration. Do not overwrite user changes to the power plan.

## Classification of remaining issues

- **Environment:** the latest audit establishes no new capacity/continuity problem. Production PHP/SMTP/HTTPS maintenance is separate from product acceptance; unrelated database administration and other-host PHP issues are not resolved by this plugin.
- **Test infrastructure:** historical WebDriver startup timeout remains unexplained despite later successful runs. Python-path and dedicated SSH runtime-directory defects were diagnosed and corrected; initial failed evidence remains. Shared kernels, development Docker socket and test S3 broker limit isolation claims. See [environment and infrastructure records](initial-release-environment-notes.md).
- **Product:** current-registry transitions and recovery checks are implemented, including the corrected SSH semantic-outcome classification. Global immediate revocation, administrator-resistant rollback, continuous cancellation after the final check and atomic fleet rollout are not implemented. All production write paths, independent placement, safe republication and ongoing operator coverage remain to be accepted.
- **Human operations:** actual substitute-operator access, physical USB rotation and production approval renewal are not satisfied by generated directory tests. The documented real candidate approval expiry remains October 25, 2026 18:15:47 JST; no test refresh extends it.

## Next work, without repeating completed trials

1. Follow the recurring trust runbook: independently review current authority, refresh explicitly, confirm every intended host, retain unknown outcomes and expiry incidents. Automated signing/approval extension is prohibited.
2. Complete actual deployment/operating ownership decisions separately from dedicated tests. Do not broaden notifications or redo all SSH/systemd/ZIP tests without a changed requirement.
3. After the threshold, finalize the original observation with its gaps and frozen scope, restore power settings and close its follow-up. Formal release remains a separate decision.

## Evidence entry points

- [Onboarding through recovery](../guides/onboarding-recovery.md), [actual SSH/S3 connection](../guides/onboarding-ssh-s3.md), [onboarding ZIP](../guides/onboarding-zip.md).
- [Current trust real S3 recovery](../guides/trust-real-s3-recovery.md) and [frozen trust ZIP acceptance](trust-final-zip.md).
- [Daily admission](../guides/daily-capture-admission.md), [operator confirmation](../guides/recurring-capture-review.md), [generated systemd deployment](../guides/generated-systemd-lab.md).
- [Recurring trust connection checks](../../evidence-public/trust-recurring-operations.json). Frozen ZIPs predate these new docs/tests and are not rebuilt here.

Backup for S3 is independent: no mandatory mutual dependency or automatic installation. Shared components and Backup for S3 are unchanged.

Additional [two-VM recurring SSH verification](../guides/trust-recurring-ssh.md) passed seven checks: per-host readback, partial authentication failure, actual expiry and explicit refresh recovery, with signed approvals unchanged. No new S3/restore or 72-hour coverage claim.
