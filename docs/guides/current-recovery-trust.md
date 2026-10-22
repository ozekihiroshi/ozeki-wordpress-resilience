# Independent current-trust checkpoint at recovery entry

Status: prototype, October 22, 2026. This adds an independent **local administrator checkpoint**, not an online global revocation service. Existing signatures, approval expiry, asset hashes and fixed-version checks remain required.

## Required deployment

A recovery host administrator maintains `/etc/owr-trust/current-recovery.json`. Recovery operators and backup writers must have no write access to this file, its parents, or the installed recovery code. Run recovery under an unprivileged account. The CLI, environment and selected bundle cannot override this path. Do not obtain the authoritative values from an untrusted USB or source server alone.

The administrator independently confirms current key/document fingerprints, sequence and revocations with the signing custodian. Provision a root-owned directory (0755) and root-owned file (0644). All parent directories must be root owned and not writable by group/others; symlinks are rejected. Prepare a complete replacement in that protected directory, verify it, then atomically rename it over the current file. Never partially edit the live file. Use the [reviewed update entry](trust-registry-update.md): it enforces increasing revisions, sequence floors and retained revocations relative to the installed registry. Privileged direct replacement and whole-host rollback are outside this local boundary.

Example schema (placeholders are not deployable values):

```json
{
  "format": "owr-current-recovery-trust-v1",
  "revision": 2,
  "issued_at": "2026-10-22T00:00:00Z",
  "expires_at": "2026-10-22T01:00:00Z",
  "revoked_key_sha256": [],
  "sets": [{
    "site_id": "your-site",
    "set_id": "your-set",
    "status": "active",
    "minimum_sequence": 2,
    "public_key_sha256": "SHA256 of exact public.pem bytes",
    "approved_document_sha256": "SHA256 of exact signed approval document bytes"
  }]
}
```

Use timezone-qualified timestamps and a validity interval no longer than 24 hours. List compromised key fingerprints in `revoked_key_sha256`; set an entry's status to `revoked` to block that set. Omitted or duplicate sets are rejected. Rotation requires the current exact approval hash and key hash and a nondecreasing sequence floor. A changed document or key cannot be accepted merely by copying its old matching pin.

Existing installations without this file now fail closed. The administrator must provision it before recovery; this change does not install production trust, refresh it automatically or grant permissions. Missing, unreadable, malformed, expired, future-dated, overly long-lived or unprotected authority information blocks recovery. Offline operation is allowed only while the independently provisioned checkpoint remains valid. Do not extend it without independently reconfirming the authoritative state.

## Entry points and races

- `first-site-daily-restore.py`: check before destination creation/S3 adapter construction, again against the selected snapshot before retrieval, and immediately before the restore call. Record the checkpoint in the result. A changed/expired authority during retrieval prevents restore; downloaded evidence is retained.
- `first-site-daily-recovery-worker.py`: default production dispatch checks before persisting a running attempt. A known pre-start rejection therefore does not create a fictitious interrupted attempt. The recovery function also checks again.
- `run-independent-recovery.py`: check before approval verification (including verify-only) and again before output/container work.
- `approved-queue-restore.py`: check before asset access and again before returning verified assets. Callers must not treat previously returned bytes as indefinitely authorized.
- `pilot/restore-s3-candidate.py`: check before output creation and again before container work.

Any checkpoint change between checks rejects the attempt, including unrelated entries; start a newly reviewed request. These are entry checks, not continuous cancellation of already running restoration. A revocation after the final check cannot retroactively stop work. Low-level signature validators are reusable primitives, not authorized standalone restore entry points.

## Verification and limits

Dedicated generated RSA signatures and a root-owned temporary registry under `/run` exercise the actual daily recovery gate. S3 retrieval and restore dispatch are synthetic counters: denied initial checks must create no output, construct no adapter, GET no assets and invoke no restore. Tests also cover a changed registry during retrieval and non-root read access with denied writes. No new real S3, Docker, production key or physical USB exercise is claimed.

Run the privileged permission suite only in a dedicated Linux lab:

```sh
python3 -m unittest discover -s tests -p test_current_recovery_trust.py -v
```

It skips outside a root-capable lab; a skip is not security evidence. Existing signature/worker regression suites isolate this dependency and are not counted as independent authority coverage.

Security assumptions: trusted OS clock, installed code, administrator and recovery host. Root/code compromise, a stale but still-valid administrator checkpoint, cross-host atomic distribution, automatic refreshing, offline immediate global revocation and physical operator/media independence remain outside the implemented guarantee. The stale-checkpoint window can be reduced by choosing shorter validity, at the cost of more frequent administrator confirmation.

Environment: no production settings, FTP/MySQL, keys or observation resources changed. A sandbox WSL invocation was denied; the authorized escalated invocation worked. Test infrastructure: generated transport/restore and dedicated permission fixtures, not a repeated full integration test. Product: local protected checkpoint enforcement implemented; global freshness/distribution remains outstanding.

Use `update-current-recovery-trust.py` for validation and reviewed atomic deployment; see [update and failure procedure](trust-registry-update.md).
