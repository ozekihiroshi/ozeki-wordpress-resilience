# Signed S3 kit: frozen ZIP acceptance results

PASS, experimental 0.1.0-dev.1. No tag, formal release or publication.

- `ozeki-wordpress-resilience-0.1.0-dev.1.zip`: 35162 bytes; SHA-256 `0537301b4f85b52cbd363c2b5909806b367c5a3d9bc40933325b31f88af51cfb`.
- `owr-development-kit-0.1.0-dev.1.zip`: 14992048 bytes; SHA-256 `fe52833aa541fee5f8d136b308b4a51981316a334e2ec5485f4b4e6771fdcf01`.

Actual WordPress Plugin_Upgrader fresh install and same-version overwrite from portable-final-v2 passed. The plugin archive is byte-identical to that previous candidate. Browser checks and deactivate/reactivate confirmed settings, cron, wp-config, requests and external generated reports/history retention. This does not test a database schema migration.

The development kit contains 873 manifested files. Seven packaged regression invocations passed, with lock-file Composer dependencies installed from the existing cache without network. Eleven external configuration/trust/approval/retrieval/reconstruction records remained byte-identical, as did their original source records and the old extracted kit. Packaged unsigned CLI refusal passed. No approval was renewed, no S3 transfer or reconstruction was repeated, and no external service was activated. Dedicated containers were removed. The first browser attempt is retained as a test-infrastructure failure: a short readiness-probe timeout and self-hostname resolution warnings in the network-isolated namespace, without OOM. A workspace-only wrapper specified the loopback Selenium host and bounded probe retries; the final archive and plugin code were not modified. A subsequent upgrade-only browser attempt used a bounded element wait after the first upgrade attempt found no login input; the original absence cause remains undetermined. Fresh evidence is lifecycle-02 and upgrade evidence is lifecycle-03. No assertion was removed. This does not resolve every historical browser-startup issue.

See [machine-readable evidence](../../evidence-public/rbr-signed-kit-zip.json), [scope and procedure](rbr-signed-kit-zip.md), and the English/Japanese READMEs. This report was generated after ZIP freeze and does not change the tested archives. CLI/host setup and all documented prototype boundaries remain.
