# Current implementation and remaining work

> **Observation closed by operator decision:** 68h 28m 24s, three daily slots completed, two historical gaps retained. This is not a 72-hour pass. See [final assessment](shortened-observation-final.md).

Snapshot: October 23, 2026. Reconstruction preview `0.1.0-alpha.4` includes the protected three-page editor, request-derived Q, exact S3 generation receipt and independently approved reconstruction. The baseline is merged PR #13 (`328f6e2`) plus this release follow-up. See [alpha.4 downloads, visible editor and limits](alpha4-preview.md). It remains a prototype; historical evidence below is not a production-readiness claim.

The development kit now plans A/R/E/D/Q, reconstructs the three-page corporate subset, stores runtime/input/code closure as fixed experimental S3 versions, and gates retrieval/execution with independent signatures and the current registry. Two fresh private WordPress targets matched Q. This is CLI functionality outside the installable administration plugin; generic production setup and S3-first WordPress authoring are not complete. Prior short-observation and legacy Restore evidence are separate from this scope.

## Implemented and checked

| Area | Dedicated evidence | Remaining operational boundary |
|---|---|---|
| Capture and storage | Admission checks, write coordination, DB/file pairing, daily processing, fixed S3 versions and retention | Fit to every real site write path, remote capture backend and production rollout |
| Approval and recovery | Independent signatures, fixed-version retrieval, isolated restore, result registration and interrupted cleanup | Clean-generation selection, credential rotation and safe production republication |
| Current trust | Mandatory independent local checkpoint; stale/revoked bundles rejected; reviewed atomic updates and pinned SSH deployment | Trusted administrator/code/clock, manual refresh and per-host reconciliation; no root-resistant rollback or global immediate revocation |
| Status and monitoring | Read-only WordPress screens, SSH reporting, systemd restart/reboot, watchdog, test notifications | Independent physical failure domains and production monitoring placement |
| Setup and distribution | Configuration drafts, read-only deployment plan, dedicated placement, frozen ZIP installation/overwrite and state retention | No automatic complete production deployment or registry provisioning |

Trust lifecycle operations and their boundaries are described in [key lifecycle](../guides/trust-lifecycle.md), [current registry](../guides/current-recovery-trust.md), [SSH deployment](../guides/trust-registry-ssh.md) and [recurring operations](../guides/trust-recurring-operations.md). Local generation enforcement is now implemented; earlier lifecycle evidence showing old-bundle acceptance describes the historical signature primitive, not the current mandatory recovery entry.

## Initial edition boundary

The operator removed waiting for 72 hours as a prerequisite to initial-edition assembly on October 22. Use the [initial edition summary](initial-experimental-edition.md) and verified final-v2 artifacts. No unfinished restricted-SSH capture implementation is included. Observation has since closed at the operator's request after 68h28m24s; formal production acceptance is not implied.

## Observation is a separate assessment

Three generated-data daily slots (October 19–21) completed storage, pending-approval observation, test signing and fixed-version isolated restoration. Maximum three stored sets reached: do not add saves or repeat restores to refresh evidence.

Final audit: October 22 12:24:21 JST, 127 samples; three approved sets totaling 89,527,925 bytes; uncertain PUTs 0; 15 trust files unchanged; unresolved trial incidents 0; undelivered trial notifications 0. No new capacity/continuity issue or gap longer than two hours. This is a dated snapshot, not live telemetry.

Earliest 72-hour threshold: **October 22, 2026 15:55:56 JST**. The operator closed the observation early; it was not reached. Existing gaps of 4h26m33s and 4h24m8s remain. Daily success, elapsed time and observation coverage must be evaluated separately. Periodic audits are not continuous observation. Features added later, including PR #7 and PR #8, do not inherit 72-hour coverage from the older running trial.

At closure, battery sleep was restored to three minutes and AC no-sleep retained and verified. The scheduled follow-up is paused. Original plan and audit records are preserved.

## Classification of remaining issues

- **Environment:** the latest audit establishes no new capacity/continuity problem. Production PHP/SMTP/HTTPS maintenance is separate from product acceptance; unrelated database administration and other-host PHP issues are not resolved by this plugin.
- **Test infrastructure:** historical WebDriver startup timeout remains unexplained despite later successful runs. Python-path and dedicated SSH runtime-directory defects were diagnosed and corrected; initial failed evidence remains. PR #8 also fixes a test-only freshness baseline: a static report expired during browser setup, and the product correctly showed unconfirmed validity. The corrected final-v2 trial passed without changing approval expiry or production rules. This is distinct from the unexplained startup timeout. Shared kernels, development Docker socket and test S3 broker limit isolation claims. See [environment and infrastructure records](initial-release-environment-notes.md).
- **Product:** current-registry transitions and recovery checks are implemented, including the corrected SSH semantic-outcome classification. Global immediate revocation, administrator-resistant rollback, continuous cancellation after the final check and atomic fleet rollout are not implemented. All production write paths, independent placement, safe republication and ongoing operator coverage remain to be accepted.
- **Human operations:** actual substitute-operator access, physical USB rotation and production approval renewal are not satisfied by generated directory tests. The documented real candidate approval expiry remains October 25, 2026 18:15:47 JST; no test refresh extends it.

## Next work, without repeating completed trials

1. Follow the recurring trust runbook: independently review current authority, refresh explicitly, confirm every intended host, retain unknown outcomes and expiry incidents. Automated signing/approval extension is prohibited.
2. Use the [production pilot acceptance checklist](../guides/production-pilot-acceptance.md) ([Japanese](../guides/production-pilot-acceptance-jp.md)) to complete actual deployment/operating ownership decisions separately from dedicated tests. Do not broaden notifications or redo all SSH/systemd/ZIP tests without a changed requirement.
3. Use the completed shortened-observation assessment with its gaps and frozen scope. Power restoration and follow-up closure are complete. Formal release remains a separate decision.

## Evidence entry points

- [Onboarding through recovery](../guides/onboarding-recovery.md), [actual SSH/S3 connection](../guides/onboarding-ssh-s3.md), [onboarding ZIP](../guides/onboarding-zip.md).
- [Current trust real S3 recovery](../guides/trust-real-s3-recovery.md) and [frozen trust ZIP acceptance](trust-final-zip.md).
- [Daily admission](../guides/daily-capture-admission.md), [operator confirmation](../guides/recurring-capture-review.md), [generated systemd deployment](../guides/generated-systemd-lab.md).
- [Recurring trust connection checks](../../evidence-public/trust-recurring-operations.json). Six operational tests passed from the corrected final-v2 kit; see [exact ZIP hashes and acceptance](recurring-trust-final-zip.md). Acceptance reports were written after the ZIP freeze and are not claimed to be inside those bytes. CI ran 677 tests on each PHP job with 54 root-required skips; skips are not passes. Dedicated packaged tests provide separate evidence.

Backup for S3 is independent: no mandatory mutual dependency or automatic installation. Shared components and Backup for S3 are unchanged.

Additional [two-VM recurring SSH verification](../guides/trust-recurring-ssh.md) passed seven checks: per-host readback, partial authentication failure, actual expiry and explicit refresh recovery, with signed approvals unchanged. No new S3/restore or 72-hour coverage claim.

## Evidence reuse review

See [what earlier tests establish and the collector gaps](evidence-reuse-and-collector-gaps.md). In particular, earlier real-SSH/S3 onboarding still captured through DockerBackend. Remote least-privilege capture and loss of the collector while the source is paused remain new integration questions. Repeated unchanged ZIP/UI/lifecycle trials are not additional product coverage. Pilot infrastructure choices are provisional, not plugin requirements.

## Committed-generation inlet

See [contract and boundaries](../spec/rbr-generation-kit.md). The selected fixed generation is preserved in D; profile/runtime dependencies are protected through its horizon, with explicit copies where needed. Output awaits independent approval. This removes fixture-generator calls from the inlet, not the remaining production editor/coordinator integration gap.

Real S3 coordinator connection verified: scoped discovery, explicit new-version retention, concurrent commit/resume, unchanged generation reference into independent signed reconstruction, two private WordPress results matching Q. Evidence: `evidence-public/rbr-live-coordinator.json`; prototype CLI only. No production authoring hook or generic connector, no release or observation restart.

Final real-S3 coordinator ZIP lifecycle acceptance: PASS; see [results](rbr-coordinator-zip-results.md). CLI prototype, no production publication; shortened observation remains unchanged.

After PR #12: opt-in three-page save API and atomic source-WordPress projection implemented on codex/wordpress-protected-save. 25 dedicated HTTP/DB cases plus 9 input and 21 coordinator contracts pass. S3 is a contract double in this new integration test; real-AWS and normal editor/upload entry remain unverified. See docs/spec/rbr-wordpress-save.md and evidence-public/rbr-wordpress-save.json. No production activation or approval changes.

Follow-up: the same save API passed 25 checks against actual experimental S3 and private HTTP WordPress. No product runtime changes; the scoped test transport is new. See evidence-public/rbr-wordpress-save-s3.json. The preceding mock-only statement describes the earlier trial. Editor/upload entry integration remains incomplete.

Opt-in three-page editor now connects Edit links to the existing save API with durable frozen input and stored checkpoint. See docs/spec/rbr-wordpress-editor.md and evidence-public/rbr-wordpress-editor.json. Real browser + S3 double, not live S3 in this trial. Generic editing/upload integration and automatic migration remain incomplete.


## Edited-generation follow-up

See [the connection contract](../spec/rbr-editor-reconstruction.md). The API receipt selects the exact full snapshot; reviewed Q defines post-edit expectations. Parent provenance is retained but not fetched as a runtime dependency. Selected asset retention and all independent approval gates remain required. Generic Q authoring, production rollout and media-authoring integration remain outstanding. Historical evidence and frozen ZIPs are not retroactively updated.

Request-derived Q is now implemented for new bounded enrollments; [scope and legacy-state limitations](../spec/rbr-request-q.md). It does not automate independent approval.

Request-derived Q live follow-up: actual editor receipt -> experimental fixed-version S3 -> approval-pending v2 kit -> separate test signature -> two fresh WordPress logical-state matches. Browser21 and regression75 PASS. No manual/observed Q, production change or auto-publication. See `evidence-public/rbr-request-q-live.json`. Auxiliary Unicode canonicalization error belongs to the test helper, not the product.
