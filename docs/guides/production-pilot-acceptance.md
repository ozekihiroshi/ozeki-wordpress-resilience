# Production pilot acceptance checklist

English | [日本語](production-pilot-acceptance-jp.md)

October 22, 2026, after PR #8 (`71e54a7`). This is a read-only planning record for experimental `0.1.0-dev.1`, not authorization to deploy or a production acceptance certificate. No production checks were executed to create this document. Dedicated evidence is historical and does not establish current site readiness.

## Record and decision rules

For each row, record a named owner, verifier, date/time, configuration version/hash, private evidence location and result: **unconfirmed**, **blocked**, or **confirmed for the stated scope**. Do not put credentials, private keys or captured content in this public checklist. Existing choices are inputs, not completed checks. A named owner is not a substitute for evidence; stale, failed or missing evidence must not be treated as ready.

Before enabling capture, complete rows A–F and H for the actual configuration. Before recovery, check G–I again for that exact set and current authority. Row J is required before production republication. A dedicated test, successful installation or completed 72-hour elapsed interval does not waive a row. Unsupported configuration blocks rollout until support and evidence exist; this document adds no runtime enforcement.

## Existing choices

- Initial candidate: `wp.ceri.link`, on community. Initial policy: once daily, 35-day retention. The lab schedule is not the production schedule.
- Existing AWS account and Ozeki as storage/signing/recovery operator were selected. dm is a watchdog candidate. Confirm actual placement, permissions and failure domains; these choices do not establish personnel or physical independence.
- Signing key custody: local PC and encrypted offline USB copy. Earlier readback succeeded; current-generation media and substitute-operator access still require confirmation.
- The documented real candidate approval expires **October 25, 2026, 18:15:47 JST**. Recheck the authoritative record. Registry refresh and test signatures never extend this approval.

## Acceptance matrix

Every row below remains **unconfirmed for the production pilot as a whole**. Existing narrower evidence remains valid within its recorded scope.

| ID / responsibility | Existing dedicated evidence | Required actual-site evidence or decision; stop condition |
|---|---|---|
| A — Site administrator: supported assets | [Initial capture profile](../spec/13-first-site-capture-profile.md), [capture adapter](first-site-capture-lab.md) | Confirm single-site Linux WordPress, DB version/engines, all files/mounts and exclusions. Inventory external state and queues; queue absence needs evidence. Unsupported DB engines, external mounts or unresolved dependencies block capture. Lab adapters are not arbitrary-host production capture commands. |
| B — Site administrator: every writer and release | [Capture consistency](../spec/11-capture-consistency-contract.md), [daily admission](daily-capture-admission.md) | Enumerate HTTP/REST, cron, CLI/SSH, deployments, direct DB/file writes and jobs; assign control owners. Agree maintenance window, maximum pause, acceptable data loss and recovery time. Prove drain, timeout and release paths for that configuration before enabling daily work. Unknown writer or missing release route blocks capture. |
| C — Storage administrator: IAM, retention and capacity | [Storage setup](production-storage-setup.md), [cost baseline](../spec/09-initial-site-and-cost-estimate.md) | Confirm actual bucket/account, versioning, 35-day retention, public blocking, encryption and writer/reader/admin separation. Record effective permissions, capacity margin, budget and retention-expiry/cleanup policy; protect uncertain operations and required evidence. Historical lab deletion refusal is not a current IAM audit. |
| D — External-process administrator: placement | [Deployment plan](external-deployment-plan.md), [setup and stop](initial-release-setup.md) | Assign capture, reporting, recovery, watchdog and trust custody hosts/users; confirm pinned host keys, service permissions, disk capacity and reboot behavior for actual placement. Record shared power/network/admin failure domains and effects on FTP/MySQL. Do not equate separate guests on one PC with physical independence. |
| E — Signing administrator: custody and renewal | [Lifecycle](trust-lifecycle.md), [recurring registry runbook](trust-recurring-operations.md) | Name primary and substitute operators and how they gain independent access. Record review cadence, approval expiry, current-registry expiry, required host list and per-host revision/hash receipts. Partial rollout is not complete; unknown outcome requires inspection. Expired/missing trust blocks recovery; no automatic signature extension. |
| F — Recovery operator: offline media | [Lifecycle/media procedure](trust-lifecycle.md), [earlier USB evidence](../../evidence-public/usb-candidate-trust-copy.json) | Confirm latest generation, public pin and encrypted key copy can be read back from the actual medium, with passphrase stored separately. Exercise substitute access and record receipt before retiring old usable copies. Directory fixtures do not prove USB durability or handover. |
| G — Recovery operator: exact-set recovery | [SSH/S3 integration](onboarding-ssh-s3.md), [current trust and S3](trust-real-s3-recovery.md) | Independently check current authority, signature, exact object versions/hashes, retention and complete asset relationship. Choose isolation appropriate to potentially infected code. Confirm restore results, interrupted resource ownership and retained pending/history records for the actual chosen set. HTTP 200 alone is insufficient. |
| H — Operations owner: schedule and failures | [Onboarding runbook](onboarding-recovery.md), [notification health](notification-health-lab.md) | Assign backup time/timezone, operator-confirmation review, primary/substitute response and escalation deadlines. Confirm actual alert receipt, missing/stale reports and undelivered handling; retain failed/unknown records and inspect before retry. Test-only delivery counts do not prove current production delivery. |
| I — Incident lead: clean generation and secrets | [Release gates](../spec/07-cyber-resilience-release-gates.md), [lifecycle](trust-lifecycle.md) | Establish incident interval and review contamination evidence independently. Decide credential/key replacement and trusted code sources. Valid signatures establish integrity/approval, not malware absence. Uncertain cleanliness blocks republication; preserve evidence. |
| J — Site owner: controlled republication | [First-site operator runbook](first-site-operator-runbook.md) | Record business/content checks, integration reconciliation, credential replacement, isolation exit, rollback and explicit publication approval. Isolated restore success does not authorize enabling live traffic or external side effects. |

## Issue classification and outstanding decisions

- **Environment:** actual host capacity, PHP/TLS/mail configuration, network/power independence and FTP/MySQL coexistence. The latest observation found no new capacity/continuity issue; it did not certify every production host.
- **Test infrastructure:** PR #8 corrected synthetic-report aging during setup; failed evidence remains. Historical browser startup remains unexplained. Shared physical host, development Docker access and S3 broker limit what the labs prove.
- **Plugin/external product:** dedicated gates, registry updater and recovery integration are implemented. Arbitrary-site production capture support, all real write paths and safe republication are not accepted. Global immediate revocation, root-resistant rollback, continuous cancellation and atomic fleet rollout are outside current implementation.
- **Operator decisions:** actual time window and objectives, host/owner allocation, substitute access, USB update receipts and review/response deadlines require named decisions. Do not label missing decisions as code failures or silently fill them with lab defaults.

## Bounded next steps

1. Complete the private evidence/owner record for A–F and H from current read-only inventory and operator decisions. List unsupported items before proposing production changes.
2. Only test a missing connection or changed condition; reference existing SSH/systemd/ZIP evidence instead of repeating it. Obtain any still-needed authorization for production changes or real notifications.
3. Use the [closed shortened-observation assessment](../releases/shortened-observation-final.md): 68h28m24s, three daily slots completed, two historical gaps retained. Daily success, elapsed time and coverage are separate; later PR features do not inherit coverage. Power restoration and scheduled follow-up pause are complete.

The current [status snapshot](../releases/current-status.md) and [final-v2 ZIP acceptance](../releases/recurring-trust-final-zip.md) remain separate from this production checklist. No new ZIP, tag, release, approval renewal or production deployment is created by these documentation updates.
