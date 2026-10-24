# Combined site recovery acceptance — 2026-10-24

## Result

PASS: Posts, Pages, images, comments, Contact Form 7, Flamingo, WP-Members and TablePress coexisted in one source WordPress. One complete Checkpoint through 21 plus subsequent S3 formal history through 29 restored their supported state together in the existing dm isolated WordPress. No source DB or local pending queue was used by restoration. Expected-result data was used only for assertions.

Existing TablePress integration directories/databases and its lab S3 prefix were reused. Previously tested plugin binaries and table/image/form/member fixture patterns were reused. New combined trial records, rather than existing articles or members, were changed: table 6, form 18, receipt 19, post 21, page 22, comment 2 and subscriber 2 in the **isolated source namespace**. These numeric IDs are not live-site IDs.

## Sequence

1. Activate existing CF7, Flamingo, WP-Members and Markdown Documents copies alongside TablePress in the isolated namespace, with protection temporarily disabled for trusted initial seeding.
2. Seed an article containing an image, CF7 reference and TablePress reference, a related page/link, comment, inquiry and approved subscriber/restriction.
3. Create a trusted initial snapshot through existing history 14; enable protection.
4. Update article/page, comment, form, receipt fields, member profile and table; confirm shared history through 21.
5. Generate one independent complete Checkpoint through 21.
6. Update those assets again after the Checkpoint, replace the image and change the comment to unapproved; confirm through 28.
7. Correct an inherited test-bootstrap URL mismatch in only the new trial article; the additional protected save becomes history 29.
8. Restore Checkpoint 21 plus tail 22–29 on dm, then boot a new request and verify.

Checkpoint manifest key: `site-snapshots/88b779a450196340a5afda504eebcadb7f1e3fcabc6fc3826c20bff6d3a10137/manifest.json`
VersionId: `vFwIAiDQLXk9SeQ.dTD5MQaMsURSfGV_`
SHA-256: `ccddff2471020e9bd19882e869371db3c568cb851b8c2dc3e840967c0f838bd7`

## Confirmed

- Published Posts/Pages: exact body after source-to-destination URL relocation, status and cross-page links.
- Replacement image: restored binary SHA-256 equals source fixture; referenced attachment restored from S3.
- Comment: updated body, unapproved state and parent article identity.
- CF7 definition and Flamingo receipt: stored metadata matches; form/article shortcode relationship renders.
- WP-Members: recorded subscriber password authenticates, post-Checkpoint profile matches, guest cannot see protected body and member can; destination administrator unchanged.
- TablePress: ID, cells, options and visibility match; table and CF7 render together in the same article.
- No pending formal history; mail attempts zero in trial phases and recovery/verification. No submission or mail replay was performed.

Operations used ordinary WordPress/plugin PHP APIs, including completed-save hooks and the same request-end adapter flush methods. This is combined persistence/recovery acceptance, not a new browser acceptance for every plugin or an actual mail submission. The preceding separate TablePress browser acceptance remains valid. Markdown is installed but new Markdown editing was not an additional claim in this combined run.

## Product correction

CF7 creates `uploads/wpcf7_uploads/.htaccess` containing only its known Apache deny-all rules. The snapshot rejected it under the general executable/control-file prohibition, preventing a normal combined baseline. The failure occurred before a completed snapshot manifest was produced.

`SiteSnapshot::validateUpload` now permits only that exact path and exact deny-all content (LF or CRLF). Arbitrary `.htaccess`, appended allow directives, PHP and PHAR remain rejected. The original protection file is retained; no guard was deleted or disabled. The accepted guard is carried in the snapshot and recovery resources. A regression test covers positive and negative cases, and is added to CI configuration.

The fix was applied only to the isolated source/destination trial plugin copies. It is not included in the earlier frozen 0.3.1 ZIP. No production deployment, new ZIP, PR or release was performed in this task.

## Environment and test infrastructure

The reused bootstrap had a fictitious content URL inconsistent with its source home URL. Correcting that test configuration and the newly created fixture's URL was a harness correction, not a product URL-recovery fix. Existing dm live probe still emits duplicate DISABLE_WP_CRON configuration warning. No new OOM failure was observed.

Existing dm live content/configuration/Cron/history hashes still match the pre-trial baseline. No existing site article/member was edited. Standard AWS SDK EC2 role credentials, existing buckets/prefixes/containers, no IAM changes or credential helper. Mail transport is blocked and WP-Cron disabled in trial bootstraps. Formal release, scheduled execution, public cutover and any S3 cleanup/deletion remain deferred.

## Regression and limits

PHP lint and upload-guard, Checkpoint, comments, forms, membership, TablePress, queue-capture and cleanup contracts passed; those contracts use declared in-memory storage doubles. The combined integration uses actual S3. Cloud CI has not been rerun for the new working changes.

This does not broaden each adapter's supported scope: premium modules, arbitrary third-party metadata, concurrent same-asset writes, unconfirmed final operations, unsupported media, scheduling and mail transport remain outside this acceptance. It verifies the named adapters together, not universal WordPress equivalence.