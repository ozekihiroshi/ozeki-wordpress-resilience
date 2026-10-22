# Current trust lifecycle: final ZIP acceptance

Prototype `0.1.0-dev.1`, October 22, 2026. This is a development candidate, not a production release or the final 72-hour observation verdict.

## Frozen distributions

- `ozeki-wordpress-resilience-0.1.0-dev.1.zip`: SHA-256 `0537301b4f85b52cbd363c2b5909806b367c5a3d9bc40933325b31f88af51cfb` (35162 bytes).
- `owr-development-kit-0.1.0-dev.1.zip`: SHA-256 `7ec68ead36a57eb216336c928621cc3118ef4b51a6dd577679d1360f6ad6db13` (14646733 bytes).

The plugin ZIP is byte-identical to the PR #6-era onboarding candidate because this work changes external recovery tools and documentation, not WordPress PHP. The actual WordPress `Plugin_Upgrader` overwrite therefore tests same-version reinstallation and preservation, not a new database migration. The separate development kit contains the current-generation/revocation gate, reviewed atomic updater, pinned SSH transport, tests and English/Japanese documentation.

## Confirmed

- Fresh plugin installation and activation from the frozen ZIP.
- Existing-candidate overwrite through the actual WordPress updater, then deactivate/reactivate.
- Browser report/history display, administrator access, editor denial and read-only POST handling.
- Non-default settings, WordPress cron records, wp-config, pending requests and external history retained.
- Completed generated roundtrip records retained byte-for-byte; original source unchanged.
- Packaged external plan remains read-only; generation refuses overwrite of existing reviewed settings; separate kit extraction preserves external configuration.
- Packaged current-trust checks 28, update checks 20, SSH protocol checks 4 all pass in a dedicated root-owned temporary lab.
- Separate external registry/trust/history (6 files) preserved across old/new kit extraction; packaged gate rejects unprovisioned state and accepts retained current state without mutation.
- Five source files bound to the successful actual-S3 recovery evidence exactly match the final kit manifest. No repeat S3 transfer was needed for this packaging check.

External registry and trust records remain administrator-owned state outside the plugin and kit. Installing a ZIP does not provision, renew, revoke or replace `/etc/owr-trust/current-recovery.json`. Missing/expired authority remains a recovery blocker. This trial does not validate automatic state migration or production service rollout.

The artifact manifest and hashes remain frozen. This acceptance note and its result JSON were added after testing and are not retroactively claimed to be inside those ZIPs. English is primary; `RAADME-jp.md` is included in the development kit.

See [machine-readable evidence](../../evidence-public/trust-final-zip.json), [current-trust deployment](../guides/current-recovery-trust.md), [SSH operations](../guides/trust-registry-ssh.md) and [real S3 recovery scope](../guides/trust-real-s3-recovery.md). Prior deliberately injected failures and the corrected test Python-path mistake remain in their own evidence. The historical unexplained browser-startup issue is separate from product defects; this run's evidence determines this ZIP result.
