# RBR 03 — Proposed policy and data contracts

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

## S3-first barrier

In standard Normal Mode, final save/publish/upload completion requires S3 original persistence first. A browser or temporary upload buffer may exist beforehand; it is not the accepted WP asset. The final transfer route is undecided. Draft/autosave may be local and explicitly unprotected; they must not be labelled recoverable. CLI/REST/import bypasses are initially unsupported and must not be advertised as protected saves until integrated.

Proposed operation states: intent -> originals_stored -> generation_committed -> wp_applied; failures/unknown outcomes remain visible. S3 success with WP failure means materialization pending, not data loss or a new version on blind retry. On uncertain S3 outcome, reconcile the operation ID and exact stored receipt before resend. Never claim one atomic transaction across S3 and WP. S3 outage keeps the previous complete generation and blocks protected completion; user policy for local drafts is explicit.

The generation manifest is written only after all required referenced versions exist. Unchanged originals can be referenced again without copying. Concurrent edits use expected parent generation; a conflict is resolved explicitly. Deleted content is absent/tombstoned in the new generation, not erased from protected older ones. Partial material may be retained but is not a complete generation.

## Proposed logical records (not implemented schemas)

- Original: stable asset ID, site ID, kind, size, hash, fixed S3 locator, registration/operation ID, provenance and inspection status.
- Content: title/body/slug/type and permitted semantic metadata; independent of old WP numeric IDs. Original body and supported representation remain distinguishable.
- Relations: source and target asset IDs, type, location/fragment, ordering, unresolved reason; covers parents, inline/featured media, navigation and required contact information.
- Profile: schema/rule versions, language/timezone, allowlisted theme/plugin identity, mapping rules, required business assets/functions and supported fallback decisions. No arbitrary code, shell, secrets or bulk options import. A clean installation's policy catalog constrains Profile choices.
- Generation: Profile version plus exact asset/relations versions, parent generation, required-item coverage, storage completion. Storage completion, WP application, content verification and publication approval are distinct.
- Incident record: affected site/generations/assets, hold boundary, reason and authorized disposition, stored independently of the old WP. A selectable old manifest must not hide newer holds. Exact standard mechanism for discovery/authentication is a design gate, not solved by this assessment.

Originals accepted by the agreed registration workflow are normal by premise. This does not authorize an incident-mode acquisition to join that series. Freeze new normal registrations on declared suspicion; retain later material in quarantine. Identification/notification of suspicion may be manual initially; automatic intrusion detection is not a prerequisite.

## Compatibility and retention

Old [current trust gate](../../tools/current-recovery-trust.py) still protects old Restore. Its mandatory root checkpoint/expiry is NOT silently bypassed or reinterpreted. A separately versioned RBR contract may accept normal registrations without a daily external signing ceremony, subject to design approval. Nothing changes old approvals now.

Normal-site credentials must not delete protected versions, bypass retention, or rewrite protection/hold authority. Recovery uses a distinct read scope available without the source. Retention must cover referenced originals, Profile and manifests together; a long-lived reused original cannot expire underneath a newer complete generation. Default duration, extension owner, lifecycle and hold retention need explicit policy before implementation. No existing S3 configuration is changed.

Existing sites require explicit baseline enrollment from their current content. Such material is marked baseline/imported, never backdated as an upload-time original. Legacy Backup for S3 material is an optional import route with separate provenance; the products remain independent.

Sources: [VersionedAssetStore](../../src/VersionedAssetStore.php), [PHP collector](../../tools/portable-content-export.php), [portable manifest implementation](../../tools/portable-content.py), RAM/Recovery Set schemas and current-trust gate. Unknown: final retention authority, incident-record access method and standard Profile approval UX.
