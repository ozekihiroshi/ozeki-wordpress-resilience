# RBR 06 — Cost and operator impact

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

No current AWS prices are quoted or newly researched. This is a structural estimate, not a billing forecast.

Standard steady state uses existing WP hosting plus S3. Remove the requirement for a second always-on EC2, external controller, SSH orchestration, systemd services and independent watchdog operations. Recovery destination hosting is created/selected when needed, and may remain the replacement production hosting; it is not a standing spare.

Cost model: retained original bytes + changed content/relations/Profile versions + generation metadata, multiplied by selected storage pricing, plus PUT/GET/LIST, optional key-management charges and recovery transfer. Original reuse can avoid repeat copies; preservation duration and unreferenced/held versions determine growth. No automatic deletion policy is assumed. Original media may live longer than a daily snapshot, so storage cost can rise even while compute cost falls.

Human tasks: initial bucket/access/policy setup and required-information selection; routine exception handling rather than daily external signature ceremonies; incident hold and generation choice; fresh WP/admin credentials preparation; final content/publication review. Recovery access must be available outside the source WP. No recurring charge for an idle recovery server does not mean zero storage, installation or operator cost.

Technical burdens move into the plugin: pre-save latency, S3 outage handling, durable progress, large uploads, image processing, concurrency and host-specific permissions. Existing [image processing](../../tools/portable-preview.py) relies on a pinned Docker runtime; a plugin-native replacement must declare supported formats and limits. Current [storage helper](../../src/VersionedAssetStore.php) does not supply hosted credentials setup.

Before pricing, collect site count, original image bytes/growth, body-change frequency, retention policy, recovery frequency/transfer destination and target-host limits. Later measure operator steps and time separately from unattended runtime. No claim of lower total cost for every site; reduced always-on infrastructure is the architectural benefit.

Unknown: measured latency, supported hosting tier, actual monthly request/storage volumes and retention-extension approach. No new AWS/production inspection or spending was performed.
