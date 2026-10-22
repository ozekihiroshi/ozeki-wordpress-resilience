# Portable content extraction increment

English primary | [日本語](portable-content-extraction-jp.md)

This implements only the extraction part of the [Reconstruct proposal](../spec/portable-reconstruct-minimum.md). It does not generate a static website or change existing approvals, backup/restore behavior, AWS or production configuration.

## Entry points and artifacts

`tools/portable-content-export.php` is a CLI collector invoked after a trusted WordPress bootstrap. It accepts an explicit JSON array of up to 200 source IDs, reads published standard pages/posts without passwords, selected metadata and referenced original attachment bytes. It parses block names but never calls render_block, the_content or shortcode rendering. All custom metadata values are excluded; unmapped key names are reported. Source rows/metadata are compared before/after. Bootstrap and permalink/upload helpers still run in WordPress and can involve installed hooks; this is not a safe forensic execution path for a compromised source.

`tools/portable-content.py --source SOURCE.json --output NEW_DIRECTORY` performs offline extraction using Python's standard library. It never fetches a URL or executes imported code. Existing output directories are refused; failures leave an incomplete manifest, never a successful package. Source size is capped at 64 MiB; each image at 8 MiB, total 32 MiB; page bodies at 2 MiB. These are initial trial limits.

Artifacts: exact selected raw records (not a public folder), typed body events in content/*.json, readable/*.txt, copied image bytes and media-index.json, relations.json, issues.json, checksums and status in manifest.json. Readable plain text is used at this stage; Markdown rendering and HTML generation are deliberately not implemented. Semantic body structure remains in JSON. Keep the whole directory private: raw HTML and images are untrusted source material, not safe-to-publish assets.

Relationships distinguish parent, inline links including anchors, inline image and featured image. Unknown destinations, unsafe schemes, missing anchors and images remain unresolved issues. Exact stored URLs are matched; aliases, resized image URLs, relative image discovery and complex navigation need further support. Menus, taxonomy and theme header/footer are explicitly uncollected dependencies, not silently claimed complete.

Basic HTML is parsed into text/structural events and reference records. Active elements are excluded from normalized text; source bytes stay in raw data. Unsupported blocks, HTML/attributes, shortcode-like text, malformed markup and unmapped metadata receive location/page-specific issues. This is extraction, not a publication sanitizer: unknown constructs can retain readable text, which remains partial and must not be treated as approved rendering.

Image bytes are copied under safe numeric names, with hashes; traversal/symlink paths are rejected by the collector. Only signatures identify PNG/JPEG candidates. Images are **not decoded, re-encoded, sanitized or proven harmless**; this is recorded per image. Other bytes remain restricted `.bin` originals and are flagged. Missing files are reported rather than replaced by network downloads.

## Scope and next boundary

The adapter uses a trusted, explicit CLI bootstrap; no administrative screen, production enrollment or arbitrary hosting connector is provided. Non-atomic before/after source observations do not prove an atomic snapshot or source honesty. Markers and unresolved items remain visible. No safe-publication decision, clean-source assertion or automatic repair is inferred.

The dedicated corporate fixture uses the existing network-isolated WordPress/MariaDB lab with three published pages, one real image, one absent image, a private draft, broken link, unsupported table/dynamic block/shortcode and builder metadata. The test compares DB checksums before/after collection, checks private values are excluded, verifies independent file bytes/relations/losses and repeated-output determinism. Source writes are limited to fixture creation in the disposable lab. This is new extraction coverage, not another restore test.

Future work: broader image/reference discovery, explicit menus and reusable blocks, stronger acquisition consistency, image decoding policy and operator-required page selection. Static generation is implemented separately by [portable-preview.py](portable-preview.md); this collector does not generate HTML. No automatic coupling with Backup for S3.

## Acceptance result — 2026-10-22

10 unit tests and 10 actual generated-WordPress checks passed. Package: 3 pages, 1 copied image, 6 relationships, 16 explicit issues (including the deliberately absent image/unexported draft and unsupported content). DB checksums were unchanged across collection. The package hashes, readable texts and media files were verified again after the source containers had been removed. No HTML/static site was generated. [Evidence](../../evidence-public/portable-content-extraction.json).

The first lab attempt failed because WordPress sanitized the intended script fixture while creating the page. Inspection of saved raw source established that the script never reached the collector. This was a test-infrastructure defect: the corrected fixture uses a direct generated-data DB update and asserts script presence before collection. The first attempt remains preserved. No new environment failure or product defect was identified in the final tested scope. This is not a production compatibility claim.
