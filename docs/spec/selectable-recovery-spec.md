# Selectable recovery assurance: initial specification

English primary | [日本語](selectable-recovery-spec-jp.md)

2026-10-22. **Design only; not implemented or accepted for production.** Baseline: the prototype after PR #9, read with the current implementation guides. This specification refines the [operating model](maintainer-operating-model.md) and [tabletop](maintainer-tabletop.md); it does not alter existing approval gates. Backup for S3 remains an independent product. No runtime, shared component, infrastructure, or existing signature is changed.

## 1. Product objective and scope

Target WordPress maintenance technicians who need recoverable backups without routine manual approval of every backup. Support different budgets and deployment capabilities. A separate always-on recovery EC2 instance is not required.

A successful check is useful even on the source host. Describe its verified scope and failure-domain dependence rather than assigning an overall security score. A same-host result must not be represented as independent evidence against compromise of that host.

Initial supported capture profile remains a single WordPress site with known writers and locally scoped assets; additional configurations require explicit support. Provide choices of verification placement, not a promise that every hosting environment supports every option.

## 2. Selectable configurations

| Configuration | Checks it can establish | Remaining boundary |
|---|---|---|
| Same-host content checks | Inventory, fixed versions, hashes, required metadata | No actual restore or boot claim |
| Same-host isolated restoration | Restore into separate DB/files, boot and specified functional checks | Host loss and host administrator compromise are shared risks |
| Same-host disposable environment built from kit | Kit completeness and repeatable construction on that host | May share kernel, credentials, caches and hidden dependencies |
| Existing separate host | Restore and construction without the source host, within the tested setup | Independence depends on actual identities, storage and administration |
| On-demand temporary environment | Build from kit and restore without a permanent recovery server | Requires available provisioning, access, capacity and dependency artifacts |

Offer same-host, existing-host and temporary-environment profiles. Verification depth is separate from placement. Users may combine routine local checks with occasional independent reconstruction. Do not block recovery solely because independent verification is absent; enforce actual integrity, missing-asset and hold/revocation failures. Current gates remain unchanged until a separately reviewed implementation exists.

Same-host execution must use a separate DB and files, restricted identities, resource/disk limits and controlled networking. Prevent mail, cron, payments and other external writes. Refuse a test if required isolation cannot be established; retain completed lesser checks without calling them restore passes. Never restore over production as a test.

## 3. Verified recovery editions and evidence

A verified recovery edition means **specified tests passed for specific immutable versions**, not malware-free or universally recoverable. S3 presence, object name, prefix or tag is not sufficient proof.

Record: edition ID and asset scope; DB/file pairing; bucket/key/version and hashes; retention evidence; kit/runtime version and dependency inventory; test policy/version, time, results and skipped/unknown checks; verifier identity and placement/failure domain; signature and trust reference; and separately recorded current eligibility.

Keep dimensions separate:
- Storage: pending / complete / failed / outcome unknown.
- Verification: untested / content checks passed / isolated restore passed / kit reconstruction passed / failed, with placement and scope.
- Eligibility: eligible / pending review / incident hold / revoked, with reason and authority revision.
- Evidence freshness and authority availability: current / stale / unavailable.

Preserve historical test results when eligibility changes. A former pass remains a historical observation, not current permission. Retain older generations for clean-point selection; latest-only recovery is not a requirement.

Source credentials cannot confer independent verification or write authoritative eligibility. Same-host verification can still produce scoped results, but source administrator compromise may forge them. Stronger claims require an appropriate independent verifier; a signature by itself does not add independence.

Future automatic attestations are distinct from existing human-signed approval. Do not automatically renew existing signatures or silently reinterpret them. Version policy and evidence formats; compatibility and migration remain to be designed.

## 4. Incident hold, freeze and quarantine

| State | Automatic actions within enrolled policy | Human decision |
|---|---|---|
| Normal | Capture, checks, register qualifying editions | Scope and important changes |
| Warning | Preserve evidence; hold new candidate promotion | Transient fault or suspected incident |
| Suspected compromise | Hold candidates; request agreed write/egress freeze; route later captures to quarantine | Scope, shutdown impact and investigation |
| Investigation | Preserve history; offer separately authorized isolated inspection/restoration | Affected time window, candidate and credential changes |
| Resume | Start a new policy/baseline epoch after approval | Reopen writes, normal capture and production publication |

Do not equate network failure alone with compromise. Enrolled rules must identify signals, automatic actions, recipients and escalation. Avoid automatically extending an incident freeze to unrelated sites or an AWS account.

Freeze writers may include admin/REST, cron, SSH, queues and outbound actions. Actual complete coverage is not established by the current prototype. Distinguish requested, confirmed and unconfirmed freeze. Do not trust a compromised source's acknowledgement as independent proof.

Separate the bounded capture pause from an incident freeze: capture-pause timeout/release must not clear a deliberate incident freeze. Record independent reasons/ownership; reopening writes requires the incident policy's release authority. Collector-loss safe release for the capture pause is still an unresolved integration item.

Detection time is not compromise onset. Exclude later captures from ordinary recovery and permit retroactive holds on earlier editions. Do not delete suspected data or rewrite original test evidence.

Quarantine uses a separately permissioned bucket or equivalent boundary, not a label alone. Normal recovery credentials cannot read it. Hold status changes access eligibility even when old bytes remain in their original retained location; physical migration is not required to apply a hold. Unknown routing outcomes must not fall back to trusted storage/promotion. Capture for evidence is optional and bounded; it must not defeat a freeze.

Ordinary recovery and automatic publication stop for held editions. A separate authorized forensic path can inspect suspected assets without treating them as eligible. Unaffected editions may become selectable after incident review. Production publication always requires explicit approval.

## 5. On-demand recovery kit

Persist the kit and recovery catalog in separately controlled S3 storage. A different bucket alone is not independence from account-wide administration compromise. Define each deployment's identity and account boundary.

Kit contents: versioned recovery tools; pinned runtime/build recipe and required artifacts; asset and edition catalog; signed test evidence; generation/hold/revocation records; dependencies and credentials references; setup, isolated restore and cleanup procedures. No embedded long-lived private credentials. Protect historical versions and verify exact versions.

Before disaster, retain outside the source/control host:
- A means of accessing the storage and necessary decryption/provisioning capabilities.
- A trusted public-key fingerprint or other trust anchor not learned solely from the retrieved kit.
- Named primary/substitute operators and emergency policy.

Recovery: authenticate from a trusted device -> verify kit and authority state -> create a clean temporary environment -> select eligible edition -> fixed-version retrieval -> isolated restoration -> human checks -> explicit publication. Stop/delete temporary resources afterwards. Missing required artifacts or keys are reported, not hidden by access to the old host.

The scheduler and normal capture/verification work still need execution somewhere. Avoid a mandatory permanent recovery VM; do not claim that storing a kit eliminates ongoing execution or all costs.

## 6. Authority unavailable: safety and recoverability

Publish holds/revocations and readback receipts to independent recovery storage during normal operation. Failure to publish is an incident, not proof of no hold. A previously cached catalog cannot prove that no later revocation exists. Historical signed records need a trusted minimum revision where available; currentness cannot be manufactured from a local clock or re-signing old bytes.

Keep normal authorization and a prospective emergency path distinct:
- Fresh trusted eligibility and valid authorization: normal isolated recovery.
- Authority unavailable: disclose last known revision/time and uncertainty; a preauthorized, scoped emergency policy may permit isolated reconstruction after operator acknowledgement.
- Known revoked edition or compromised signing authority: do not authorize using that proof. Investigate other independently established editions or rebuild.
- Missing storage access/decryption: reconstruction is unavailable until those prerequisites are recovered.

Emergency isolation is not permission to publish. Define substitute authority, selected versions, reason and unresolved risks before production publication. No automatic reuse of quarantined data. A new emergency path is **not implemented**; current expired/missing registry still blocks before GET.

Tradeoff: strict freshness minimizes use of stale authority but can prevent recovery of sound data; unconditional offline acceptance can reuse revoked data. The proposal enables bounded isolated work while keeping the uncertainty visible and publication explicit.

## 7. Automated, bounded verification

Provisional starting cadence, not an SLA:
- Every backup: inexpensive storage/content verification.
- Roughly weekly and on material changes: isolated restoration, on the selected host profile.
- Roughly monthly and on kit changes: construction from kit, optionally on a temporary separate host.

Users can adjust depth/cadence to risk, size and cost. These tasks are not required to run on EC2. Measure duration and cost before defining a budget. Changed schedules are not evidence of checks having occurred.

Automate provision -> retrieve kit -> verify -> restore -> test -> record -> cleanup. A cold-start test may supply only declared access/trust bootstrap inputs; document caches and downloaded dependencies. Same-host tests must not borrow undocumented production config.

Bound concurrency, resource size, duration and retries; reconcile unknown outcomes before retry. Use resource ownership tags/IDs and an independent expiry cleanup mechanism. Report cleanup leftovers and missed tests; a budget alert alone is not a spending cap. Test workloads use the chosen protected data only within explicitly authorized environments and isolation.

Display last success per check type and edition, latest failure, age, missed schedule, authority state, cost and residual resources. Absence of a successful scheduled test is not itself proof of compromise.

## 8. Existing capability versus required change

| Requirement | Existing reusable capability | New or unconfirmed work |
|---|---|---|
| Scoped recovery editions | Fixed S3 versions, hashes/retention, signatures, isolated recovery, result registration | Unified edition contract, placement labels and automated attestation authority |
| Same-host option | Dedicated isolated fixture tests and recovery components | Supported installer, isolation/resource checks, site-safe end-user workflow |
| Eligibility and incident state | Generation/revocation enforcement, admission checks, status reports | Site-wide incident state, warning/freeze policy, retroactive holds and UI |
| Freeze and evidence quarantine | Writer-coordination primitives and storage adapters | Complete production writer coverage, pause/freeze ownership, restricted SSH capture, quarantine routing and IAM profiles |
| On-demand recovery | Recovery toolkit artifacts, setup drafts and SSH deployment primitives | Self-contained supported kit bootstrap, external operator entry, catalog publishing and cold-start provisioning |
| Authority outage | Mandatory local current registry, atomic updates, readback and rollback checks | Emergency authorization policy and stage-specific access; no current bypass |
| Automated verification | Restore results, daily records, reporting, timers and notifications | End-to-end verification scheduler/provisioner, bounded spending, independent cleanup |
| Less manual approval | Technical admission and independent signature primitives | Policy-based automatic attestations, expiry semantics, migration and operator UX |

Reuse does not mean production acceptance. Earlier dedicated tests establish only their recorded scopes; no new tests were run for this specification. Historical observation closed after 68h28m24s with two gaps; it is not a 72-hour pass or evidence for this design.

Environment constraints (memory/disk/network, AWS access), test infrastructure defects (fixture/browser orchestration), and product gaps above must stay separate in reports.

## 9. Proposed acceptance questions before implementation approval

- Can a maintainer select a same-host profile and see useful successful checks without an unsupported independence claim?
- Are incomplete/mismatched/held editions excluded regardless of placement, while intact historical results remain visible?
- Can warning, actual freeze confirmation and quarantine routing failure be distinguished?
- Does capture timeout release leave an incident freeze in place?
- Can a kit reconstruct using only declared bootstrap inputs, with the source/control host absent?
- Does unavailable authority remain visibly unknown rather than silently current?
- Are unknown cloud operations reconciled and orphan resources cleaned within a defined limit?
- Can routine successful operation avoid per-backup human approval without renewing old approvals?

Before coding, decide supported isolation/runtime profiles, automatic-freeze signals/actions, eligibility authority and emergency scope, quarantine/storage trust boundaries, actual data handling, and measured budget/cadence. These are open design decisions, not newly imposed production settings.
