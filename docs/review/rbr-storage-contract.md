# S3-first originals and site generations — minimum contract v0.1

> Follow-up: [v0.2 concrete coordination and editor decisions](rbr-coordination-contract.md) supersedes the open mechanisms below, selects protected-copy renewal without retention-write permission, and integrates the normal editor buttons.


Status: design only, 2026-10-22. Proposed implementation contract; no schemas, application code, AWS settings or tests changed. Builds on [Stage 0 policy](rbr-03-policy-consistency.md). [日本語](rbr-storage-contract-jp.md).

## 1. Boundary and default decisions

Originals accepted through the normal S3-first registration workflow are normal by premise. The system preserves their identity, relationships and recoverability. Standard topology: existing WordPress plus S3; a clean WordPress is prepared when recovery is needed. No always-on second EC2 or signing server is required.

Initial business scope: exactly three required page roles (company, services, contact), JPEG/PNG images, paragraphs, headings, lists, internal/external links, image placement and navigation order. Contact means displayed address, telephone and email links, not form execution. Custom PHP, forms, shortcodes, dynamic blocks, arbitrary HTML/scripts, PDF/SVG and plugin-specific state are outside this contract. Unsupported input is reported before protected acceptance; it is not silently removed. The user must change it or explicitly adopt a supported alternative.

Normal editing remains in WordPress; users need not author Markdown. Initial protected entry is an explicit Resilience save/publish workflow for the selected pages and images. Until ordinary editor save paths are integrated, they cannot be described as protected. Local drafts are allowed, visibly unprotected. No full-site protection claim is made for unintegrated REST, CLI or import paths.

## 2. Units and identity

| Record | Unit and mandatory meaning |
|---|---|
| Site | Random stable site_id, independent of domain or old WordPress IDs |
| Page original revision | One accepted revision of one page: asset_id, revision_id, title, desired slug, language, supported semantic body, operation_id, provenance |
| Image original revision | Exact uploaded JPEG/PNG bytes; stable asset_id, immutable revision_id, detected type, byte count, SHA-256. Replacements create a new revision; thumbnails are derived and regenerable |
| Relations revision | For this small site, one whole-site record: parent IDs, navigation order, inline link node/anchor IDs, image placement, alt text and captions. It references exact page/image revisions |
| Profile revision | Three role-to-asset assignments, required image list, locale, supported clean-theme/rule identifier and approved fallback choices; no credentials, executable code or wholesale options |
| Generation manifest | Complete snapshot of all three page revisions, required and included images, relations and Profile; parent generation and operation IDs, counts, hashes and fixed-version object references |
| Application receipt | Whether this committed generation was applied to the source WordPress; separate from its original manifest |

Use random asset/revision/operation/generation identifiers, not timestamps or source WP numeric IDs as identity. Each fixed object reference contains bucket, key, Version ID, bytes and hash. Timestamps are UTC metadata, not ordering authority. Domain/slug changes do not change asset identity. Media used in two locations has one original revision and two relation entries. Editing alt text or navigation changes relations, not image bytes.

Persist the submitted supported body before it becomes accepted WordPress content. If an editor representation is also kept, label it source evidence; the reconstruction input is the versioned supported semantic representation. A conversion loss must block required-content completion rather than be hidden. Internal links use asset and anchor identities; rebuild URLs for the destination domain. An unresolved internal target blocks completion unless the user explicitly removes or replaces it.

Proposed logical namespaces: sites/{site_id}/originals/{asset_id}/{revision_id}, relations/, profiles/, generations/, operations/, application-receipts/, quarantine/. These are not deployed paths. Records are immutable. Search indexes and a latest pointer are conveniences, not sufficient recovery authority.

## 3. Site generation and acceptance barrier

A generation is a complete logical snapshot, not a full copy of every image. Reuse unchanged exact revisions; save new revisions for changed material. All three required pages must exist even when only one was edited. Removal of a required role is blocked until a replacement is assigned. Removing an optional image excludes it from the new snapshot; earlier snapshots retain it.

Sequence:

1. Prepare an operation with stable operation_id, immutable payload digest and expected parent generation. Capture the chosen page revisions and all dependencies; later edits become a new operation.
2. Validate supported content and required roles. Save originals, relations and Profile to S3, collect exact-version receipts and verify references.
3. Serialize competing writers for this site and compare expected parent. A stale parent is a conflict, never an automatic last-writer-wins overwrite. Rebase explicitly and use a new operation.
4. Create the immutable committed manifest only when every referenced object and its protection condition are confirmed. This is the S3 recovery boundary.
5. Apply that exact generation to WordPress; record an application receipt. Final user success requires both S3 commit and WP application. Public visibility remains a separate choice.

The site-wide commit mechanism must work for concurrent PHP requests without an external host, include safe takeover after a crashed owner and reject stale owners. Its concrete S3/database concurrency mechanism remains an implementation-design gate; a latest-pointer write alone is not adequate. Partial generations never become the default recovery choice.

A committed generation can be recovered even when source WordPress application failed; show it as “saved to S3 / WordPress application pending”, not as previously published content. A recovery selector distinguishes last committed from last confirmed applied/published, and checks holds separately. Absence of an application receipt is unknown, not proof of failure.

## 4. Failure and restart contract

States: prepared -> storing -> originals_confirmed -> committed -> applied. Also conflict, retryable_failure and outcome_unknown, with the last confirmed stage and error preserved. Status is a projection of append-only receipts, not a rewritten original.

| Failure | Required behaviour |
|---|---|
| S3 unavailable before commit | Keep previous complete generation active; do not apply protected final changes to WP; preserve local draft where possible |
| Some originals saved | Reuse confirmed exact versions; upload only missing material after reconciliation; do not create a partial generation |
| Write response lost | Use operation/revision identity to discover and validate any written object before resend. Same identity with differing content is an error |
| Commit outcome unknown | Stop WP application and new generation progression until the manifest and parent/commit result are reconciled |
| S3 committed, WP apply failed | Resume from that manifest, not a newly extracted WP snapshot; do not repeat original registration |
| WP succeeded, receipt failed | Inspect generation-to-WP mapping and content before replay; repair the receipt without duplicate pages/media |
| Browser/PHP stopped | Release only expired execution ownership safely; reopen pending operation in UI and resume. Do not assume in-memory buffers survived |
| Source lost before commit | Only previous committed generation is guaranteed; partial originals may be recoverable material but never labelled a complete site |

Durable S3 receipts permit reconciliation after source loss for committed material. Pending bytes not yet in S3 may still require user re-upload; no false guarantee of draft durability. Repeated clicks attach to the existing operation. A deliberate edit gets a new operation. Automatic attempts are bounded (initial proposal: three within one worker invocation, with backoff); authentication, content and conflict errors wait for action. UI reports actionable state and supports resume; no always-running worker is required. Abandoning an incomplete operation never deletes its S3 objects automatically.

## 5. Retention and deletion

Separate minimum protection, eligibility for cleanup and actual deletion. “35 days” is the proposed minimum protection window for a newly committed generation, not an expiry that makes current originals disappear. The generation contract records protect_until; each exact referenced object must be protected at least until that timestamp before commit. Existing source policies are not changed by this specification.

Reused old objects must satisfy the new deadline. Standard design grants only narrowly scoped retention extension to the normal writer, with no shortening, bypass or deletion capability. If the implementation cannot enforce that boundary, do not grant broad retention rights: create a newly protected copy of the same original or fail the commit visibly. A copy preserves original provenance/hash and records the new storage locator. Signature approval is never extended by this operation.

Initial cleanup default: OFF. No automatic age-based expiration of originals or manifests. Therefore a quiet site needs no daily work merely to keep its only reconstruction source. After minimum protection expires, normal credentials still cannot delete; however continued storage is not represented as perpetual time-lock protection against a storage administrator. Stronger long-term locked retention is an explicit configuration option, not a hidden guarantee.

A future/manual cleanup plan may propose a generation only if it is superseded, its minimum protection has elapsed, and it is neither latest committed nor latest confirmed applied, a pinned baseline, held/in-use or required by an unresolved operation. Missing/stale dependency or hold information prohibits cleanup. An object is deletable only after every retained generation and pending operation that references it has been accounted for, all protection periods have elapsed, and no hold applies. Do not infer this from upload age. Review a dry-run and revalidate immediately before any deletion with a separate cleanup authority. That execution feature is outside this first implementation scope.

Consequences: storage grows until reviewed; show bytes and generations, never silently turn on lifecycle deletion to reduce cost. Retention does not make a held generation eligible for reconstruction. Current independent hold information must still be checked; incident registration/access policy remains a separate gate before claiming incident-ready release.

## 6. Worked example

G1 contains company C1, services S1, contact T1 and image I1. Editing services produces G2 = C1/S2/T1/I1 plus new relations if needed. If I1's protected deadline is too early for G2, extend protection under the restricted contract or make a protected copy before committing G2. Neither route changes I1's logical content revision.

If S3 saves S2 but cannot commit G2, G1 remains the recovery choice. If G2 commits but WordPress stops, G2 is saved/application-pending and can be resumed. Removing I1 in G3 does not delete it while G1 or G2 is retained. A site without edits for six months retains its current generation under the default no-deletion policy.

## 7. Scope to implement next, not executed here

Implement one vertical path: three pages plus one JPEG/PNG -> S3-first committed generation -> source WP application, with resume/unknown/conflict behaviour and retention prerequisites. Reconstruction can then consume precisely this contract. Keep legacy Restore approval rules unchanged and preserve its evidence; no automatic conversion of legacy recovery sets or Backup for S3 data.

Before coding, select the concrete conditional commit and narrow retention-authorization mechanisms and confirm the supported WordPress save interception boundary. These are implementation choices to satisfy this contract, not reasons to add another EC2. No new signature ceremony or unattended publication is introduced. Tests and AWS validation are future work, not evidence claimed by this document.
