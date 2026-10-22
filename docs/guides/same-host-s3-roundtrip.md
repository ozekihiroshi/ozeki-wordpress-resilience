# Shared isolated runtime with experimental S3

English primary | [日本語](same-host-s3-roundtrip-jp.md)

## Changed boundary

This acceptance connects the shared two-container preparation/inspection/restore contract to the existing real S3 adapter. It reuses the generated WordPress capture, SSH inventory, daily publication, separate test signing, current-registry gate, recovery worker and result registration. It does not add an alternate approval path or change production configuration.

The dedicated harness is tools/same-host-s3-roundtrip-cases.py. It extends the previous local roundtrip harness with the existing onboarding SSH/S3 integration. The root-owned current registry is a disposable fixture in a private /run directory. Existing operator SSH configuration is used for scoped role authorization without copying keys. The writer and reader remain my-ssm-role and OwrM1RecoveryReader; only the existing experimental lock bucket is used.

## Acceptance criteria

- Admission failures and duplicate requests must cause no extra capture or S3 writes.
- Two generated assets are stored with non-null Version IDs and actual retention evidence.
- Unsigned and invalid-signature paths must not read remote assets or start recovery.
- Publication, approval and recovery GET receipts must identify the same two versions.
- The original capture workspace is unavailable during recovery.
- The prepared, DB-started and running inspections must pass before their respective restoration steps.
- WordPress post, media hash and HTTP checks must pass; daily state must become restore_verified and results must be registered.
- Owned local resources must be removed. Retained S3 objects are not deleted.

This is a small generated-site acceptance, not general-site support or independent-host verification. SSH inventory is not restricted SSH capture. Retention/signatures establish the tested integrity and authorization properties, not absence of malware. Historical environment/test-infrastructure issues and the closed shortened observation are not reclassified by this trial.
## Result: 2026-10-22

All 9 acceptance checks passed. The two assets total 29,811,484 bytes. There were exactly 2 acknowledged PUTs and 6 fixed-version GETs (publication, approval, recovery), with matching version/size and actual GOVERNANCE retention evidence. Unknown PUTs: 0. All three runtime inspections passed; post/media/HTTP checks passed; registration was recorded and daily phase became restore_verified. Local test resources were removed. A duplicate recovery request performed no additional transfers or restore.

[Sanitized evidence, asset locators, retention and implementation hashes](../../evidence-public/same-host-s3-roundtrip.json). No new environment failure, unexpected test-infrastructure failure, or product defect was observed. The only new integration code is the dedicated harness; production restore and approval code did not need additional changes. Earlier local-runtime defects remain in the preceding report. This run does not claim malware-free contents or production recovery approval.
