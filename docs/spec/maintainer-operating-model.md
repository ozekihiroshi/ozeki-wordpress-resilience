# Maintainer-oriented recovery service: design proposal

> Historical design discussion: deployment and verification choices are refined by the [initial selectable-recovery specification](selectable-recovery-spec.md). That specification takes precedence where proposals differ; neither changes current runtime behavior.

English | [日本語](maintainer-operating-model-jp.md)

October 22, 2026. **Proposal only: no implementation, policy relaxation, production change or new acceptance claim.** Baseline: Resilience initial experimental edition after PR #9. Backup for S3 comparison uses the verified 0.4.0 distribution, SHA-256 `4876c3971ebb5d7d4adf829a755c574216f22a20b5d6be9a74552ca00721fd62`, its readme/changelog and release validation records. An older checkout still describes 0.2.1/0.3.0; it is not the baseline. This is a scoped document/artifact assessment, not an exhaustive security audit.

## Start from failures and outcomes, not the existing feature list

Two complementary design lenses are useful: preserve the prototype's protection invariants, and ask what a maintainer still needs after a verified Backup for S3 backup. Neither lens mandates two installed plugins, a new shared API or moving features between products. The products remain independent. An optional future import contract would require its own design; existing backups are not automatically Resilience sets.

Proposed end state: a WordPress maintenance technician enrolls a supported site once; protected recoverable candidates accumulate without daily manual approval; loss or compromise of WordPress does not remove the maintainer's recovery authority or retained copies; the technician can reconstruct and inspect a selected candidate without the source; only an authorized person permits production republication. Every claim has a timestamp, scope and unresolved dependency.

Initial cohort: technicians who already administer Linux/WordPress and can approve AWS/storage policy, initially using one supported single-site profile with known writers, local assets and no external queue. A five-site walkthrough can expose repeated work; this is an evaluation scenario, not verified capacity or a customer limit. Shared hosting, multisite, externally stored media and transactional external services remain excluded until supported. This does not exclude restoring such sites manually with other tools.

## Backup for S3 baseline and the residual job

| Failure / need | What 0.4.0 already contributes | Remaining assurance, and its owner |
|---|---|---|
| Corrupt or incomplete upload | SQL/gzip/S3 integrity checks; media inventories; resumable set collection and verified manifest publication | Reuse these concepts. Checksums alone do not establish an application restore or clean content. Backup correctness belongs in Backup for S3 too. |
| DB/media relationship during updates | Recovery Set records, component observations, status; set creation requires developer integration | A linked set does not prove a common point in time. Coordinated capture or an explicitly weaker consistency claim is needed; this is a backup/restore correctness concern, not exclusive to Resilience. |
| Source host disappears | External DB/uploads objects and reconstruction information | Core/themes/plugins/configuration/runtime and an accessible source-independent restore path are still required. Reproducible installation sources may replace backing up every executable file if version and availability are verified. |
| Source is compromised | Integrity evidence and server credential integration; no guarantee that the source's identity cannot delete assets | Effective storage policy must prevent the source from destroying retained versions or changing protection. This depends on provisioned permissions/retention, not the plugin name. A correctly managed independent platform can also supply it without Resilience. |
| Source lies about success or stops | Local execution/schedule assessment and JSON; observations distinguish recorded checks | Independent observation is needed when the local observer is outside the trust assumption. Source-root compromise can falsify capture facts; remote SSH, hashes and signatures alone do not prove source truth. |
| Bad content has already entered a backup | Stored-component verification | Preserve older candidates and independently validate recovery. No implementation can infer malware absence from a valid signature alone. Clean-point selection remains incident work. |
| Recovery must happen without the site | Internal helpers and dedicated restore test evidence | A supported operator workflow, independent access to manifest/authority, credential replacement and isolated reconstruction. General recovery usability is legitimate Backup for S3 work too. |
| Entire storage admin/account or all operators lost | Not guaranteed by 0.4.0 | Separate account/control or offline recovery arrangements as required by the contract. Current Resilience prototype does not establish this either; do not imply same-account governance covers every compromise. |

Backup for S3 can be sufficient for an agreed DB/media backup-and-manual-restore need when an operator separately manages software/configuration, storage protection and recovery. Resilience earns its extra operational cost by delivering the source-loss/compromise recovery workflow, not by duplicating backup status screens or forcing its adoption for ordinary backups.

## Product shape and minimum boundaries

Offer a WordPress connector plus one externally managed **recovery service package** and an out-of-band operator/recovery interface. This is a proposed delivery shape, not a currently shipped installer or hosted service. The same service may be self-hosted or managed later; hosting/business model remains open.

A single service package can contain several processes/identities. Logical separation does not require a VM per process. Source credentials must not administer retained storage or signing authority. WordPress cannot authorize its own policy changes or recovery. The external operator path must work while WordPress is unavailable. Observer placement follows the failures being promised: a process on the same host cannot detect loss of that entire host reliably. A separate observer is required for that claim; monitoring every reporting process with another bespoke watchdog is not the default design.

Initial contract excludes source-root truth guarantees, all-account administrator compromise, malware-free certification, automatic business reconciliation and automatic republication. These exclusions must appear in enrollment, not only in a developer appendix.

## Four operator journeys

| Stage | Human decisions | Automatic work proposed | Outcome shown to operator |
|---|---|---|---|
| Enrollment | Asset scope and exclusions; tolerated pause/data loss; runtime dependencies; destination/retention/cost; primary and substitute; notification path; treatment of suspicious captures | Discover facts, identify unsupported paths, propose one configuration, generate/verify scoped deployment, establish pinned identity, perform first full capture/retention/readback/isolated-restore acceptance | Supported scope, unverified items, cost basis, last tested recovery candidate; explicit enable decision. Discovery cannot prove absence of every writer. |
| Normal week | One concise weekly review; approve material changes only; decide spending/retention changes when needed | Every scheduled capture checks config/writers/space; drains/captures/releases; stores exact versions; independently verifies evidence; runs agreed restore checks; records results; retries only safe operations | Latest capture vs latest validated candidate, coverage freshness, exceptions and assigned next action. No daily hash copying, CLI reconciliation or USB update. |
| Failure | Resolve ambiguous outcomes, unsupported changes, budget exhaustion or suspected compromise; approve a changed plan | Source-owned bounded release, safe readback reconciliation, bounded idempotent retries, durable incident queue, deduplicated notifications, preserve good prior candidates | What failed, service impact, last usable candidate, automatic actions already attempted, owner and one next action. Never hide failure behind an older success. |
| Recovery | Classify accident vs compromise; select recovery point after impact review; approve credential changes, business checks and republication | From external interface verify current authority and exact versions, provision appropriate isolation, retrieve/verify/reconstruct, test and report, track interrupted cleanup | Isolated candidate with checks and unresolved items. A separate explicit action approves live publication; no automatic DNS/traffic or external-side-effect activation. |

Normal-week walkthrough: enrollment acceptance on day 0; days 1–6 automatic scheduled capture and verification with no normal per-set human action; an agreed representative isolated restore during the week; day 7 one summary review. Backup/restore frequency follows site RPO/RTO, change rate and cost, not a universal weekly test guarantee. Configuration/key/destination changes interrupt this flow for review. A material site change can block new captures while leaving old approved candidates visible.

## Approval, signing and freshness redesign

Current prototype rules remain enforced until a new design is reviewed and tested. They include separate capture confirmation, signed recovery approval and a short-lived independent registry. The following is an alternative policy design, not permission to extend existing records.

1. A human approves a versioned **operating policy** at enrollment: assets, writer controls, destination, permissions, limits, validation rules, revocation authority and owner. Material changes require review. Mechanical unchanged-state checks should not demand a fresh human assertion every seven days merely because the timer elapsed; time-based reviews may remain for facts automation cannot establish.
2. An independent verifier may automatically issue an **evidence attestation** binding the exact versions, policy revision and performed checks. It asserts what was checked, not that a person approved that set or that it is clean. The signer cannot use WordPress's own success report as its sole evidence. This is new authority semantics, not an automatic extension of existing signed approvals.
3. Current-authority distribution/readback may be automatic under a separately authenticated authority, with sequence/rollback checks and durable receipts. Never mint freshness from an old USB copy, a repeating local timer or the compromised source. Automatic reissuance cannot revive expired authorization or revoked sets. The verifier/control service becomes a high-value component and needs scoped keys, audit, replacement and revocation procedures.
4. Distinguish unavailable current-authority information from a positive revocation. Preserve both facts and the older evidence. Current recovery gates still fail closed. If recoverability during authority-service outage is required, design a separately pre-authorized offline procedure with explicit bounded exposure and custody; no silent stale-cache bypass. If that contract cannot be made safe, disclose the outage dependency and retain manual review.
5. Human approval of production republication remains distinct from cryptographic attestation. Suspected compromise triggers investigation; neither automation nor the operator's button alone certifies malware absence.

This proposal deliberately does not promise zero ongoing security administration. It moves repetitive evidence transport/checking away from humans while retaining decisions that need business context or independent judgment. An encrypted USB can support key/authority recovery after enrollment, rotation or handover; daily set metadata should be replicated automatically to independent storage. No automatic writing to an offline USB is implied, and a stale USB cannot itself establish current authority.

## Reuse map and work that remains

| Existing implementation | Reuse | Needed change or validation |
|---|---|---|
| Profile/preflight/admission and operator-scope binding | Supported-profile checks, changed-config blocking | Enrollment orchestration and a small supported deployment contract; do not ask users to compose adapters |
| Capture/gate and daily state machine | Pairing, leases, unknown states, store/pending/restore separation | Real restricted-SSH backend and collector-loss/source-release acceptance remain missing |
| Fixed-version S3/retention and restore worker | Version-bound transfer, isolated reconstruction, result registration | Supported installation, independent operator entry and workload-specific containment |
| Current registry/updater/pinned SSH | Reviewed transitions, rollback floors, sticky revocations, per-host readback | Explicit new authority/attestation policy before automating freshness or approval |
| Notifications/watchdog/status transfer | Durable outbox, idempotency, freshness and recovery events | One incident view and consistent safe recovery actions; fewer normal notifications |
| Read-only WP UI and configuration generator | Presentation/validation foundation | Task-based overview and full external-service provisioning; current generator covers reporting/inventory, not complete capture/sign/recovery setup |
| Interrupted cleanup and retained journals | Ownership checks, inspect-before-delete | Automated safe branches; retain manual judgment for ambiguous ownership/outcomes |

Do not duplicate existing Recovery Set correctness work solely to differentiate the products. Shared implementation decisions remain separate changes; no shared-core adoption is authorized here.

## Burden budget and acceptance before coding broadly

Proposed usability goals, **not measured claims**: no routine per-backup approval or SSH commands in an unchanged healthy week; one weekly review, initially target at most 10 minutes for a five-site scenario; one enrollment workflow with no hand-written adapter code (provider authorization may remain); one external recovery workflow not requiring the failed WordPress installation. Measure installation/credential setup separately, record all assistance, and adjust targets based on independent trials rather than lowering safety checks to meet a stopwatch.

Evaluate three scripted walkthroughs first: (a) enroll and a normal week; (b) source lost plus collector disconnect; (c) suspect compromise plus unavailable authority. Record human decisions, repetitive actions, errors, support requests and recovery outcomes. Show policy scope, usable candidate and next action to an uninvolved maintainer; a screenshot or developer-assisted success is insufficient. A normal-week usability walkthrough is not a new time-based reliability certification.

Before implementation choose: first supported hosting profile; exact compromise/failure promise; whether automated evidence attestation is acceptable; authority-outage/offline policy; per-site/multi-site incident presentation. Provisioning/managed hosting can follow the minimum trust design. Do not start another sequence of per-screen SSH/systemd/ZIP experiments until one journey has a clear outcome and burden budget.

References: [initial edition](../releases/initial-experimental-edition.md), [evidence reuse](../releases/evidence-reuse-and-collector-gaps.md), [operator flow](../guides/onboarding-recovery.md), [deployment generator](../guides/external-deployment-plan.md), [current trust operations](../guides/trust-recurring-operations.md), [Backup for S3 0.4.0 source](https://github.com/ozekihiroshi/secure-s3-storage-for-wordpress/tree/v0.4.0). Historical operational guides contain dated trial instructions; they are not a finished generic installer.


[Three-scenario design walkthrough](maintainer-tabletop.md) — Design analysis only; no participant trial or implementation.
