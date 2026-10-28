# Site materials reconstruction (development)

> **研究・旧構成の資料 / Research and legacy reference.** 現行製品の導入手順ではありません。See [current distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md) and [導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md).

> Historical v1 implementation record. Native block-editor saving and source publication semantics now supersede the redirect/draft-only restrictions below. See [current native editor scope](native-wordpress-editor.md). Recovery targets remain private drafts.

Resilience is independent of Ozeki Database Backup for S3. Its source of truth is submitted content stored in S3 before WordPress projection. A database dump is not a reconstruction input. Git is an analogy, not a protocol or dependency.

## Active implementation

- `tools/site-materials.py`: bounded site-wide material contract; stable IDs; page/post distinction; page hierarchy; ordered paragraphs, headings, internal links and images. A full generation lists all current assets. Omitting an asset means deletion, provided no dangling reference remains.
- Each original is independently gzip-compressed with deterministic headers and content-addressed storage. Unchanged assets reuse fixed versions within the same daily retention window. A new window gets separately retained copies, avoiding indefinite dependence on expired objects. There is no delta chain. A generation is self-contained; its parent is provenance, not a restore dependency.
- `tools/site-materials-command.py`: explicit save / receive commands using the existing experimental S3 transport. This is not yet a general AWS deployment installer.
- `tools/site-wordpress-apply.php`: private WordPress projection/reconstruction. Stable IDs map to fresh WordPress IDs. DB updates use InnoDB transactions; partial image files may remain after failure but prior DB content remains. Same-generation replay is idempotent. Incremental application requires explicit dedicated-environment opt-in and exact parent receipt. Fresh targets can reconstruct any selected generation.
- Expected logical state is generated from the submitted material, before reconstruction. Actual titles, slugs, kinds, parents, rendered node positions and image bytes are checked. All resulting posts remain drafts; no automatic publication.

## Concurrency and recovery boundaries

There is one designated writer process host per site. A filesystem lock serializes operations and a durable request digest prevents reuse of an operation ID with changed content. Stale parents fail before new writes. Independent writers on different hosts are **not** supported by this new path. Preserve the writer journal and fixed generation receipts; unknown PUT outcomes block retries through the existing transport ledger. No guessed resend or ledger deletion is permitted.

The default new contract is `integrity`: fixed Version ID, digest, decompression bounds, references, retention and request-derived expected state are mandatory. This is distinct from a human signature. `independent-signature` fails closed unless an independent verifier is supplied. The old signed RBR executor is unchanged; its approval does not automatically authorize a new-schema generation.

A reused object's retention must reach the generation horizon. If it does not, create a separately retained copy; do not extend or overwrite the old object. Expired generations fail closed. Site and object bounds remain explicit (1,000 assets, 4 MiB binary image, 64 MiB decompressed closure).

## Current limits

The generalized contract has an opt-in dedicated editor in addition to its CLI. The existing three-page browser editor is not silently converted to this schema. Ordinary Gutenberg, classic editor, XML-RPC, direct DB edits and regular media upload are not automatically protected by it. HTML, shortcodes, dynamic blocks, forms, plugins, users and credentials are not imported. Markdown supports plain lines and level 2–6 headings only; other markup is explicitly rejected. PNG/JPEG are supported; PDF is not.

The dedicated live experiment uses existing EC2 roles only to authorize experimental S3 requests. That test transport is not a requirement to run a permanent second EC2. Reconstruction runtime images are pinned local Docker images in this experiment; it is not a new proof of cold bootstrap from S3-only runtime archives.

## Legacy separation and Backup for S3

Legacy DB/files restoration, daily-backup watchdog, preflight deployment and three-page RBR experiments retain their evidence and existing entry points until dependencies are audited. They are not requirements of the new site-materials contract. See `docs/legacy-transfer-inventory.md`. No feature is considered transferred merely because a candidate is listed, and no previous test proves the new contract.

## Dedicated editor integration

`SiteMaterialsEditor::boot($bridgeDirectory)` is explicit enrollment for a fresh, guarded disposable WordPress. The lab runner configures it; existing installations are not automatically enrolled. `SiteMaterialsProjection.php` is shared by CLI and web application, with the same request-derived comparison.

1. Open Posts / Pages edit or Media / Add New. In the enrolled lab this redirects to **S3先行編集**. Select a material, add a post/page, or register a PNG/JPEG. Body input supports paragraphs, headings and explicit asset links/images.
2. Save enqueues an immutable request. A single designated `site-editor-worker.py` stores and retrieves fixed S3 versions before reporting `stored`. The browser then applies the exact received generation. Selecting a file does not create a WordPress attachment.
3. Failure preserves previous WordPress content. Reload retains the pending request. **同じ要求を再開** resumes the same operation; changed content and stale parents are rejected. Unknown storage outcomes require reconciliation, not automatic resend.
4. After S3 commit, an interrupted worker can reconcile its journal and return the same receipt. Projection failure rolls back DB changes; orphan image files may remain. The UI stops automatic apply retries and offers explicit resume.

Only administrators can use these endpoints; normal post/page/media REST writes, normal insert/delete and upload paths are blocked on the explicitly enrolled lab. Direct SQL and arbitrary third-party code are outside this control. WordPress navigation/internal records are outside the managed material count and are not removed.

All source and reconstruction pages remain drafts. Public production update semantics, normal block/classic editors, arbitrary Markdown, metadata/custom fields, bulk import and production enrollment are not implemented. This developer harness is not a production installer. The existing independently signed three-page path and its conditions remain unchanged; the new material path uses its separately documented integrity policy.

### Editor validation, 2026-10-23

The dedicated real-browser suite passed 23 checks with both the persistent S3 double and experimental S3. Seven committed generations (initial enrollment plus six edits) ended with two posts, three pages and two images. All 17 PUT operations were acknowledged; none had unknown outcomes. Failures were injected before save and the worker actually exited after commit, before reporting/applying. These checks do not claim coverage of every network failure.

After the source containers were removed, a new reader fetched the final fixed S3 version and reconstructed a fresh private WordPress. All seven assets matched request-derived expectations, including media bytes and references; side-effect attempts were zero. The existing rollback check also passed. Runtime images were pinned local images, not recovered from S3. Core/worker unit tests: 19 passed. [Machine-readable evidence](../evidence-public/site-materials-editor-validation.json).

Product fixes include excluding WordPress navigation from managed material counts, removing the enrolled dashboard's quick-draft path, immediate pending UI state, and literal-input slashing. A WebDriver invocation mismatch was a test-infrastructure correction. An earlier read-only WSL timeout remains an environment issue; no WSL restart or uncertain PUT replay was used. Historical failed trials are preserved.

Invalid queued material currently requires operator correction; there is no pending-cancellation UI. Existing public-state updates remain unverified: the trial deliberately uses drafts and performs no production changes or automatic publication.
