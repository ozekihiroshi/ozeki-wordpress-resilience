# Recurring trust operations: final ZIP acceptance

Experimental prototype `0.1.0-dev.1`, October 22, 2026. No formal release or final 72-hour observation verdict.

## Frozen artifacts

- `ozeki-wordpress-resilience-0.1.0-dev.1.zip`: SHA-256 `0537301b4f85b52cbd363c2b5909806b367c5a3d9bc40933325b31f88af51cfb` (35162 bytes).
- `owr-development-kit-0.1.0-dev.1.zip`: SHA-256 `7ec65fd810cb57ac6a7b75c4a901a73cdf00d33e0dcb5f83001b1d006e7505fe` (14661140 bytes).

The plugin ZIP is byte-identical to the previous PR #7 candidate. The actual WordPress Plugin_Upgrader trial therefore checks fresh installation and same-version overwrite, not a new database migration. The new development kit includes recurring-update procedures, two-VM SSH evidence and operational tests. Existing ZIPs are not overwritten.

## Results

- Packaged configuration/plan checks: five passed, including read-only planning, overwrite refusal and configuration retention.
- Actual WordPress fresh installation/activation and previous-candidate overwrite passed. Chromium checked status/history, administrator access, editor denial and read-only behavior; settings, cron records, wp-config, pending requests and external records survived deactivate/reactivate.
- Thirty-two completed generated roundtrip files retained; original source unchanged.
- Separate root-owned external-state check: four checks passed, preserving seven files containing registry, signed approval, signature, public key, pin and SSH failure/recovery history across old/new kit extraction. Packaged current and signature gates accept the retained state, while unprovisioned state fails closed. Original VM trial records remain unchanged.
- Six operational tests executed from the extracted final kit passed without skips: no automatic signature renewal, partial-host handling, failed update/expiry/recovery and unknown-outcome reconciliation.
- Five implementation source hashes from the successful actual-SSH two-VM evidence match the kit exactly. That trial is not rerun for packaging.

The approval document and its expiry remain byte-identical. ZIP installation does not provision or renew `/etc/owr-trust/current-recovery.json`. Manual independent review and per-host readback remain necessary. No global immediate revocation, root-resistant rollback or automatic full deployment is claimed.

Environment, test infrastructure and product boundaries are separate in the [result JSON](../../evidence-public/recurring-trust-final-zip.json). The first candidate failed because its static report aged past five minutes during setup; the UI correctly showed current validity unconfirmed. The test harness now sets synthetic observation timestamps after startup and before the immutable preservation baseline. Initial artifacts/diagnostics remain; no product expiry rule or approval changed. This corrected candidate passed. Historical unexplained browser startup remains a separate test-infrastructure issue. No new environment or product fault was established. S3, production FTP/MySQL and the original observation were not modified.

This acceptance report and its JSON were added after the ZIP freeze and are not retroactively included in those bytes. The [recurring runbook](../guides/trust-recurring-operations.md) and [actual SSH evidence](../guides/trust-recurring-ssh.md) describe the included work. Physical USB, substitute-operator access and production deployment remain separate acceptance tasks.
