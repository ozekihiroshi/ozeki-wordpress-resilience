# Signing trust lifecycle: rotation, revocation, handover and recovery media

Status: experimental operational specification, October 22, 2026. Baseline: merged PR #6 (`55ea023`). The original exercise reused the signature primitive. Recovery entry points now additionally require the [independent current-trust checkpoint](current-recovery-trust.md). See [generated-data results](../../evidence-public/trust-lifecycle.json).

## Separate approvals and responsibilities

- Capture operator confirmation authorizes a capture configuration for a limited period; it is not a signature over a recovery set.
- Recovery approval binds an exact document hash, site/set, generation, public key and validity interval. It does not certify absence of malware or approve republication.
- The signer keeps private keys outside the source WordPress and storage writer. The recovery operator independently obtains and checks trust information. One person can fill both roles in a pilot, but this is not independent personnel control.
- Record the operator, reason, site/set, old/new key fingerprint, old/new document hash, minimum sequence, approval expiry, storage retention limit and each recovery host/media receipt. Never record private keys or passphrases in the ledger.

## Renewal without changing the signing key

1. Before expiry, independently retrieve the exact pinned object versions and recheck size/hash/retention and the intended recovery scope. Do not merely change a date in the old document.
2. Review known contamination or compromise reports. If evidence is missing or the key may be compromised, stop renewal and use the incident procedure.
3. Issue a new immutable approval with a higher sequence and bounded expiry. Never extend approval beyond the shortest asset retention deadline. Preserve the previous document and evidence as history.
4. Verify the new signature and document hash in a controlled recovery environment, then explicitly deploy the new trust bundle. Existing verifier formats have per-set pins; they are not a global key registry.
5. Update recovery media and record a successful readback before retiring a usable copy. A missed renewal blocks recovery authorization; do not disable expiry checks.

The real-site candidate has a documented expiry of October 25, 2026, 18:15:47 JST. This lab neither renewed nor inspected that production approval. Recheck its authoritative record before any real renewal.

## Planned key rotation

1. Generate a new key on the operator-controlled signing system, separate from source and reader hosts. Use the established production key standard; the lab's RSA2048 keys are disposable fixtures, not a production policy change.
2. Compare the new public fingerprint through a trusted independent channel. A document delivered by the source server or a signature by a potentially compromised old key is not sufficient authority to replace the trust root.
3. Re-review the set and issue a new approval with the new key and incremented sequence. Do not alter S3 assets just to rotate a signing key.
4. Build a new generation directory containing the public key, exact approval, signature, pin and verification receipt. Check the complete bundle before selecting it as current. Never overwrite individual current files while recovery is running.
5. Explicitly update every recovery host's trusted selection and generation record; account for offline hosts. Keep old public verification material as historical evidence. Prevent old private keys from issuing new operational approvals after retirement.
6. Record which hosts/media have acknowledged the change. Until all required copies are updated, report a partial rollout rather than complete rotation.

These are operator steps. The project does not yet provide an atomic rollout command, distributed acknowledgment registry, or enforcement of signer retirement.

## Suspected compromise and revocation

1. Suspend new approvals and recovery initiation using the affected key. Preserve incident evidence and pending/unknown operation records; do not automatically resend, re-sign or restore.
2. Mark each affected trust pin revoked on controlled recovery hosts and reject new work there. Updating one file does not revoke every copy of that key. Inventory all sets, hosts and offline media using it.
3. Treat approvals issued under the potentially compromised key as requiring independent re-review. Determine the incident interval from evidence; do not infer cleanliness from signature validity.
4. Distribute a replacement trust root through an independently authenticated process, issue new approvals only after review, and update recovery media.
5. Already running or completed restores are not undone by pin revocation. Investigate their status separately and preserve uncertainty. The existing gate does not continuously poll revocation during execution.

**Known product limitation:** the verifier accepts an operator-selected old active pin together with its original key/document/signature while the old approval is still valid. A complete trust-directory rollback is not detected. Minimum sequence protects only against documents checked against a newer trusted pin. Neither that minimum nor a same-bundle signature establishes that the pin itself is current.

Operational mitigation: before initiating recovery, reconcile the media/host generation and revocation state with an independently maintained current ledger. If that source is unavailable or inconsistent, stop and escalate; do not assume an old USB is current. This is a manual prerequisite, **not an implemented mandatory software check**. A protected current-generation authority and rollback-resistant distribution/check at the recovery entry point remain product work.

## Operator handover

1. Inventory sites, approved sets, retention/expiry dates, recovery host access and all media; identify the new accountable person.
2. Prefer a new signing key for the successor and the rotation procedure above. Do not routinely give the previous operator's private key to the successor. Revoke the old operator's administrative access separately; changing a WordPress account does not remove host or signing access.
3. Deliver public trust information and compare fingerprints through an independent authenticated channel. Record who confirmed them and when.
4. Have the successor perform an isolated generated-data exercise using their own access and the current trust bundle, including rejection of old approval material. Only then record handover as operationally complete.
5. An emergency encrypted-key escrow copy is distinct from routine handover. Custody, release approval and the passphrase channel must be documented; this prototype does not enforce two-person control.

The present lab simulates a successor directory on the same OS account. It does not prove a second person's identity, access revocation or independent device operation.

## Recovery media / USB update

1. Confirm the actual removable-media target and available space before writing. Do not format media or select a drive solely because it has a familiar letter.
2. Create a new generation directory. Copy the complete public trust bundle and, if required by custody policy, only an encrypted private-key backup. Do not put its passphrase on the USB or into logs/chat.
3. Keep a current manifest of expected filenames and hashes outside the media. Read every file back, compare public fingerprint, approval hash, sequence and expiry with the independently held current record.
4. Test decryption and sign a generated challenge using the key read from the copy, verifying with the independently held public key. In a real drill use a separate controlled machine; do not overwrite production approval files to prove that a key works.
5. Treat interrupted copies, wrong passphrases, missing files, mixed generations or stale approvals as incomplete. Preserve the last verified copy and failure evidence. Do not declare a new copy current until all checks pass.
6. Record the media generation and verification time, safely eject it, and keep it offline. Retire stale copies according to incident/retention policy. Preserve required public historical evidence; secret erasure on flash media requires a separate media-handling decision.

The lab uses directories, not a mounted USB. It uses PKCS#8/AES-256-CBC with 600,000 iterations and a generated in-memory passphrase, then removes both plaintext and encrypted disposable private keys. It does not validate physical media durability, safe removal, hardware isolation or a real person's passphrase recovery.

## Dedicated acceptance exercise

Run from a repository checkout, with a new private workspace path:

```sh
python3 tools/trust-lifecycle-cases.py \
  --workspace /path/to/new-generated-trust-lab \
  --output /path/to/trust-lifecycle-result.json
```

The workspace must not exist. No production input is accepted, no network/storage adapters are invoked and no downloaded asset is executed. A fresh real OpenSSL signature is checked by `protected-first-site-set.authorize`; retention and storage identities are synthetic declarations, not newly verified AWS observations.

Twelve checks passed: initial approval, new key/generation, rejection of old document under current pin, revocation, expiry, sequence floor, mixed key/pin, altered document, wrong passphrase, encrypted readback signing after plaintext-key removal, successor bundle verification and incomplete copy rejection. The separate old-bundle rollback case is **accepted by the low-level signature primitive in the original exercise and recorded as an unmet entry-gate requirement at that time**, not included in the passing count.

The test does not repeat SSH/S3/systemd/ZIP/restore coverage and does not modify the ongoing 72-hour observation. Production keys and the existing USB remain untouched.

## Classification and next implementation boundary

| Category | Result / next step |
|---|---|
| Environment | No new environment failure in this exercise; production PHP/SMTP/proxy maintenance stays in operational records |
| Test infrastructure | Same-machine generated fixtures and simulated media; prior unexplained browser startup issue remains separate |
| Product | Recovery entry now requires a protected local current checkpoint; global revocation distribution and atomic rollout remain unimplemented |
| Human operations | Real successor identification, separate-machine recovery, actual USB rotation and production renewal remain unperformed |

The independent local entry check is now implemented; see its deployment requirements, expiry behavior and race limitations in [current recovery trust](current-recovery-trust.md). Do not claim that another successful restore resolves this trust gap.
