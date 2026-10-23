=== Ozeki WordPress Resilience ===
Requires PHP: 8.1
Stable tag: 0.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Immutable assets, deterministic WordPress reconstruction.

== Description ==
Save supported posts, pages and images as immutable S3 originals before applying them to WordPress. Reconstruct supported business information without the original WordPress database.
The supplied dedicated-environment workflow supports private drafts, bounded text nodes and PNG/JPEG. It requires explicit enrollment and a separately configured worker. Installing or upgrading alone does not enable protection. General Gutenberg/classic editing and production publication are not supported by this edition.

== Installation ==
Upload this ZIP in Plugins > Add New > Upload Plugin and activate it. Existing settings remain unchanged.
Follow README.md and docs/site-materials-v1.md in the accompanying runtime kit for dedicated enrollment, worker configuration and scope.
Do not put AWS credentials or signing keys in the administration screen.

== Upgrade Notice ==
= 0.2.0 =
Adds the explicitly enrolled multi-material editor. Existing options, legacy history and external journals are preserved. Legacy three-page data is not automatically converted.

== Changelog ==
= 0.2.0 =
S3-first multi-post/page/image editor, immutable generations, same-operation resume and shared WordPress projection.
