# Real S3 generation coordinator connection (prototype)

This development-kit CLI connects the existing generation coordinator to the existing experimental S3 bucket. It does not intercept WordPress editor saves or publish a site.

## Flow

Explicit generated asset job -> conditional immutable originals/operation intent -> one conditional generation slot -> unchanged generation reference -> `rbr-generation-kit.py` -> approval-pending kit -> existing independent signature/current-trust gate -> private reconstruction.

The live generation manifest is produced by `RbrGenerationCoordinator`, not a fixture-generation bridge. The test harness supplies only ordinary input assets/jobs and fault timing. The existing reconstruction rules, environment, comparator and expected logical state remain pinned. Changing these is not part of this connection.

## Entry and prerequisites

`tools/rbr-coordinate-s3-lab.php --job=JOB --case=CASE --work=PRIVATE_DIRECTORY --execute-generated-lab` uses `rbr-coordinator-transport.py` and the existing SSH role signer. Requires PHP/Composer dependencies, Python, SSH aliases community/dm, and the explicitly authorized experiment prefix. Only generated `corporate-test` jobs are accepted. Use separate private work directories for concurrent callers and preserve every journal after failures. Do not run multiple callers against the same journal.

The physical experiment prefix is separate from the logical site ID. The legacy `sites/{site}/` mode remains available. The added reader policy permits latest reads and prefix-constrained listing only in the new experiment scope. Exact-version reads remain mandatory for actual content. A HEAD403 alone is never treated as absence: a successful bounded-prefix listing must establish absence; denied discovery remains an error. This adapter is experiment-specific, not a generic production credential/configuration interface.

## Retention

Live preflight showed Object Lock enabled with **no default retention rule**; the same configuration was observed afterward. Earlier notes incorrectly called the prior per-object 35-day retention a bucket default. No bucket configuration was changed. An opt-in object-store mode sets GOVERNANCE retention to 36 days on each **new** PUT and verifies actual S3 retention afterward. The generation still promises `deadline + 35 days`. Legacy mode still requires a 36-day default. Short-held existing assets require a new retained copy; old versions are not extended, deleted or bypassed. No PutObjectRetention operation is used.

## Verification and limits

Evidence is recorded separately in `evidence-public/rbr-live-coordinator.json` when the live run is complete. Local regressions cover explicit retention, unchanged legacy behavior, denied discovery, fixed-version reads and scope rejection. Live cases cover competing processes, pre-PUT failure/restart, lost commit response/reconciliation, insufficient retention and retained copying. The winning generation then passes through independent approval into two fresh private WordPress instances and comparison with Q.

Faults are injected at the transport boundary around real S3 requests; they are not claims that an actual AWS outage occurred. Retained versions and failed journals remain for review. Independent test approval uses a root-only test key and a private mount namespace, not a physically separate signing host. Existing dedicated Docker image storage is reused; this is not another cold-cache experiment. No production change, automatic approval renewal, automatic publication, new EC2, ZIP or release is included.

## Completed live run

PASS: one real commit winner, failed save resumed, lost response reconciled with zero PUTs on repeated operation, short retention rejected, new retained copy preserved the old retention. The exact winning generation entered the signed kit. Two private WordPress reconstructions matched Q. See the evidence JSON for hashes, counts and bounds.
