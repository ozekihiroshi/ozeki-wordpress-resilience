# Maintainer tabletop: three operating scenarios

> Historical design discussion: deployment and verification choices are refined by the [initial selectable-recovery specification](selectable-recovery-spec.md). That specification takes precedence where proposals differ; neither changes current runtime behavior.

English | [日本語](maintainer-tabletop-jp.md)

October 22, 2026. Design walkthrough against the [operating model](maintainer-operating-model.md) and recorded implementation boundaries. **No real users participated, no commands or faults were exercised, no seven-day trial or time measurement was performed.** Proposed automation is not shipped behavior. Existing approval/expiry/revocation gates remain unchanged. Baselines are Resilience after PR #9 and the verified Backup for S3 0.4.0 artifact, not the stale older checkout.

## Assumptions and accounting

One maintainer and a substitute, a supported single-site WordPress profile, known writers, local assets and no external queue. Use daily capture and 35-day retention as scenario assumptions, not newly authorized settings. Examine one site then five to expose repeated work; no capacity claim. Pause bounds, data-loss tolerance, budget and recovery targets require agreement.

Count decisions (policy, candidate, exception or publication choices) separately from operations (entry, inspection, transfer, commands). Decision bundles are not click counts. Do not invent total labor or RTO without measurement; distinguish hands-on time, system waits and external approval waits. Backup for S3 alone and Backup for S3 plus separately managed infrastructure/procedures are different comparisons. No mandatory pairing or automatic import is assumed.

## A. Enrollment and an unchanged healthy week

Inputs: new enrollment; no material configuration change, delivery failure, capacity problem or compromise signal during the week. Failed initial acceptance prevents entering the healthy-week branch.

| Step | Human | Proposed automation | Current boundary |
|---|---|---|---|
| A1 Scope | Confirm DB/files, dependencies, exclusions and writers | Inventory and flag unsupported facts | Profile, SSH inventory and preflight reusable; absence of all unknown writers cannot be proved by discovery alone |
| A2 Policy | Approve maintenance/data-loss bounds, retention/cost, primary/substitute and notifications | Produce a single deployment and permission proposal | Individual specifications exist, complete enrollment does not |
| A3 Provision | Authorize independent storage/recovery/signing identities through trusted administration | Install supported topology and verify pins/permissions/readback | Generator primarily covers inventory/reporting; key, systemd and capture wiring remain manual |
| A4 First acceptance | Review evidence and substitute's source-independent access; enable | Capture/release, fixed-version store, independent checks and isolated restore as one workflow | Dedicated pieces tested; restricted-SSH capture, collector-loss release and supported installation remain gaps. Unassisted current enrollment stops here |
| A5 Days 1–6 | Target: no normal action | Scheduled checks/capture/store/attestation/report; only safe retries | Daily machinery exists; current per-set approvals and short-lived registry operations still require humans |
| A6 Restore check/day 7 | Review exceptions and objectives once | Agreed periodic isolated test and multi-site summary | Worker/report pieces reusable; integrated unattended test scheduling, summary and new signing policy are incomplete |

Four enrollment decision bundles: scope; service/cost objectives; authority/ownership; acceptance/enablement. This does not mean four clicks or eliminate provider administration.

Conditional workload arithmetic: one newly approved daily set means seven approval items per site/week, or 35 for five sites. Adopting the existing twice-daily registry-review proposal means 14 refresh/review occasions per managed authority scope/week. Four host stages (inspect/validate/apply/inspect) give 56H processing stages for H intended hosts; batching may reduce commands but not automatically remove the human review requirement. Do not multiply shared registry reviews by site count. Capture-confirmation renewal adds work if its seven-day expiry falls within the week. Setup, failures, USB handling and restore-test operations are excluded from these counts. These are model counts, not measured observations.

Target: zero per-set human work in a healthy week and one consolidated review. The earlier five-site/ten-minute target remains unvalidated. This requires independently generated attestations, a new approval policy, authenticated registry distribution and consolidated presentation. A bulk approve button alone does not remove the judgment burden.

Backup for S3 can suffice where DB/media plus separately managed code/configuration and manual restoration meet the agreed requirement, and the maintainer coordinates media scheduling and writes. Standard daily scheduling covers DB; general automatic media scheduling and end-user Recovery Set creation are not provided by 0.4.0. Do not compare against an imagined install-and-daily-full-site baseline. Resilience's proposed value is owning that operational coordination and recovery preparation.

Verdict: current pieces support developer-assisted evaluation, not an unassisted enrollment/zero-touch week. A wizard alone cannot fix the current recurring human-approval contract.

## B. Source host lost

Inputs: yesterday's restore-tested candidate exists; source is unreachable this morning; independent storage, authority and recovery access remain available. Do not assume outage proves absence of compromise.

| Step | Human | Proposed automation | Current boundary |
|---|---|---|---|
| B1 Detect/triage | Assign owner; assess impact and compromise signals; route suspicious cases to C | Stale-report incident, last candidate/time and potential lost updates | Watchdog/freshness/outbox reusable; consolidated out-of-band operator interface missing |
| B2 Reconcile interrupted work | Distinguish a dead host from a broken connection | Preserve partial/unknown work, inspect PUT outcome, no blind replay | Unknown/duplicate handling reusable; actual restricted-SSH loss/release unverified |
| B3 Select point | Choose candidate based on capture time, data loss, validity and checks | Distinguish latest capture from latest usable candidate; enforce exact-set gates | Version/signature/registry checks reusable; yesterday's stored set may not be usable if the last approved set is three days old |
| B4 Reconstruct | Decide credential/configuration treatment and dependencies | Retrieve without source, isolate, reconstruct, test and register | Dedicated fixture recovery exists; supported general interface, reproducible runtime and workload containment remain incomplete |
| B5 Republish | Technician checks content; site owner accepts loss and live publication | Produce evidence and cutover proposal, no live side effects before approval | Documented procedure, not an implemented integrated live cutover |

At least four decision bundles: incident classification/ownership; point/loss; configuration/credentials; business validation/publication. Exceptions increase them. Automation removes repeated transfer/check/build bookkeeping, not content review or customer approval. No elapsed-time upper bound can be inferred; measure data transfer, provisioning, authority access and human delay separately.

Counterfactual: if only the collector/connection fails while source remains alive, source-owned release and service continuity take priority over restoration. Never depend on collector finally cleanup. Do not accept an unconfirmed-release capture or restart capture before reconciliation. This is a new integration boundary despite existing local lease tests.

Backup for S3 can suffice if independent S3 credentials and asset identifiers survive, and the technician has software/configuration plus a practiced DB/media reconstruction procedure. WordPress-only history is insufficient after source loss. Its dedicated restore evidence is not a general restore UI. Resilience's extra value would be integrating these preparations and making source independence an acceptance requirement.

Verdict: useful recovery components exist, but a substitute progressing through one independent interface remains an unfulfilled delivery promise. Successful S3 GET alone does not pass this journey.

## C. Suspected compromise and unavailable authority

Inputs: suspicious changes; recent captures may be contaminated; old S3 assets and recovery host remain readable; independent authority is unreachable. Local registry is expired or predates the incident and cannot establish that no revocation is missing. Distinguish unavailable authority from compromised authority; unknown cause does not rule either out.

| Step | Human | Proposed automation | Current boundary |
|---|---|---|---|
| C1 Scope incident | Assess source/collector/signer/authority exposure; authorize containment and evidence preservation | Deduplicate incidents, preserve history; never certify suspect new captures safe | Logs/notifications exist; incident determination, all-key revocation and credential rotation are not automated guarantees |
| C2 Preserve | Confirm protection through trusted storage administration | Do not advance automated deletion; retain candidates, attempts and uncertain records | Actual permissions/retention determine protection; no all-admin-account compromise guarantee |
| C3 Current authority | Try independent route/substitute; re-establish authority if compromised | Display unavailable vs expired vs explicitly revoked; no validity extension | Expired registry blocks current entry before GET even if signature verifies |
| C4 Choose branch | A: recover trusted authority; B: pre-designed independent offline process; C: remain blocked | Existing components can support A; do not invent B | B is not designed or implemented. Old USB cannot prove current revocations; worst-case recovery deadline cannot be promised |
| C5 Select/review | Investigate incident interval, keys and candidate; approve live publication separately | Appropriate isolation and evidence/difference report | No malware-free certification; authority recovery does not justify selecting latest automatically |

At least five decision bundles, with unbounded investigative branches; no credible labor/RTO cap. Automation can preserve records, list candidates, diagnose connectivity and perform authenticated checks. It cannot manufacture missing current authority.

An unexpired local checkpoint may still allow the existing entry to proceed, but does not establish globally current revocation or safety after a new incident. This scenario deliberately follows expired-checkpoint refusal. If offline forensic inspection is needed, define separate evidence-access, execution and publication authority/containment; do not disguise it as bypassing the current pre-GET gate.

With Backup for S3, independent access/assets may let a technician attempt manual recovery without this registry-service dependency. That does not establish clean content, absence of tampering or non-revocation. Resilience's stricter gate prevents use of stale authority while potentially reducing recovery availability. **A stricter gate alone does not establish greater overall resilience.**

Verdict: central unresolved product decision. Choose independently authorized offline authority, recovery/redundancy of the authority, or explicit acceptance of waiting. None is adopted here. No guarantee of recovery during compromise plus authority failure is justified yet.

## Design findings and next decisions

1. Define automatic attestation versus human authorization first: it determines healthy-week work and candidate age during loss. Reuse hashes, versions and daily state; do not silently reinterpret existing signatures.
2. Define authority-outage recovery before adding more gates: preserve existing behavior until an alternative has a defensible trust model.
3. Choose one supported deployment and independent recovery interface: reuse preflight, workers, durable notifications and result registration rather than exposing every internal component.
4. Keep restricted-SSH capture and source-owned loss release as explicit missing integrations; existing gate tests supply reusable assertions, not proof of the new transport.

Do not yet turn this into a feature sequence. First settle when the healthy system needs a human and what is authorized during authority loss, then conduct a paper walkthrough with an uninvolved maintainer. Record decision bundles, actual inputs/commands, assistance requests, hands-on time, waits and recovery outcome. This document is not that participant study or a new reliability test.

Do not replace a sufficient Backup for S3 workflow merely to add machinery. Ordinary backup/restore correctness improvements may belong there independently. Select Resilience when its source-independent protection/observation/recovery contract reduces more operational burden and risk than its added system creates.

Sources: [proposal and artifact baseline](maintainer-operating-model.md), [current authority operations](../guides/trust-recurring-operations.md), [recovery gate](../guides/current-recovery-trust.md), [operator flow](../guides/onboarding-recovery.md).
