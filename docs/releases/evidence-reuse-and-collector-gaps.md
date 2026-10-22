# Evidence reuse and collector pilot test boundaries

October 22, 2026; baseline PR #8 (`71e54a7`). This is a retrospective review of recorded evidence, not a rerun, independent reproduction, or audit of every historical test. Nine representative JSON summaries were read and fingerprinted in the private review record. No production changes or new VM experiments were performed.

## Assessment

Earlier work has value where it establishes a specific invariant or real integration boundary. It does not collectively certify an arbitrary production installation. Test counts, repeated successful screenshots and consecutive PRs are not additional coverage by themselves. Preserve historical results, but consolidate their future use into the claim matrix below.

An important gap: the real-SSH/S3 onboarding exercise explicitly uses **DockerBackend for capture**. SSH supplies inventory and EC2 S3 authorization. It is not evidence that a collector VM can remotely suspend and capture a production site through a least-privilege interface. This is a product integration gap that can first be addressed in a dedicated generated-data environment; creating a production EC2 instance is not a prerequisite to discovering it.

## What existing evidence is useful for

| Claim / evidence | Established within recorded scope | Not established | Reuse and rerun trigger |
|---|---|---|---|
| Paired capture, draining and release — [capture](../../evidence-public/first-site-capture.json) | Generated WordPress/MariaDB real dump, attachment pairing, failure/lease-expiry handling and source release | All live writers, remote host adapter, arbitrary mounts/engines, five-minute production stop limit | Keep as adapter contract regressions. Rerun affected cases when capture/backend/writer coordination changes. |
| Admission and daily transitions — [admission](../../evidence-public/daily-capture-admission.json), [onboarding](../../evidence-public/onboarding-ssh-s3.json) | Failed initial/late checks block capture/PUT; duplicate invocation does not add work; stored vs pending approval | Unattended production schedule or a complete remote capture path | Reuse state-machine assertions; exercise only new transport/process boundaries and changed persistence. |
| Exact S3 versions and recovery — [onboarding](../../evidence-public/onboarding-ssh-s3.json), [trust/S3](../../evidence-public/trust-real-s3-recovery.json) | Real experimental S3 fixed-version operations, retention metadata and offline restored generated content | New instance-profile policy, current production IAM, complete object-loss resilience, malware-free content | Preserve exact-version integration baseline. A new IAM principal needs a scoped policy/transport acceptance; it does not require repeating every restore/UI test. |
| Current trust and expiry — [operations](../../evidence-public/trust-recurring-operations.json), [two-VM SSH](../../evidence-public/trust-recurring-ssh.json) | Reviewed transitions, partial deployment, actual expiry/recovery, unchanged approvals, per-host readback | Physical fault independence, substitute operator access, universal revocation, root-resistant rollback | Reuse contract tests and fixtures; rerun when authority format, updater, SSH protocol or platform boundary changes. New host provision needs one configuration acceptance. |
| Reports/systemd/watchdog — [generated deployment](../../evidence-public/generated-systemd.json) | Dedicated guest service stop/restart/reboot and report/UI recovery | Every new host distribution, production alert response, shared infrastructure survival | Treat the reusable mechanism as one capability. New payload schema needs schema/staleness checks; OS/service deployment changes need targeted lifecycle checks. Do not multiply full reboot suites merely by report label. |
| Packaging and retained state — [final-v2 ZIP](../../evidence-public/recurring-trust-final-zip.json) | Exact bytes, actual Plugin_Upgrader and browser checks; retained settings/history; packaged external tests | New database migration, resumed in-flight operation, all older upgrade versions | Plugin ZIP is explicitly byte-identical to the preceding candidate. Repeating installation adds little evidence without changed bytes/runtime/migration risk. Kit changes still need manifest and affected-tool checks. |
| Three daily slots / time — [daily summary](../../evidence-public/initial-release-three-days.json) | Three generated-data daily round trips; periodic capacity/trust/delivery observations in original scope | Continuous 72-hour coverage, automatic signing, newer features, production RPO/RTO | Use the final shortened-observation assessment. Report elapsed time, daily success and gaps separately; do not restart it after each PR. |

## Were earlier repetitions justified?

Progression from a local model to a real process, actual SSH, a separate guest reboot, actual S3 and exact packaged bytes can reveal different defects. Those transitions were useful where the dependency boundary actually changed. Examples of concrete learning include SSH outcome classification, dedicated runtime-directory/Python-path fixes, and the final ZIP fixture aging past the report freshness limit.

However, the current records do not prove that every repeated SSH/systemd/browser cycle was necessary. Several report features reuse the same mechanism. Repeated installation of identical plugin bytes is mainly confirmation, not new feature evidence. The latest fixture-aging failure improved test reliability; it was not a newly discovered product expiry defect. Historical browser startup remains unexplained and must not be called fixed solely because later runs passed.

Future work should consolidate fixtures and make the changed boundary explicit. This is a process correction, not a retrospective claim that all earlier work was either necessary or worthless. Identifying exact duplicate assertions across the entire test corpus would require a separate code-level audit; this review does not claim to have done that.

## New collector work: smallest useful experiment

| ID / type | New uncertainty | Minimum experiment and acceptance | Why previous evidence is insufficient |
|---|---|---|---|
| C1 — Product adapter | Remote capture without broad host/Docker control | Two dedicated generated-data endpoints with pinned SSH and an allow-listed capture protocol. Capture DB/files, bind attempt/config IDs, drain/release all declared writers; deny arbitrary command/path/site requests. No production keys or data. | Existing capture is DockerBackend; inventory SSH is not capture SSH. |
| C2 — Product failure boundary | Collector loss while source is paused, or response lost after an action | Interrupt the collector/connection at controlled points; source-side owned lease/release must remain effective without collector cooperation. Preserve unknown outcome, refuse duplicate work, require inspection before retry. | Process separation creates a failure mode not established by a local success path. Reuse existing state/lease assertions instead of rebuilding them. |
| C3 — Environment-specific IAM | New writer/profile and actual S3 route | After separately authorized provisioning, use a generated canary in an authorized test prefix: PUT/version receipt, independent reader check, writer read/delete/retention-change refusal. Never test destructive operations on retained production data. | Old-role success does not prove new-role policy. Current JSON syntax checks are not IAM simulation. |
| C4 — Environment capacity | 2GiB VM, streaming load and stop budget | First representative generated workload, measure peak RSS, CPU/credits, disk, bytes/time and release time. Use declared upper-bound sizes and interruption cases. Require documented headroom and no accepted run beyond the stop bound. | Earlier small fixture success and historic 458MB capture are not current performance sizing. Actual site measurements require separate authorization. |
| C5 — Placement/coexistence | Dedicated service identity, mounts and dm impact | Inspect unit/path/permissions; run only generated status traffic in dedicated test setup. On authorized target deployment, compare bounded resource use and existing service health without stopping FTP/MySQL. Confirm no demand DB or FTP data dependency. | dm's inventory proves current state, not future coexistence. No need to recreate every UI screen or outage campaign. |
| C6 — One final connection check | Replacement adapter through existing approval/recovery chain | After C1/C2 pass, one generated set through the new capture path, existing storage, independent approval and existing isolated restore/result registration. Match asset hashes and source/attempt identities. | Existing end-to-end test used the old backend. Reuse its harness and recovery assertions; do not turn this into six separate feature projects. |

C1/C2 are the immediate development questions; C3–C5 depend on a chosen, authorized placement. C6 closes the new connection once. Network console review is a placement prerequisite, not a plugin security test. None of these experiments has been executed by writing this plan.

## Keep product and environment separate

Product requirements are authenticated transport, bounded/owned source control, consistency checks, least-privilege integration, durable unknown outcomes and independent recovery authority. An adapter declares its supported site profile; unsupported writers/assets must remain unverified.

EC2 type, VPC/AZ, public IPv4, dm, resource quotas, operating hours and budget are **provisional pilot choices**, not universal plugin requirements. The pilot's same-AZ/shared-account limitations must be disclosed. Different hosting and credential models should be revisited after the initial release without removing the protection invariants.

## Decision rule for any future test

Before execution, record: requirement/claim; what code, configuration or boundary changed; prior evidence reused; failure injected; expected side-effect counts and independent oracle; acceptance criteria; artifact/code/config hashes; scope and cleanup. If nothing relevant changed and no uncertainty is resolved, do not rerun the manual integration. Automated regressions may still run in CI, but are not reported as a new capability.

A mocked callback proves a local contract; real-service receipts prove that integration; a report screenshot proves display; a same-version reinstall proves persistence of that version. Do not substitute one kind of evidence for another. Retain failures, skips and missing observations. Further tests are justified by a changed risk, not by the number of successful runs.

The original observation was closed at the operator's request after 68h28m24s; see the [final assessment](shortened-observation-final.md). No additional stored sets were created to close it. No production configuration, IAM, VM or retention change follows from this review.
