# Recurring current-trust operations (prototype)

This procedure uses the existing reviewed registry updater and pinned SSH endpoint. It does not add a scheduler, renew signatures, deploy production services or change the 72-hour observation. The registry is an independently administered local checkpoint, not an online global revocation authority.

## Responsibilities and three separate clocks

| Record | Who controls it | Renewal rule |
|---|---|---|
| Signed recovery approval | Independent signing operator | Explicit new approval only, after reviewing the assets, retention and incident status. Never extend by changing a registry. |
| Current-generation/revocation registry | Independent trust administrator | Explicit reviewed higher revision, with a validity interval of at most 24 hours. Preserve all revocations and sequence floors. |
| Daily capture operator confirmation | Capture operator | Its separate admission policy applies; this is neither a signature nor a registry refresh. |

One person may hold multiple roles, but signing/administrator credentials must not be placed on the captured WordPress host. Name a primary operator and a substitute and record the handover. The substitute must be able to access independent records without relying on WordPress.

Initial operational proposal: review the registry twice daily (12-hour interval) with a 24-hour maximum validity, and open an operational incident if a refresh remains unconfirmed six hours before expiry. These are manual operating targets, **not implemented timers or notifications**. Choose shorter intervals if the incident response requirement demands them. Incident revocation is immediate operator work, not something to defer to the next routine refresh.

## Before each refresh

1. Obtain the authoritative revision, key fingerprints, approval hashes, sequence floors and revocations from the independently held administrator record. Do not derive authority from a WordPress status screen or an old USB copy alone.
2. Check the signed approval's expiry independently. If it has expired, do not edit its document, signature or pin. Obtain a separately reviewed new signed approval, or leave the set unavailable. Registry freshness alone never grants recovery approval.
3. Review the complete intended host list and pinned host keys. Record intentionally excluded/retired hosts and how their recovery entry is disabled. An unreachable host is not implicitly excluded.
4. Produce the next candidate under the [existing update rules](trust-registry-update.md). A routine refresh keeps approval/key hashes, sequence floors and revoked entries unchanged, and advances registry revision and validity. Record why the administrator still considers those approvals current. The updater enforces transitions but cannot decide whether that human review actually happened.
5. Hash the exact candidate bytes; preserve that file and the review record. Do not regenerate it between hosts. Do not overwrite signed approvals to match it.

## Deploy and reconcile each host

Use the [pinned SSH setup](trust-registry-ssh.md). `HOST_CONNECTION.json` is a reviewed local connection file, and the two hash placeholders below must be actual independently reviewed values.

```sh
python3 tools/trust-registry-ssh.py inspect --connection HOST_CONNECTION.json
python3 tools/trust-registry-ssh.py validate --connection HOST_CONNECTION.json \
  --candidate REVIEWED_REGISTRY.json --candidate-sha256 REVIEWED_CANDIDATE_SHA256 \
  --expected-current-sha256 INSPECTED_CURRENT_SHA256
python3 tools/trust-registry-ssh.py apply --connection HOST_CONNECTION.json \
  --candidate REVIEWED_REGISTRY.json --candidate-sha256 REVIEWED_CANDIDATE_SHA256 \
  --expected-current-sha256 INSPECTED_CURRENT_SHA256
python3 tools/trust-registry-ssh.py inspect --connection HOST_CONNECTION.json
```

Review each host's predecessor separately: deployments may start from different revisions. Never automatically substitute a newly observed expected hash into a failed request. `absent` is only for reviewed initial provisioning, never for bypassing corruption or lost history.

Record outside the hosts: rollout ID, reviewer and review time, candidate hash/revision/issued/expiry, intended hosts and pinned key references, each previous hash, apply outcome, readback hash/revision/time, and unresolved incidents. Keep failed attempts alongside later resolution; do not replace them with a successful row.

A host is **deployment confirmed** only when a post-apply inspect returns the reviewed hash and revision. All intended hosts must be confirmed before the rollout is called complete. Inspect is a readback, not a signature check or proof that recovery is currently possible: it intentionally permits reading expired registries. Check candidate validity and approval expiry at the time of use; the actual recovery entry still enforces both. A saved receipt can become stale and cannot authorize later recovery.

## Failure and expiry decisions

| Situation | Required action / remaining protection |
|---|---|
| Communication fails before a result is known | Mark host unknown; reconnect and inspect. No blind apply retry and no rollback. |
| Inspect matches the reviewed candidate | Record bytes confirmed. If the original failure was directory fsync, crash durability is still unproven; repair storage and inspect again after restart before closing that incident. |
| Inspect matches the predecessor | Record not applied, investigate, revalidate freshness and reviewed expected state before explicit retry. |
| Inspect shows another hash, or cannot be read | Keep unresolved; investigate independently. Do not overwrite or remove the registry to force bootstrap. |
| One host remains old | Mark rollout partial. Old unexpired state can still authorize recovery there, including a subsequently revoked set. Quarantine/disable that recovery entry through trusted administration if reachable; otherwise report revocation containment incomplete until resolved/expired. |
| Refresh fails while old registry is valid | Existing entry rules remain; there is no automatic validity extension. Escalate according to the operational deadline. |
| Registry expires | Recovery blocks before retrieval. After independent review, apply a fresh higher revision against the inspected old hash, then verify readback. Preserve the expiry/failure record. |
| Signed approval expires | A refreshed registry does not fix it. Explicit new signing approval and registry transition are required; no automatic signing or expiry edits. |
| Incorrect update or revoked set | Issue a reviewed higher revision. Revocations remain sticky; do not restore old files or reactivate a revoked set. Use a newly reviewed set where appropriate. |

A host or privileged administrator compromise, clock changes and whole-host rollback remain outside this checkpoint's protection. No atomic multi-host rollout or global immediate revocation is claimed. Physical USB rotation and real substitute-operator identity/access checks require separate human acceptance; directory tests do not satisfy them.

## Targeted dedicated verification

Six operational-connection tests use existing updater, SSH endpoint inspect logic and actual recovery entry with generated real signatures. Registry paths are redirected **only inside the tests** to root-owned temporary `/run/owr-recurring-*` files representing two hosts. Network/GET/restore callbacks are local fixtures; there is no SSH transport, real S3, actual OS reboot, power-loss or elapsed-time observation claim in this new test.

Confirmed: refresh preserves signed bytes and exact per-host readback; fresh registry cannot extend expired approval; failed refresh followed by expiry blocks before retrieval and reviewed refresh permits entry; partial revocation remains visibly incomplete; post-replacement uncertainty reconciles by inspection while stale retries reject; expired registry inspection is not readiness. Expiry is injected without changing the OS clock. Existing real-SSH and real-S3 evidence remains separate and is not repeated.

Evidence: [trust-recurring-operations.json](../../evidence-public/trust-recurring-operations.json). No production state, original approvals, USB, observation assets or private production keys are touched. Tests clean their temporary directories.

- Environment: no new environmental failure established.
- Test infrastructure: injected replacement/fsync faults and simulated expiry/two-host paths; historical unexplained browser startup issue remains separate.
- Product: no runtime change needed for these six connections. Manual refresh/host reconciliation and the local trust boundary remain operational limitations; this is still a prototype.

Additional [two-VM recurring SSH verification](trust-recurring-ssh.md) passed seven checks: per-host readback, partial authentication failure, actual expiry and explicit refresh recovery, with signed approvals unchanged. No new S3/restore or 72-hour coverage claim.
