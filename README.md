# Ozeki WordPress Resilience

> **Target architecture — Immutable Assets, Deterministic Reconstruction:** regenerate business information from immutable assets and pinned rules/environment, without the original database. See the [design principle and logical-equivalence acceptance contract](docs/spec/immutable-assets-deterministic-reconstruction.md). The bounded corporate-site CLI now reconstructs a private WordPress from pinned A/R/E and a signed fixed-version S3 kit; a general production reconstruction engine is not implemented.


> **Observation closed by operator decision:** 68h 28m 24s, three daily slots completed, two historical gaps retained. This is not a 72-hour pass. See [final assessment](docs/releases/shortened-observation-final.md).

English | [日本語](RAADME-jp.md)

> **Experimental prototype — not a completed production protection product.**
> The installable WordPress ZIP provides administration and status screens. Capture, storage, signing, recovery, monitoring and notification delivery require separately configured external processes. Installing the plugin alone does not start protection.

The project aims to preserve recovery assets and recovery capability when WordPress is compromised or unavailable. It covers consistent database/file/queue capture, external storage, exact-version retrieval, independent approval and isolated recovery. Monitoring exists to expose failures and incomplete work.

**A valid signature or matching hash does not prove that a backup is malware-free. A successful isolated restore does not authorize production republication.**

## Initial experimental edition

The [initial edition summary](docs/releases/initial-experimental-edition.md) identifies the verified ZIPs, operating sequence and remaining boundaries. The shortened observation is closed; no continuous-coverage or production-readiness claim is made.

## Current status

The Git baseline is PR #10 (main `f5ebf8c`). This working candidate adds the subsequent bounded reconstruction, fixed-version S3 kit and independent signature gate. It remains `0.1.0-dev.1`, an experimental prototype, with no formal release or automatic production deployment. Older tested archives remain unchanged.

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

## Proposed next operating model

The [initial selectable-recovery specification](docs/spec/selectable-recovery-spec.md) describes same-host verification, optional independent verification, incident quarantine and on-demand recovery environments. **Design only: these are not shipped capabilities or relaxed approval rules.** [Japanese specification](docs/spec/selectable-recovery-spec-jp.md).

## Reconstruct design proposal

The [portable-content research and minimum Reconstruct specification](docs/spec/portable-reconstruct-minimum.md) proposes extracting business information independently of WordPress and generating an offline static preview. It separates preserved source material, supported conversion, missing dependencies and operator review. The specification is broader than the implemented increments below; the prototype's current approval rules remain unchanged.

The first [portable extraction increment](docs/guides/portable-content-extraction.md) is now implemented and checked with generated corporate-site data. It produces independent text/media/relationships and an explicit loss report; production enrollment remains unimplemented; the subsequent increment adds static previews.

The subsequent [local static preview increment](docs/guides/portable-preview.md) now builds review-only pages from saved portable material without WordPress. Missing/unsupported items remain visible; this is not publication authorization.

The [generated corporate-site roundtrip](evidence-public/portable-roundtrip.json) verifies extraction through offline preview with a valid image and original fragment-target positions. Three pages and one normalized image render after the source containers are removed; missing/unsupported items remain explicit.

## Portable extraction and preview: shipped scope

Experimental CLI tools are in **owr-development-kit**, not in the WordPress admin plugin ZIP. Installing the plugin alone does not add extraction or static generation buttons. A technician needs Python 3, a trusted WordPress CLI environment for extraction, and Docker with an explicitly pinned PHP/GD image for image normalization. The saved package can then be previewed without the original WordPress.

| Supported subset | Remaining limitations |
| --- | --- |
| Explicitly selected, published standard pages/posts; independent text and JSON | No general site discovery, draft/private/password-protected export or atomic snapshot guarantee |
| Referenced local attachment originals; normalized PNG/JPEG preview | Missing attachments, relative/resized image discovery and unsupported types require review |
| Page parents, internal links, featured/inline images, unique fragment positions | Theme layout, menus and taxonomy are not reconstructed; ambiguous/legacy fragment positions fall back with a notice |
| Escaped allowlisted body markup and local review pages | Forms, shortcodes, dynamic blocks, builders, custom metadata and active content are not recreated |

Markdown export, general import into a new WordPress, automatic publication, production enrollment and proof that content is uncompromised are not implemented. Losses remain in issues.json and the preview. Existing approval rules are unchanged. Keep packages and generated output outside the code directory; update the kit by extracting into a new directory and explicitly selecting that version. Do not overwrite private material or existing output. Plugin updates use the WordPress ZIP updater; this prototype retains the same development version, so the test covers overwrite and state retention, not a schema migration.

## S3-first reconstruction storage prototype

The following links record successive implementation stages. Their stage-specific limitations do not negate the later private reconstruction and signed-kit results below; production editor integration is still absent. Final frozen ZIP results, including separate environment/test-infrastructure findings, are in [the acceptance report](docs/releases/rbr-signed-kit-zip-results.md).

[Minimum implementation and evidence](docs/spec/rbr-generation-minimum.md): CLI/development-kit PHP components for S3-first originals, conditional site generations, retries and protected-copy renewal. Offline fault/race tests only; live AWS/IAM, WordPress editor/application and reconstruction are not verified or integrated. No production-ready claim.

Planning-only follow-up: [definition validator and deterministic plan generator](docs/spec/rbr-planner-minimum.md). Validates explicit pinned inputs and emits P offline; synthetic environment fixtures do not establish runnable WordPress or reconstructed-site equivalence.

- [Private WordPress reconstruction and logical comparison](docs/spec/rbr-wordpress-reconstruction-minimum.md) — prototype CLI lab; no automatic publication.

- [Fixed-version S3 reconstruction kit](docs/spec/rbr-s3-reconstruction-kit.md) — generated-data cold-cache experiment; private preview only.

- [Independent approval for S3 reconstruction kits](docs/spec/rbr-signed-kit.md) — prototype / 試作

## Signed S3 reconstruction kit: distribution scope

| Artifact | What it provides | What installation does not do |
| --- | --- | --- |
| WordPress plugin ZIP | Existing administration/status screens | Does not install or run the reconstruction CLI, enroll a production site, sign approvals or start external services |
| Development kit ZIP | A/R/E/D/Q planning, bounded private WordPress reconstruction, experimental S3 fixed-version kit and independent approval CLI | Does not contain private keys, credentials, runtime images, recovery data or a production setup wizard |

The supported reconstruction subset is company, services and contact pages with plain text, PNG/JPEG assets and explicit page/link relationships under pinned rules/environment. The approved S3 entry validates the complete fixed root receipt, signature, independently supplied key pin, current generation/revocation registry and expiry before retrieval and before execution. It revalidates downloaded code, assets, image inventory and plan. The unsigned S3 fetch CLI is disabled. Full received kits may be revalidated with `--received`; partially reconstructed WordPress targets are not resumed. Approval is never automatically extended and success never publishes the site.

A technician still provisions Python/PHP/OpenSSL and Composer dependencies (`composer install --no-interaction --prefer-dist` using the shipped lock file), a compatible isolated Docker runtime, S3 reader access, a trusted bootstrap, public-key pins and the independent current registry. The experimental S3 adapter uses the existing dedicated bucket and SSH role brokers; it is not a configurable general S3 connector. Account-separated signing was tested on one dedicated host, not independent physical hosts. Classic Docker image-store/architecture compatibility remains required. Arbitrary themes/plugins/forms, production WordPress save interception and end-to-end production S3-first authoring remain outside this tested subset. A valid signature is approval/integrity evidence, not proof of clean content.

Keep configuration, root receipts, approvals, trust pins, histories and assets outside the code tree. Extract a new development kit into a new directory and explicitly switch versions; do not copy private material into the package. Plugin updates use WordPress's ZIP updater. This same-version candidate verifies overwrite and preservation, not a versioned database migration. See [ZIP acceptance procedure](docs/releases/rbr-signed-kit-zip.md), [signed-kit operation](docs/spec/rbr-signed-kit.md) and [reconstruction comparison contract](docs/spec/immutable-assets-deterministic-reconstruction.md).
