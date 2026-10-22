# Updating and deploying the independent recovery trust registry

Prototype administrator procedure. See [recovery-entry checks](current-recovery-trust.md). This tool updates one local recovery host; it does not distribute trust between hosts or authenticate an upstream signer automatically.

## Responsibilities and review

The signing custodian confirms the current public-key fingerprint, approval-document fingerprint, minimum sequence and revocations through an independent trusted channel. The recovery host administrator reviews those exact values and installs the registry. A hash identifies reviewed bytes; it is not proof of origin. Never derive authority solely from the selected recovery bundle or the compromised source site.

Keep the tool and its imported modules root-managed and unwritable by recovery operators. Do not grant arbitrary sudo access to this tool or to a writable checkout. All supplied candidate contents are an administrator decision. The candidate contains public trust metadata only, never private keys or passphrases.

Before first use, the administrator explicitly creates `/etc/owr-trust` as root:root, mode 0755. No command in this work has provisioned production directories or registries. The destination is fixed at `/etc/owr-trust/current-recovery.json`; there is no path override. First provisioning requires the explicit expected value `absent`. A corrupt existing file cannot be silently treated as absent.

## Inspect, review, validate, apply

1. Inspect the installed registry using the trusted installation:

   ```sh
   python3 /trusted/tools/update-current-recovery-trust.py --inspect
   ```

   Record its exact `sha256` and revision outside the recovery bundle. Inspection allows an expired registry so the operator can plan a refresh; it does not authorize recovery.

2. Prepare a complete candidate using the schema in the recovery-entry guide. Increase `revision`; preserve all revoked keys and all existing set identities. Retire sets with `status: revoked`, not removal. Revoked set identities cannot be reactivated. Use a new reviewed set identity for a genuinely new set. Changing an approval hash or key requires a strictly higher `minimum_sequence`; refreshing expiry alone may retain the sequence. The issued time must not move backwards. The candidate must be currently valid and its validity interval must not exceed 24 hours.

3. Calculate the candidate SHA-256, compare its full contents with the custodian's independent record, and retain the approved hash. Substitute reviewed values in the following commands (do not run literal placeholders):

   ```sh
   sha256sum /reviewed/candidate.json
   sudo python3 /trusted/tools/update-current-recovery-trust.py \
     --candidate /reviewed/candidate.json \
     --candidate-sha256 REVIEWED_CANDIDATE_SHA256 \
     --expected-current-sha256 INSPECTED_CURRENT_SHA256
   ```

   Without `--apply`, the tool validates but does not replace the registry. It may create the protected lock file. For a separately approved first installation only, replace `INSPECTED_CURRENT_SHA256` with `absent`.

4. Apply the **same** reviewed candidate and expected current hash by adding `--apply`. The tool takes a nonblocking exclusive lock, rechecks the current hash, validates the transition, writes and syncs a temporary file in the protected directory, rechecks freshness/current state, atomically replaces the destination, syncs the directory and reads the result back. Successful JSON has `applied: true`, the revision, new hash and prior hash.

5. Inspect again and retain the result in the administrator's operational record. Confirm the selected approved recovery set against the new registry. Updating the registry does not approve an asset by itself and does not initiate retrieval or restore. Update each host individually; a host with an older checkpoint may continue to accept it until expiry. Record which hosts have received the update.

## Failure and retry decisions

| Situation | Result and next action |
|---|---|
| Candidate/hash changed, old revision, sequence decrease, removed revocation/tombstone, expired/future candidate | Reject; preserve installed registry; obtain a new reviewed candidate |
| Another updater holds the lock | Reject without waiting; inspect after it finishes, then review again |
| Installed hash differs from the reviewed hash | Reject; do not just substitute the new hash and retry without reviewing its contents |
| Temporary write/sync or replacement fails before replacement | Existing registry remains; removeable temporary file is cleaned up; inspect before retry |
| Directory sync or readback fails after replacement | Outcome is uncertain; new bytes may already be installed. Do not blindly resend or copy the old registry back |
| Installed registry missing/corrupt/unprotected | Recovery fails closed; investigate before any administrator repair. Do not delete evidence to make bootstrap succeed |

For an uncertain outcome, run `--inspect`: if the installed hash is the reviewed candidate hash, verify its contents and retain the error record; if it is the previous hash, investigate the storage error and then revalidate; if it is another hash or inspection fails, stop for administrator investigation. A directory-sync failure means durability across a crash was not established even if current readback succeeds. After restart, inspect again. A repeated apply with the old expected hash is rejected once the new registry has been installed.

The old registry is not automatically extended when updating fails. It remains usable only under the existing recovery-entry validity rules; after its expiry, recovery is blocked. To correct a bad update, issue a **new higher revision** rather than restoring an old file. Removing revocations or lowering sequence floors is intentionally not offered as an override.

## What rollback resistance means here

The supported update entry rejects rollback relative to the installed registry and preserves revocations. It uses a single atomic registry, avoiding a two-file watermark/registry crash window. It does **not** detect a privileged administrator directly replacing/deleting both local state and history, restoring a whole-host snapshot, modifying code, or changing the clock. Trusted administrator/host and an external review record remain assumptions. Hardware monotonic state, a remote independent authority and authenticated cross-host distribution are not implemented. Never describe this as protection against root-level rollback.

## Dedicated verification

`tests/test_update_current_recovery_trust.py`: 20 generated-data tests passed in a temporary root-owned `/run/owr-update-*` directory, removed after the run. Cases cover bootstrap/update/readback, validation-only, reviewed-hash mismatch, obsolete revision, sequence downgrade, changed key without generation advancement, sticky revocations and tombstones, expiry refresh, lock contention, symlink/corrupt current state, injected pre-replacement and post-replacement failures, and deployed revocation rejected by the actual current-trust checker. This does not claim an actual power-loss, full-host rollback, real S3 or physical USB test.

Environment: no new host failure, no production/FTP/MySQL changes. Test infrastructure: injected filesystem failures and synthetic public metadata; root-only suite skips when root is unavailable. Product: local safe update entry implemented; privileged rollback and distributed freshness remain explicit limits. The separate 72-hour observation continues unchanged.
