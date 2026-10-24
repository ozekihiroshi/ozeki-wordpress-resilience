# Ozeki WordPress Resilience — S3 originals and site recovery

## Choose the recovery operation

**Site-wide recovery is the primary workflow.** In Tools → Resilience, use **Site-wide recovery — primary workflow** to select a complete initial snapshot / Checkpoint and **Restore complete site**. It reconstructs the supported site state from that baseline and subsequent S3 formal history, including supported images and site relationships. Destination content is replaced; prepare the destination WordPress, plugins and S3 access beforehand. These are normal administrator tasks. On-demand recovery is the product workflow; continuous replication is not required.

**Individual recovery is supplementary.** Under **Confirmed formal history / Individual recovery**, select one version per asset and use **Restore selected assets (text and attributes)**. This updates matching asset identities or creates missing records, preserving unrelated destination content. It does not restore media files, themes, menus or complete site relationships. Use site-wide recovery for that purpose. The earlier asset-snapshot controls are grouped separately under a collapsed supplementary section; they are not complete site snapshots.

**The recovery boundary is confirmed S3 formal history.** A trusted snapshot provides the baseline. Later operations are included only after their formal history is persisted in S3. A prepared original or WordPress application alone is insufficient. If the source is lost while history is pending, omit that operation: an unconfirmed new article is absent, and an unconfirmed update leaves the previous confirmed version. Recovering the final unconfirmed operation is not a completion requirement. While the source remains available, **Resume history** can verify and confirm it. The pending notice distinguishes WordPress application from recovery confirmation.

Recorded publication status, including `publish`, is preserved. Internet exposure and DNS are administrator decisions. Periodic execution and formal release remain deferred; this clarification changes no save/recovery conditions.

## Validated native editor and image workflow (2026-10-24)

Standard Pages and Posts can be created, published, updated and moved to/from Trash through the normal WordPress editor. Supported local image uploads are stored in S3 before registration; referenced images and generated sizes are bound to the successful article version. Each native body is a complete HTML file, not a database dump or content delta. Recovery uses the complete site baseline plus subsequent S3 formal history and preserves publication status.

Real browser tests used trial articles, image addition and replacement, and recovery on a separate existing WordPress. Chrome's visual inserter and Replace/media-library controls worked without code-editor input (histories 25 and 26). The in-app browser left the blob editor iframe blank while the same site, user and article worked in Chrome without server or plugin changes. This is a browser-environment limitation; its internal cause remains unresolved. Use Chrome for this workflow. It is not evidence of a Resilience save/recovery defect.

This does not cover featured-image changes, unused media entries, external/CDN resources, arbitrary metadata/taxonomy changes, third-party binary overwrite tools, permanent deletion or scheduled publication guarantees. Images are limited to JPEG/PNG/GIF/WebP/AVIF, 32 MiB per file; source text is limited to 5 MiB. Recovery is manually invoked, not automatic destination synchronization. Wall-clock periodic execution remains deferred. Cleanup code is optional and disabled by default; real-S3 deletion acceptance is not claimed.

The final package validation report is delivered alongside the ZIP. Tests and transport mocks are not shipped. AWS SDK standard authentication remains the product path. Installing or replacing plugin files does not intentionally migrate or clear settings/history; formal history resides in S3. Keep a rollback copy and never erase the configured prefix during an update.


**Complete site reconstruction:** the new [site baseline and Checkpoint path](docs/site-snapshot.md) also captures pages, media, theme, menus and presentation data. Read its coverage and remaining change-capture limitations; the Markdown-only scope below describes the original M1 path.

Keep independently usable Markdown originals in S3 and reconstruct published documents in a new WordPress, without the original server or database.

This product path is independent of the earlier research implementation. It consists of a WordPress plugin, Ozeki Markdown Documents, and S3. Python, SSH helpers, a shared worker, Docker and a custom content editor are not product requirements. Existing dm Docker also verified standard EC2 role authentication and restoration without any credential helper.

## Normal use

1. Install and activate Ozeki Markdown Documents and this plugin on WordPress (PHP 8.1+, InnoDB posts/postmeta/options).
2. Supply AWS credentials using the AWS SDK default provider on the server (for example an instance role or environment). Never put secrets into the document or S3 metadata.
3. Open **Tools → Resilience**. Set bucket, region, a dedicated prefix ending with `/`, optionally expected account owner and Object Lock retention days. Enable versioning in the bucket. An existing Object Lock bucket is required when specifying retention. This plugin does not change bucket policies, lifecycle or retention of existing versions.
4. Allow prefix-scoped ListBucket, GetObject/GetObjectVersion and PutObject. Object Lock writes additionally need PutObjectRetention. Saving and recovery do not need deletion rights. Optional cleanup needs separately reviewed version-deletion and lock-inspection rights (docs/checkpoints.md); never grant retention bypass. Use exactly one writing WordPress per prefix. A recovery installation can use a read-only role.
5. Enable protection. Use **Markdown Documents → Add New / Edit**, the usual Markdown field and WordPress Publish/Update buttons.

For a supported save, complete `.md` and metadata are uploaded first. WordPress applies and verifies the source and attributes in an InnoDB transaction. Successful operation history is then written to S3 in confirmation order. Neither Markdown nor Mermaid, formula or code syntax is translated into another storage format. Each version is complete; there are no content deltas and no whole-site manifest on each save.

```
<prefix>/originals/<document-uuid>/<operation-uuid>/source.md
<prefix>/originals/<document-uuid>/<operation-uuid>/metadata.json
<prefix>/history/00000000000000000001.json
```

Download `source.md` at its recorded VersionId with ordinary S3 tools. It is readable without this plugin. History pins raw and metadata versions and SHA-256 values. Failed attempts can leave unadopted originals; those are not formal recovery candidates. Optional dependency-aware cleanup is described in docs/checkpoints.md; it is disabled by default.

## Failures and recovery

- S3-original failure: the protected WordPress write does not start. Return to the editor and retry.
- WordPress apply/verification failure: roll back the transaction; no successful history is added.
- WordPress commit succeeds but formal history write fails: show **history pending**. **Resume history** verifies the applied document and retries the same immutable history key. A lost PUT response is reconciled by reading the existing object. Further protected editing waits for this repair; excluded draft/scheduling operations remain available.
- If the source is lost before formal history is independently persisted, omit that operation by design. For a new article there is nothing to restore; for an update restore the previous confirmed version. Do not adopt prepared originals. Cross-system atomic commit is not claimed or required.
- For site recovery, prepare the destination and use **Restore complete site** as described above and in the site-snapshot guide. For text/attribute-only recovery, select one formal version per asset and **Restore selected assets (text and attributes)**. The result lists identity, selected order, new post ID, hash and status. Repeating individual recovery updates that identity rather than duplicating it.
- Published documents are restored as `publish`. Publication on the internet, server/network access and DNS are the system administrator's responsibility.

Raw Markdown is preserved exactly as received from the normal editor. Normal browser textarea line-ending conversion is not a Resilience conversion. Recorded canonical document URLs are mapped to their new URLs in rendered links, without rewriting raw Markdown. Select the referenced documents as well. Arbitrary old URLs, external resources, embedded shortcodes, relative URL conventions and arbitrary plugin-specific relations are not a general migration engine.

## Retention and limits

An original, its metadata and formal history use the same optional retention cutoff for that operation. Referenced files must remain available for recovery; do not configure lifecycle expiration that removes needed versions. Retention extension remains out of scope. Optional cleanup preserves the latest complete baseline and every retained recovery chain; see docs/checkpoints.md. Independent snapshots and Checkpoints are described in docs/checkpoints.md; their acceptance status is separate from original M1 acceptance. The history listing currently scans the dedicated prefix and is intended for small deployments. Maximum source size is 5 MiB, valid UTF-8 without NUL. Stale normal editor forms are rejected before S3 writes. Concurrent writers from separate WordPress installations to one prefix are unsupported.

Normal authenticated Markdown editing and standard WordPress page/post saves now share S3-first complete-original storage and formal history. Native block HTML remains a complete `source.html`; Markdown remains `source.md`. Trash and untrash state changes are recorded for protected assets (or previously published assets). Whole-site Checkpoint recovery replays these records, including trash, without republishing removed articles. This is not continuous destination synchronization: recovery is explicitly invoked.

The integration covers body, title, slug, publication state, dates, excerpt, parent/order and discussion settings. Image upload/sideload originals are saved to S3 before WordPress registration. Publishing a native post/page binds referenced local images (original and generated sizes, attachment data and alt text) to that successful version; whole-site replay restores these files from S3 and rebases internal URLs. Replacing an image means selecting another image file, not overwriting an existing binary through a third-party plugin. Unused media-library entries, external/CDN images, featured-image changes, taxonomy changes, plugin-specific metadata and arbitrary dynamic block dependencies are not covered by this extension. Existing baseline resources remain available. Article permanent deletion/empty-trash propagation, full recovery of unpublished drafts, scheduling state and automatic protection when a scheduled post publishes remain outside this acceptance. Stale-form rejection is currently provided for the Markdown full editor; native editing retains WordPress's standard controls rather than an additional Resilience version token.

Other exclusions: full standard posts/pages support, general attachments/media-library reconstruction beyond the image path above, business CSV/Excel data, arbitrary third-party plugins, automatic site provisioning, network cutover, legacy migration, advanced monitoring and a standing recovery server. Hooks that commit transactions or perform external side effects during saves are not covered by database rollback. WordPress object-cache compatibility beyond the tested stack needs separate validation.

## Packaging and evidence

The release ZIP contains this plugin and its existing AWS SDK for PHP dependency; acceptance helpers are excluded. Ozeki Markdown Documents remains a separate dependency. See `docs/contract.md` and the acceptance report for measured results and outstanding conditions. No test outcome is implied by this specification.

## Checkpoints

See [Independent snapshots](docs/checkpoints.md) for complete raw files, attributes and inventories and Checkpoint-plus-history recovery. This addition is under integration validation; do not infer live acceptance from this description.

## Comments (current working addition)

Core comments on published/protected posts, pages and Markdown documents now
have complete JSON originals and confirmation-ordered S3 history. Creation,
editing, moderation, trash/untrash and permanent deletion are replayed by
**Restore complete site**, including reply relationships and approved counts.
The adapter freezes the successful operation payload; it does not re-fetch a
comment by ID to create the original. WordPress storage, S3 storage and formal
history must all succeed for recovery confirmation. Core insert/status hooks
supply persisted-result snapshots, not a pre-write input interception. Failed
S3 writes remain pending for **Resume history**, using the same frozen data. If the
source is lost before confirmation, restore the previous confirmed state.
Individual text recovery does not restore comments. See [scope and evidence](docs/comments.md).
