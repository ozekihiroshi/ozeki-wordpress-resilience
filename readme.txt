=== Ozeki WordPress Resilience ===
Requires PHP: 8.1
Stable tag: 0.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Immutable assets, deterministic WordPress reconstruction.

== Description ==
Save supported posts, pages and images as immutable S3 originals before applying them to WordPress. Reconstruct supported business information without the original WordPress database.
The explicitly enrolled dedicated-environment workflow supports administrator editing of posts/pages, publication intent and PNG/JPEG through the standard block editor. Only basic paragraph, heading, list, quote and image blocks with basic links/emphasis are supported. Custom/dynamic blocks, forms, taxonomy/custom fields, scheduling, Classic Editor and Markdown plugins are unsupported. A separately configured matching worker and PHP DOM are required; installing or upgrading alone does not enable protection. Reconstructed targets remain private and are never automatically published.

== Installation ==
Upload this ZIP in Plugins > Add New > Upload Plugin and activate it. Existing settings remain unchanged.
Follow README.md and docs/native-wordpress-editor.md in the accompanying runtime kit for dedicated enrollment, worker configuration and scope.
Do not put AWS credentials or signing keys in the administration screen.

== Upgrade Notice ==
= 0.2.0 =
Adds native standard-editor integration for explicitly enrolled multi-material sites; update the matching external runtime as well. Existing options, legacy history and external journals are preserved. Legacy three-page data is not automatically converted.

== Changelog ==
= 0.2.0 =
S3-first native post/page/image editing, immutable generations and request-derived Q, same-operation resume, private reconstruction and preview. Media registration waits asynchronously for S3 commitment; source and recovery HTML share KSES canonicalization.
