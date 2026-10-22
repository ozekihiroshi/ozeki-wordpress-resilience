# Initial experimental edition — 0.1.0-dev.1

> **Observation closed by operator decision:** 68h 28m 24s, three daily slots completed, two historical gaps retained. This is not a 72-hour pass. See [final assessment](shortened-observation-final.md).

Prepared October 22, 2026 from main `71e54a722498751ebf861238cb4a7c0a921edc7e` (PR #8), with documentation-only clarification. This is a development prototype, not a production-ready protection service. No new production deployment, GitHub tag or formal Release is made by this preparation.

## What is included

The WordPress plugin provides administration and status screens. The separate development kit contains external capture, storage, independent approval, recovery, monitoring and configuration tools. Installing the plugin alone does not start backups or protection. Ozeki Database Backup for S3 is independent; neither plugin requires the other.

Use the already verified **recurring-trust-final-v2** artifacts; do not rebuild or overwrite them just for this documentation update:

| Artifact | SHA-256 |
|---|---|
| ozeki-wordpress-resilience-0.1.0-dev.1.zip | 0537301b4f85b52cbd363c2b5909806b367c5a3d9bc40933325b31f88af51cfb |
| owr-development-kit-0.1.0-dev.1.zip | 7ec65fd810cb57ac6a7b75c4a901a73cdf00d33e0dcb5f83001b1d006e7505fe |

See [artifact acceptance](recurring-trust-final-zip.md) for fresh install, same-version overwrite, settings/history retention and packaged tests. The new summary and pilot checklist are companion documentation, not retroactively part of the frozen ZIPs. PR #8 CI passed on PHP 8.1/8.3; its 54 root-required skips per job are not passes.

## Use and evaluate

1. Read [current scope](current-status.md) and [installation](../guides/plugin-candidate-install.md). Use a dedicated generated-data environment first.
2. Configure external processes using [setup and stopping](../guides/initial-release-setup.md) and [deployment planning](../guides/external-deployment-plan.md). Review identities, writer paths, limits and ownership; do not treat a generated plan as applied configuration.
3. Follow [onboarding through recovery](../guides/onboarding-recovery.md): inspect/admit, capture, store exact versions, independently approve, validate current trust, retrieve and restore in isolation, register results.
4. Maintain [current trust explicitly](../guides/trust-recurring-operations.md). Registry refresh never extends signed approval. Missing, stale or revoked authority must block recovery.
5. Before any real deployment, complete the [pilot checklist](../guides/production-pilot-acceptance.md). VPC, VM size, public IPv4, dm and the USD35 budget are provisional site choices, not universal plugin requirements.

## Acceptance basis and observation

Dedicated tests demonstrate the documented consistency, fixed-version storage, signature/current-trust gates, isolated recovery and state-retention contracts for their tested profiles. Three generated daily slots completed. These are useful evidence, not proof that every site or failure mode is supported.

The 72-hour duration was a project observation target; no external standard or cited technical derivation has been identified in the reviewed planning records. The original request was to observe daily operation for several days. Three daily slots, duration, fault coverage and gaps are different measures. Waiting alone does not establish availability or security.

On October 22 the operator explicitly removed waiting for 72 hours as a prerequisite to assembling this initial edition. The operator subsequently explicitly shortened and closed observation at October 22 12:24:21 JST, after 68h28m24s, without extra stored sets or reruns. The original 72-hour target was not completed. The final snapshot has 127 audits, three approved sets / 89,527,925 bytes, uncertain PUTs 0, 15 unchanged trust files, unresolved/undelivered trial events 0. Two historical gaps (4h26m33s and 4h24m8s) remain. This is periodic sampling, not uninterrupted coverage, and later features do not inherit the original trial's duration.

Future duration must follow the risk being checked (scheduled cycles, expiry/renewal boundaries, disconnect release and restart behavior), with explicit measurable pass conditions. There is no blanket 72-hour gate for each feature. The final assessment is recorded in the closure report; power settings were restored and the scheduled follow-up was paused.

## Known limitations, classified

- **Product:** least-privilege remote capture over a restricted SSH entry and source release after loss of that real collector remain unverified integration work. Earlier SSH/S3 onboarding used DockerBackend for capture. No new SSH adapter is included in this edition. Real-site writer coverage, clean-generation selection, credential replacement and safe republication remain operator/deployment work. Global immediate revocation and administrator-resistant rollback are not implemented.
- **Environment:** actual production placement, independent physical hosts and effective site permissions are not certified by lab tests. No VM creation, production update or FTP/MySQL change is included.
- **Test infrastructure:** the static-report freshness baseline defect was diagnosed and corrected in PR #8; initial failures are retained. Historical browser startup failure remains cause-unknown. Shared-host lab isolation and the S3 test broker limit claims; a later passing run does not explain an earlier failure.
- **Human operations:** real substitute-operator access and physical USB rotation need acceptance. Existing candidate approval expires October 25 18:15:47 JST and is not extended by this edition.

## Next bounded development

First implement restricted SSH capture and test collector loss against source-owned release, reusing the existing capture/gate fixtures. Require: only the configured site/operations are accepted; arbitrary commands and foreign scopes are rejected before capture; source writers resume within a declared lease bound after collector kill/disconnect without collector cleanup; partial or expired capture never becomes an eligible recovery set. No new cloud VM or full repeated S3/ZIP cycle is needed to establish those specific claims. See [evidence reuse review](evidence-reuse-and-collector-gaps.md).
