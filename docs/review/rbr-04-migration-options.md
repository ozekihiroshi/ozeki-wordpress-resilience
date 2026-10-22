# RBR 04 — Migration options and dependencies

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

| Option | Assessment |
|---|---|
| Wrap current Python/SSH/Docker pipeline in WP buttons | Smaller apparent UI change, but preserves external host, OS and root dependencies. Reject as standard design. |
| Build a plugin-native RBR engine using existing contracts and independent materials | Recommended target. Requires new ingestion and importer, but fits no-second-EC2 and fresh-WP entry. |
| Reuse old SQL/file backups as primary reconstruction input | Retain optional future importer; not equivalent to upload-time S3 originals and not the default dependency. |

Separate an RBR domain layer from execution adapters. Operations: inspect, plan, prepare, reconstruct, verify, status. The WP admin client and future optional controller call the same rules. Old Restore entry remains intact; no replacement of backup-core, old schemas, evidence or stored objects.

PHP plugin-native execution is a plausible engineering direction, not demonstrated by the current static preview. Existing PHP collector, storage abstraction and admin code show useful building blocks. The actual importer, media pipeline and lifecycle integration remain new work. Shared hosting must not require Python, Docker, systemd, SSH or root. Bounded batches and persisted progress are required; exact scheduling/background implementation is undecided. A browser-driven/resumable initial path is acceptable; unattended execution guarantees require separate capability checks. VPS can use optional local scheduling; Docker remains a development/optional environment.

Trusted WordPress installation and Resilience installation are manual initially. Missing theme/plugin installation permission may be resolved by manual preparation; no secret requirement for an external controller. Unsupported hosts receive a concrete capability report, not a promise that every shared host works.

Profile is declarative; install only identifiers/versions resolved through an approved catalog, never arbitrary Profile URLs. Specific version availability and supported version-selection policy remain open. Recovery uses newly issued accounts/secrets. Links are resolved through asset->new-WP-ID mappings, not preservation of source IDs.

Evidence migration: retain existing release-candidates, tags, manifests, signatures, S3 versions and summaries in place. Label old tests by their actual contract. The closed shortened observation remains closed and is not evidence for RBR. Keep Python CLI as reference/diagnostic; avoid two independently evolving rule engines.

Sources: [plugin bootstrap](../../ozeki-wordpress-resilience.php), [packaging](../../tools/build-release.py), [lab transport](../../tools/queue-s3-adapter.py), [runtime contract](../../tools/same-host-runtime.py). Unknown: hosted PHP limits, dependency packaging, editor integration and credentials UX. These are design gates, not grounds to add an always-on EC2.
