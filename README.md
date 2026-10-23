# Ozeki WordPress Resilience

**Immutable Assets, Deterministic Reconstruction.**

Preserve business information independently of the WordPress system that presents it. Save an accepted original to S3 **before** applying it to WordPress; when needed, rebuild a new WordPress from those originals instead of restoring the old database.

English | [日本語](RAADME-jp.md)

## How it works

1. Edit a supported post/page or select an image in the protected editor.
2. Store immutable compressed assets and a complete site-generation manifest in S3. Bind exact Version IDs, digests, retention evidence and request-derived expected content to that generation.
3. Apply that confirmed generation to WordPress. A failed save leaves the previous content unchanged. Resume interrupted work with the same request; reject stale edits.
4. Fetch a selected generation from S3 and reconstruct a clean WordPress. Compare its logical content and media with the expected result.

WordPress's database is the operational projection of the originals, not the only recovery source. A generation names its complete asset set; recovering it does not require replaying all parent generations. Unchanged assets can be reused within a retention window; independently retained copies prevent dependence on expired parents.

## Trust model

The accepted material saved before WordPress projection is the original under this design's trust assumption. Hashes, fixed versions and retention protect identity and availability after acceptance; they do not certify that arbitrary supplied content is malware-free. Keep S3 permissions and the writer's journal protected. Independent human approval is an optional policy boundary, not a mandatory action for every edit in the new integrity-based path.

The older independently signed reconstruction path retains its own approval rules. Its signatures are not automatically valid for the new material schema; the new strict-signature policy refuses execution without an integrated verifier.

## This edition: 0.2.0

The release candidate provides a multi-material editor and reconstruction tools. It is not a claim that every WordPress site or production deployment is supported.

| Available | Boundary |
|---|---|
| Multiple posts and pages, stable IDs, page hierarchy | Dedicated enrollment; no automatic existing-site conversion |
| Paragraphs, headings, explicit internal links and image references | No general HTML, Gutenberg blocks, shortcodes or arbitrary Markdown |
| PNG/JPEG registration and replacement | Up to 4 MiB per image; no PDF support |
| S3-first queue, fixed generations, retry and stale-edit rejection | One designated writer host; no distributed writer coordination |
| Rebuild supported content from S3 without the old DB | Private drafts; no automatic public activation |
| Administrator access and normal-write bypass controls | Direct SQL/arbitrary third-party code is outside this control |

Limits are explicit: 1,000 assets per generation and a 64 MiB decompressed closure. The trial's WordPress/DB images are pinned local images; cold runtime bootstrap from S3 alone is not covered.

## Install and operate

Two ZIPs have different purposes:

- `ozeki-wordpress-resilience-0.2.0.zip`: install in WordPress under **Plugins → Add New → Upload Plugin**. Includes the new editor, plus retained compatibility status screens.
- `owr-development-kit-0.2.0.zip`: operator/runtime sources, documentation, tests and retained research/compatibility tools. It is not a WordPress plugin ZIP.

Installing or upgrading does not enable protection by itself. Configure a private request/report bridge, the designated worker, S3 permissions/retention and explicit site enrollment. The current integration requires a guarded dedicated environment (`OWR_RBR_DISPOSABLE=1`, Cron and external HTTP blocked); `OWR_SITE_MATERIALS_BRIDGE` explicitly enables the editor. The worker and WordPress need appropriate shared-directory permissions. No permanent second EC2 is required by the architecture; the included experimental transport is not a general AWS deployment installer.

Once enrolled, ordinary post/page edit and image-registration entry links open **S3先行編集**. Select or add a material, then **S3へ保存して反映**. Inspect pending/failure status and use **同じ要求を再開** when appropriate. Unknown storage outcomes require reconciliation, not blind resend. Invalid queued material currently needs operator correction; a cancellation UI is not implemented.

See [operation and detailed limits](docs/site-materials-v1.md). Credentials and signing keys do not belong in the WordPress editor.

## Upgrades and evidence

Updates preserve existing settings and history and do not silently enroll existing sites. The old three-page schema is not automatically migrated. Keep bridge files, journals and receipts outside the replaceable plugin/runtime directory.

[Real S3 editor/reconstruction evidence](evidence-public/site-materials-editor-validation.json) records 23 browser checks, 19 core/worker tests, 17 acknowledged PUTs and a fresh reconstruction of seven edited assets. ZIP installation/update preservation is a separate test and does not repeat those cloud operations or imply a new signature approval. See [ZIP validation procedure](docs/releases/site-materials-020-zip.md).

Environment failures (including an unresolved read-only WSL timeout), test-harness corrections and product limitations are recorded separately. The historic shortened observation is closed and is not a certification of this new architecture.

## Relationship to Backup for S3 and older code

Ozeki Database Backup for S3 captures and restores an existing site's DB/files. Resilience preserves pre-projection originals and regenerates supported information. Neither plugin requires the other. Useful older guarantees may be transferred only after a concrete gap and dependencies are checked; no transfer is claimed merely from a plan.

Older whole-backup, monitoring and three-page workflows are compatibility/research material, not prerequisites of the new architecture. [Separation inventory](docs/legacy-transfer-inventory.md). Historical evidence and archives remain available; they do not establish current-path coverage.

[License](LICENSE) · [Contributing](CONTRIBUTING.md)

## Final review status

**Release blocked:** the save path can commit a text asset larger than the reconstruction reader accepts (6 MiB per canonical asset). The 64 MiB generation limit alone is insufficient. The frozen ZIP remains unchanged; see [review and required corrections](docs/releases/site-materials-020-review.md). Successful bounded trials do not cover this defect.
