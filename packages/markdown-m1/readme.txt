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

Ozeki Resilience preserves independent originals and confirmed history for supported WordPress content. Start with an administrator-trusted Baseline, preserve supported changes, and create complete Checkpoints from saved S3 resources. Recover a selected point plus confirmed history on a designated destination.

Supported content includes Posts/Pages, local images, core comments, and defined integrations with Ozeki Markdown Documents, Contact Form 7, Flamingo, WP-Members and TablePress. Optional plugins are separately installed. Markdown Documents is required only for Markdown content; native-only sites do not require it. Read the included guides for exact coverage and tested versions.

Installing or activating alone does not enable protection. A versioned S3 bucket, one writing site per dedicated prefix, standard AWS SDK authentication available to PHP, InnoDB, ZipArchive and writable paths are required. Libraries are bundled; no external Python/SSH runtime kit is required. Optional integrations can impose higher PHP requirements.

Only confirmed history is recoverable after source loss. Body saves and associated operations may confirm separately. Unknown captured settings are preserved but not blindly applied. Theme/runtime changes outside tracked operations can require a new trusted Baseline. Source text is limited to 5 MiB and supported images to 32 MiB.

Recovery replaces supported destination state and reproduces saved publication status, including published posts. Prepare a compatible dedicated destination and control network exposure yourself. This is not malware removal, replication, infrastructure provisioning, or an unconditional recovery guarantee. WP-Cron schedules need execution opportunities. Optional cleanup deletes eligible fixed versions only when explicitly enabled; preview itself does not delete.

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
