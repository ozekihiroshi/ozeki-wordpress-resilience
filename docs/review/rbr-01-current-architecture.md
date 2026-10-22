# RBR 01 — Current architecture and target

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

## Adopted premise

The first original accepted into S3 by the normal ingestion workflow is treated as normal. This is the design's trust starting point, not a malware-detection task. Protect that exact version and reconstruct from it. Later authorized edits create new versions. Incident-suspect material is outside the normal series. No always-on second EC2 or external Recovery Controller is required; S3 is required external storage, not such a server.

## Current code observations

- [Plugin bootstrap](../../ozeki-wordpress-resilience.php) boots notification/status administration. [Packaging](../../tools/build-release.py) ships ten plugin files; portable tools are in the development kit, not the installed admin plugin.
- [Collector](../../tools/portable-content-export.php) reads already-persisted WordPress rows and original attachments after a trusted WP bootstrap. It is not upload interception or S3-first capture.
- [Extractor](../../tools/portable-content.py) creates local JSON, text, media, relationships, issues and hashes. Record and media identity currently uses source WP IDs; there is no permanent site-independent identity service.
- [Preview](../../tools/portable-preview.py) renders local HTML, normalizes images through Docker/PHP GD and preserves supported fragment positions. It does not insert pages into a new WP database.
- [Daily coordinator](../../tools/first-site-daily.py) is a generated-site Python/SQLite workflow, with hard-coded trial constraints. [S3 adapter](../../tools/queue-s3-adapter.py) obtains authorization over SSH from named hosts. That adapter is not the standard plugin's storage connector.

## Target topology

Normal: editor/upload -> original and relations saved to S3 -> immutable generation manifest -> WP materialization. New WP at recovery time: install Resilience -> supply recovery access and site identity -> choose complete generation -> inspect/plan -> reconstruct -> verify -> operator publication decision.

S3 stores originals, versioned content/relations, Profile, complete-generation manifests and separate incident/use-hold records. A manifest references exact versions; it must not depend on a mutable latest pointer alone. The plugin's built-in rules interpret data, never executable commands from Profile. Keep originals and generated thumbnails separate.

The operator retains a recovery access pack outside the lost site: bucket/region/site identifier, recovery authentication instructions, Profile/rule compatibility and any verification baseline. Do not put secrets inside Profile. No old-site connection is required during reconstruction.

Evidence boundary: [portable ZIP acceptance](../../evidence-public/portable-final-zip.json) establishes generated extraction and static preview only. It does not establish S3-first ingestion, a new-WP importer or a standard hosted-plugin workflow. Historical static-preview specification remains historical, not the new target's completion claim.

Unknown: actual hosting permissions and execution limits, ordinary editor save-hook coverage, browser-direct versus plugin-mediated upload, and generic WordPress importer behavior. These require later decisions, not infrastructure work now.
