# RBR 07 — Assessment and decisions

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

**Conditional migration is reasonable. It is not a small UI addition to an already complete reconstruction system.** Existing material/relationship/loss primitives are useful, but S3-first acceptance, Profile/generation management and fresh-WP reconstruction are the missing backbone.

1. Can migrate? Yes as a proposed staged architecture; executable end-to-end WordPress reconstruction is still unverified. [Current architecture](rbr-01-current-architecture.md).
2. Must retain? Version/hash/size identity, explicit omissions, source-independent material, exact-generation selection, progress/failure records and all historical evidence. [Matrix](rbr-02-component-reuse-matrix.md).
3. Remove from standard prerequisites? External always-on EC2, SSH/systemd orchestration, root-owned recovery authority files and SQL/file full restore. Preserve as optional/research, not delete.
4. Plugin-first feasible? Plausible, with new PHP ingestion/importer/job adapters. Current Python/Docker tools are not already a native plugin. Actual hosting support is unresolved.
5. Manual fresh WP plus no spare server? Structurally yes; S3 and separately available recovery access provide persistence. Cannot rely on authentication held only in the lost site.
6. Backup for S3? Remains a standalone backup/restore product. No required installation, migration, shared-code changes or automatic absorption in this plan. Legacy assets may later have an explicit importer with distinct provenance.
7. Simplification? Fewer permanent services, no routine controller setup, event-driven protected saves; unavoidable S3/retention/recovery-access and exception/publication decisions remain.
8. Limits? Adopt initial S3-original normality as agreed; do not build an impossible universal innocence detector. Still preserve correct versions, relationships, operation ordering and hold decisions. Unsupported edit routes and dynamic features must remain visible. Initial enrollment of existing content is explicit baseline adoption, not historical upload proof.
9. Minimum new work? N1-N7 as scoped in [plan](rbr-05-minimum-poc-plan.md); first demonstrate a small S3-first to fresh-WP vertical slice, not general theme/plugin reconstruction.
10. Preserve results? Keep old code/ZIPs/evidence/approvals/S3 assets unchanged and distinguish the [static-preview acceptance](../../docs/releases/portable-final-zip.md) from later RBR acceptance. Shortened observation is closed, never relabelled.

## Decisions needed before implementation

Proposed first scope: one corporate site, standard pages/posts, basic body elements, original PNG/JPEG, one clean theme; forms replaced only by explicitly approved contact information. PDF/media beyond this subset are not silently included.

Confirm protected saves versus local draft behavior, normal update routes, baseline enrollment consent, retention of referenced originals, independent hold authority/recovery access and which Profile changes require operator review. These are finite design decisions; do not reopen the adopted normal-original premise.

Next deliverable, if approved: concrete Profile/generation and operation-state contracts plus the smallest WordPress adapter plan. Do not start code, test campaigns or provisioning merely because this assessment is written.

All judgments are based on the baseline source and documents linked in RBR01-06, not new runtime proof. No incompatible old-policy migration, deletion, new spending or change to Backup for S3 is authorized by this report.
