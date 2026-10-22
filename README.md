# Ozeki WordPress Resilience

> **Observation closed by operator decision:** 68h 28m 24s, three daily slots completed, two historical gaps retained. This is not a 72-hour pass. See [final assessment](docs/releases/shortened-observation-final.md).

English | [日本語](RAADME-jp.md)

> **Experimental prototype — not a completed production protection product.**
> The installable WordPress ZIP provides administration and status screens. Capture, storage, signing, recovery, monitoring and notification delivery require separately configured external processes. Installing the plugin alone does not start protection.

The project aims to preserve recovery assets and recovery capability when WordPress is compromised or unavailable. It covers consistent database/file/queue capture, external storage, exact-version retrieval, independent approval and isolated recovery. Monitoring exists to expose failures and incomplete work.

**A valid signature or matching hash does not prove that a backup is malware-free. A successful isolated restore does not authorize production republication.**

## Initial experimental edition

The [initial edition summary](docs/releases/initial-experimental-edition.md) identifies the verified ZIPs, operating sequence and remaining boundaries. The shortened observation is closed; no continuous-coverage or production-readiness claim is made.

## Current status

PR #8 is merged (main `71e54a7`). Both CI jobs (PHP 8.1/8.3) passed. The candidate remains `0.1.0-dev.1`, an experimental prototype; no formal release was made. Recurring trust operations and the corrected final-v2 ZIP acceptance are included in the current evidence. Previously tested ZIPs and historical tags remain unchanged.

Dedicated generated-data tests cover the admission gate, capture, real experimental S3 storage with fixed Version IDs and retention evidence, separate reader/writer roles, test signing, isolated restore and result registration. Fresh installation, candidate upgrades and settings/history preservation have also been tested. These results do not establish production-wide deployment or physical host independence.

Three daily trial slots (October 19–21, 2026) are complete. At the operator's request, observation closed after **68h28m24s** on October 22 at 12:24:21 JST. Gaps of approximately 4h26m and 4h24m remain. This is not a 72-hour pass or continuous coverage. See the final assessment above.

## Start here

- [Current capabilities and gaps](docs/releases/current-status.md), [production pilot acceptance checklist](docs/guides/production-pilot-acceptance.md), and [release readiness](docs/releases/initial-release-readiness.md).
- [Installation, operation and stopping](docs/guides/initial-release-setup.md), [candidate ZIP installation](docs/guides/plugin-candidate-install.md), and [external deployment planning](docs/guides/external-deployment-plan.md).
- [Onboarding through recovery](docs/guides/onboarding-recovery.md), [real SSH/S3 integration](docs/guides/onboarding-ssh-s3.md), and [ZIP acceptance](docs/guides/onboarding-zip.md).
- [Signing key rotation, revocation, handover and recovery media](docs/guides/trust-lifecycle.md).
- [Development setup](docs/guides/development-setup.md), [tools](tools/README.md), [evidence index](evidence-public/README.md), and [contributing](CONTRIBUTING.md).

Some detailed guides are currently in Japanese. The English README is the primary entry point; the Japanese README retains the detailed historical feature index.

## Verified scope and limitations

| Area | Dedicated verification | Remaining boundary |
|---|---|---|
| Capture | Write suspension/draining/release, admission checks, paired assets | All actual site write paths and production deployment |
| Storage | Exact S3 versions, retention evidence, separate access roles | Every credential escalation path and production-wide protection |
| Recovery | Signature gates, fixed-version retrieval, isolation, result registration | Clean generation selection, credential replacement and safe republication |
| Operations | Read-only status screens, SSH transfer, systemd, watchdog, notifications | Independent physical failure domains and complete production onboarding |
| Trust lifecycle | Current checkpoint enforcement, reviewed atomic updates and pinned SSH deployment; generated-data recovery and ZIP checks | Global revocation and administrator-resistant rollback protection are not implemented |

The initial real-site candidate approval has a documented expiry of **October 25, 2026, 18:15:47 JST**. Test signatures do not renew it. Expiry must never be bypassed. Production PHP/SMTP/HTTPS maintenance is separate from Resilience acceptance evidence.

## Relationship to Ozeki Database Backup for S3

Both products are intended to work independently. Neither requires or automatically installs the other. Backup for S3 focuses on backup and restore; Resilience covers the recovery asset set, retention, independent trust and recovery decisions.

`packages/backup-core` is the maintenance source for shared PHP database dump components. Consumers use pinned versions and contract tests. MariaDB CLI streaming integration and legacy backup compatibility remain incomplete. This work does not change Backup for S3 or the shared component. See [product boundaries](docs/spec/04-product-boundaries-and-initial-release.md) and [shared component status](docs/releases/shared-core-adoption-status.md).

## Development and evidence

Development uses Ubuntu under WSL and dedicated generated-data environments. Never commit credentials, private keys or captured production content. Published summaries are not the signed original evidence. Docker is not certified here as safe containment for malicious code.

Keep environment failures, test infrastructure defects and product defects separate. Do not overwrite failed observations with later successes. Do not repeat completed S3 writes or uncertain operations merely to refresh evidence.

License: GPL-2.0-or-later.

## Current trust at recovery entry (prototype)

Recovery entry now requires a root-owned independent current-generation/revocation checkpoint. Whole old trust bundles are rejected when they conflict with that checkpoint. Missing or expired checkpoints block recovery. Administrator provisioning is required; online global freshness is not implemented. See [deployment and limits](docs/guides/current-recovery-trust.md). The closed shortened observation does not provide duration evidence for this later gate.

Registry updates now have a reviewed compare-and-swap entry with atomic replacement and sticky revocations. See [administrator update procedure](docs/guides/trust-registry-update.md).

Reviewed registry deployment is also available over pinned, fixed-command SSH; see [SSH deployment and unknown-outcome handling](docs/guides/trust-registry-ssh.md).

SSH-deployed current trust has been connected to the actual recovery entry and offline WordPress/MariaDB restore in a dedicated generated-data exercise. Old/revoked bundles were blocked before retrieval. Storage responses were local fixtures, not a new real-S3 trial. See [scope and results](docs/guides/trust-ssh-recovery.md).

The SSH-installed registry/recovery-entry integration also passed with actual experimental-S3 fixed-version GETs and offline WordPress restoration. Old/revoked bundles were blocked before object requests. See [real-S3 scope and results](docs/guides/trust-real-s3-recovery.md); a credential-isolating test broker is used.

Frozen trust-lifecycle candidate ZIPs passed installation/update and retention checks; see [acceptance and exact hashes](docs/releases/trust-final-zip.md). Still a prototype, separate from 72-hour final evaluation.

Recurring registry refresh, per-host readback, failure and expiry procedures are documented in the [operating runbook](docs/guides/trust-recurring-operations.md). Registry refresh never renews a signed approval. Six operational-connection checks passed from the corrected final-v2 development kit. The closed observation covers its original scope, not these later additions.

Additional [two-VM recurring SSH verification](docs/guides/trust-recurring-ssh.md) passed seven checks: per-host readback, partial authentication failure, actual expiry and explicit refresh recovery, with signed approvals unchanged. No new S3/restore or 72-hour coverage claim.

[Recurring trust final ZIP acceptance](docs/releases/recurring-trust-final-zip.md): fresh install, same-version update, settings/history and unchanged approval retention verified; prototype only, separate from 72-hour evaluation.
