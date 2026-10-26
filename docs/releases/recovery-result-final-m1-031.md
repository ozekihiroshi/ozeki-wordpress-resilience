# Recovery-result final ZIP acceptance — 2026-10-25

Candidate: `ozeki-wordpress-resilience-0.3.1-recovery-result-final.zip`
SHA256: `c3eabeb71b4c2ec13f287bfa4eda4ed715c80295bd2b3f470ad6c31c5f7472cb`
Size: 7,378,188 bytes; 3,812 files. Vendor bytes unchanged from the previous native-details-final candidate. Product files match the current package sources; older ZIP evidence is preserved.

## Accepted

- Existing dm container/core/database reused with previously unused, separate `owrrrzip_20261025_fresh_` and `owrrrzip_20261025_upgrade_` tables and isolated content directories. No new infrastructure or authentication helper.
- Fresh activation and overwrite update from the prior validated native-details-final 0.3.1 ZIP passed. This is extraction/activation and file replacement, not a browser Plugin_Upgrader test.
- Configuration, asset identity, saved recovery results (including latest failure and previous success), frozen pending queues/errors, content, comments, CF7/Flamingo data, member credentials/settings and TablePress IDs/settings/data retained.
- AWS SDK standard EC2-role authentication read the existing formal history: 56 records, identical SHA256 `590424c54da516c7c93a9e4918c35fc8071c185044354f9a65d692f0d2466c53` before/after. No S3 writes or deletions.
- Admin rendering from both installed ZIPs includes the readable recovery-result area and detailed JSON. Focused ZIP contract checks passed for success, legacy data, failure, unfinished attempt, missing Checkpoint, empty result, zero tail and escaping. PHP syntax passed.
- All 3,812 installed files match the final ZIP on both installations.
- Existing live-site probe before/after identical; mail calls zero and scheduled execution disabled. No live content/member updates, restore rerun, periodic acceptance or formal release.

## Scope and issues

Result counts are post records across all types, not unique public articles; file counts measure writes and may be zero when reusing files. Failure/unfinished status does not imply zero changes or completed rollback. The local result is not the S3 recovery authority or a complete audit log. English/Japanese root and packaged READMEs explain these limits.

Environment: the live probe emits a pre-existing duplicate DISABLE_WP_CRON definition warning; actual disabled state and unchanged probe were verified. Trial preparation initially had a Python syntax error, corrected before execution (no remote effects). These are environment/harness issues, not product defects. No new product defect was found in this ZIP acceptance. Remote CI has not been run for these uncommitted changes.

The previous browser display acceptance is recorded separately in recovery-result-ui-20261024. This task verifies packaging/installation/preservation rather than repeating site reconstruction.

## Display acceptance before packaging

In the existing isolated dm browser admin screen, the previous real recovery result showed Checkpoint through 33, tail 34–56 (23 records), 22 post records and zero file writes (matching files reused). Detailed JSON expanded correctly. A valid administrator request without destination-replacement consent exercised the actual action's precondition failure before replacement; the browser showed failure and unconfirmed counts rather than the previous success counts. Temporary failure/error options were restored; before/after content/member/settings probes matched. This checks precondition-failure reporting, not failure injection halfway through reconstruction.

The candidate is available in [release-candidates](../../release-candidates/20261025-recovery-result/ozeki-wordpress-resilience-0.3.1-recovery-result-final.zip), with its [manifest](../../release-candidates/20261025-recovery-result/ozeki-wordpress-resilience-0.3.1-recovery-result-final.manifest.json).
