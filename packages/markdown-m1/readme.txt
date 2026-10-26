=== Ozeki Resilience ===
Contributors: ozekihiroshi
Tags: backup, recovery, amazon s3
Requires at least: 6.4
Tested up to: 7.1
Requires PHP: 8.1
Stable tag: 0.3.1
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Preserve supported site content and confirmed history in Amazon S3, then reconstruct it on a prepared WordPress.

== Description ==

= How this product works =

Ozeki Resilience reconstructs supported WordPress state from saved originals and confirmed history. It is not a whole-server image or a general database-and-files backup that can reproduce every part of an arbitrary WordPress installation. Understand the supported scope before relying on it for recovery.

1. Baseline: an administrator judges the current site trustworthy, pauses editing and captures an initial supported recovery set.
2. Protected operations: supported edits preserve originals and confirmed history in your S3 bucket. A visible WordPress change is not, by itself, proof that its history is confirmed.
3. Checkpoint: build an independent supported recovery set from the saved Baseline and confirmed S3 history. This does not scan the live site for untracked changes.
4. Recovery: prepare a compatible WordPress destination and reconstruct a selected point plus the required confirmed history. The destination is not continuously synchronized.

= Supported scope =

* Posts and Pages: body, recorded attributes, Trash/restore/deletion, featured images and category/tag assignments.
* Local images: supported originals, referenced files and attachment information.
* Core comments: creation, editing, moderation and deletion.
* Defined integrations: Ozeki Markdown Documents sources and supported relationships; Contact Form 7 form definitions and Flamingo received inquiries; WP-Members core subscriber accounts, recognized fields/settings and viewing restrictions; TablePress core tables, recognized options and references.

These are defined integrations, not coverage of every extension or version. Optional plugins are installed separately. Markdown Documents is required only when Markdown content exists; native-only sites do not require it. See the included README.md and docs/user-guide.md for exact coverage and tested versions. Source text is limited to 5 MiB and supported image files to 32 MiB.

= Outside scope and recovery limits =

* Arbitrary plugins/extensions, all metadata, external/CDN resources and every later settings change are not automatically protected. Captured selected theme/plugin files do not imply continuous protection of all code changes. Theme/runtime or other untracked changes can require a new trusted Baseline; a normal Checkpoint does not discover them.
* Only confirmed history is recoverable after source loss. Body saves and associated operations may confirm separately. WordPress and S3 do not form one atomic transaction; an unconfirmed change must not be counted as recoverable.
* Unknown captured settings are preserved but not blindly applied. Recovery is not an unrestricted copy of all source settings, identities or credentials. Prepare a working destination administrator login; source administrator credentials are not restored.
* This is not malware detection/removal or certification that saved content and code are safe. It is not replication, infrastructure provisioning, mail replay or an unconditional recovery guarantee.
* Recovery replaces supported destination state and reproduces saved publication status, including published posts. A failed recovery must not be assumed to have left the destination unchanged; a local rollback copy is not a promise of automatic rollback.

Keep other backup arrangements until you have confirmed the supported recovery scope for your own site. This product does not promise to replace protection for resources outside that scope.

= What the administrator must prepare =

Installing or activating alone does not enable protection. Prepare a versioned S3 bucket, a dedicated prefix with one writing site, appropriate permissions and standard AWS SDK authentication available to PHP. InnoDB, ZipArchive and writable paths are required. Libraries are bundled; no external Python/SSH runtime kit is required. Optional integrations can impose higher PHP requirements.

Create a trusted Baseline and confirm success before enabling protection. Monitor confirmed history and pending saves. For recovery, prepare a compatible dedicated WordPress, the recorded required plugins, a working administrator login and private writable temporary storage. Control network exposure and DNS yourself; recovery does not make published content private.

WP-Cron schedules need execution opportunities and are not exact-time guarantees. Keep required S3 versions and access available. Optional cleanup deletes eligible fixed versions only when explicitly enabled; preview itself does not delete. Follow docs/user-guide.md for setup, pending operations, retention and recovery.

= External services and privacy =

This plugin connects to Amazon Web Services (AWS), primarily Amazon S3, using your configured account/bucket/region/prefix and the bundled AWS SDK. AWS may charge for storage and requests. Terms: https://aws.amazon.com/service-terms/ ; privacy: https://aws.amazon.com/privacy/ .

When you configure storage and request capture, enable protection for supported edits, request recovery/preview/cleanup, or enable scheduled Checkpoints/cleanup, the plugin sends the corresponding requests to AWS. Saved resources can include article text, images, comments, form submissions, subscriber personal data, recognized settings, selected theme/plugin files and reconstruction metadata. Configure access and retention appropriately and inform your site's users. Cleanup can send deletion requests. Displaying configured storage/history can make read requests. Credential providers may contact AWS instance metadata or STS as required by your server's standard SDK configuration. No AWS keys are entered in this plugin's settings screen.

No analytics or telemetry is sent to the developer. AWS access and credentials are provided by your administrator. There is no separate developer-operated storage service.

= Documentation and source =

User guide, AWS policies and installation/update instructions are included in docs/.
Source and build tools: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/release/wordpress-org/packages/markdown-m1
Support: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues

== Installation ==

1. Prepare a versioned S3 bucket, dedicated prefix and permissions using docs/aws-setup.md (Japanese: docs/aws-setup-ja.md). Provide standard SDK credentials to PHP.
2. Upload ozeki-resilience-0.3.1.zip using Plugins > Add New Plugin > Upload Plugin and activate. For an old prerelease in ozeki-wordpress-resilience/, deactivate that copy first; do not activate both. Preserve settings and pending records; see docs/install-update.md.
3. Open Tools > Resilience and configure storage with protection and cleanup initially disabled.
4. Pause editing, judge the source trustworthy, and create a complete initial snapshot (Baseline). Confirm success before enabling protection.
5. Monitor confirmed history and pending saves. Follow docs/user-guide.md for Checkpoints, retention and recovery.

== Frequently Asked Questions ==

= Is this a full copy of my server or database? =
No. It reconstructs documented supported state from a trusted Baseline and confirmed saved history. Checkpoints do not discover untracked live changes. Read the scope and limits above before choosing it for your site.

= Does installation protect all site content automatically? =
No. Configure storage, create a trusted Baseline and enable protection. Only documented content/operations are covered.

= Is Markdown Documents always required? =
No. Native-only Baselines/recovery do not require it. If Markdown documents or originals exist, activate the compatible plugin before capture/recovery.

= Does recovery keep published posts private? =
No. Saved publication state is restored. Use a designated destination with access restrictions and decide separately when to expose it.

= Is a second server always running? =
No. Prepare a compatible destination when recovery is needed. Python workers, SSH helpers and Docker are not product requirements.

== Changelog ==

= 0.3.1 =
* Initial WordPress.org submission candidate based on the current 0.3.1 implementation.
* Public name and installation directory changed to Ozeki Resilience / ozeki-resilience; stored settings and history keys retained.
