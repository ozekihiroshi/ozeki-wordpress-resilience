=== Ozeki Resilience ===
Contributors: ozekihiroshi
Tags: backup, recovery, amazon s3
Requires at least: 6.4
Tested up to: 7.1
Requires PHP: 8.1
Stable tag: 0.3.3
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Preserve supported site content and confirmed history in Amazon S3, then reconstruct it on a prepared WordPress.

== Description ==

= From originals and history to reconstruction =

Ozeki Resilience preserves supported content as independent originals and confirmed history in your S3 bucket. It reconstructs that supported state on a prepared WordPress, rather than copying a whole server or database image.

Start with a trusted initial capture (Baseline). Enable protection for supported edits, then create Checkpoints from the saved resources and confirmed history. When needed, prepare a compatible destination and recover a selected point plus confirmed history. Checkpoints use what has been saved; untracked live changes may require a new trusted Baseline.

= Supported content =

Posts and Pages, supported local images and core comments are covered. Defined integrations support Ozeki Markdown Documents, Contact Form 7 / Flamingo, WP-Members core subscribers TablePress core tables and ACF free basic fields on posts/pages. See the included README.md for exact coverage and tested versions.

ACF recovery uses the recorded free version (tested 6.8.10), database-defined groups and post/page location rules. PRO, reference/nested fields and PHP/Local JSON definitions are outside this integration. Create a new trusted Baseline when adding ACF or changing its version or definitions.

Optional plugins are installed separately. Markdown Documents is needed only when Markdown content exists. Source text is limited to 5 MiB and supported image files to 32 MiB.

= Scope and responsibilities =

* Protection covers documented content and operations, not arbitrary plugins, all settings or external/CDN resources. Keep separate protection for resources outside this scope.
* After source loss, recovery uses confirmed history. A visible edit can still be pending, and body and related operations may confirm separately. Monitor the save status.
* Recovery replaces supported destination state and restores saved publication status. Prepare a compatible dedicated destination and control its public access.
* This product reconstructs saved state; malware removal, server provisioning and continuous replication are outside its role. Recovery depends on the required saved resources and a suitable environment.

= Getting ready =

Prepare a versioned S3 bucket, a dedicated prefix with one writing site, appropriate permissions and standard AWS SDK credentials available to PHP. InnoDB, ZipArchive and writable paths are required. Libraries are bundled; no external Python/SSH runtime kit is needed. Optional integrations may require a higher PHP version.

Installation alone does not enable protection: create and confirm a trusted Baseline, then enable protection. Follow docs/user-guide.md for setup, pending saves, recovery and retention. Optional schedules need WP-Cron execution opportunities; cleanup deletes eligible versions only when explicitly enabled, while preview does not delete.

= External services and privacy =

This plugin connects to Amazon Web Services (AWS), primarily Amazon S3, using your configured account/bucket/region/prefix and the bundled AWS SDK. AWS may charge for storage and requests. Terms: https://aws.amazon.com/service-terms/ ; privacy: https://aws.amazon.com/privacy/ .

After storage settings and the terms confirmation are saved, checking storage reads bucket versioning and the dedicated prefix. The terms version, time and administrator ID are recorded locally. When you request capture, enable protection for supported edits, request recovery/preview/cleanup, or enable scheduled Checkpoints/cleanup, the plugin sends the corresponding requests to AWS. Saved resources can include article text, images, comments, form submissions, subscriber personal data, recognized settings, software names/versions and reconstruction metadata. Configure access and retention appropriately and inform your site's users. Cleanup can send deletion requests. Displaying configured storage/history can make read requests. Credential providers may contact AWS instance metadata or STS as required by your server's standard SDK configuration. No AWS keys are entered in this plugin's settings screen.

No analytics or telemetry is sent to the developer. AWS access and credentials are provided by your administrator. There is no separate developer-operated storage service.

= Documentation and source =

User guide, AWS policies, terms of use (docs/terms-of-use.md; Japanese: docs/terms-of-use-ja.md) and installation/update instructions are included in docs/.
Source and build tools: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/release/wordpress-org/packages/markdown-m1
Support: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues

Install WordPress, themes and required plugins separately from trusted distributors before recovery, and activate the required plugins. Resilience restores information assets and their supported relationships; it does not install or activate software from S3. It keeps the destination theme selection. Unknown settings are reported without being applied.

== Installation ==

1. Prepare a versioned S3 bucket, dedicated prefix and permissions using docs/aws-setup.md (Japanese: docs/aws-setup-ja.md). Provide standard SDK credentials to PHP.
2. Upload ozeki-resilience-0.3.3.zip using Plugins > Add New Plugin > Upload Plugin and activate. For an old prerelease in ozeki-wordpress-resilience/, deactivate that copy first; do not activate both. Preserve settings and pending records; see docs/install-update.md.
3. Open Tools > Resilience. Follow Preparation for protection, choose Protect this site, configure storage with protection and cleanup initially disabled, read the terms and select the confirmation checkbox. Save settings, then Check storage.
4. Pause editing, judge the source trustworthy, and create a complete initial snapshot (Baseline). Confirm success before enabling protection and saving settings with the terms confirmation.
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

= 0.3.3 =
* Validate recovery references before storage, sanitize nonces, and escape rendered URL attribute changes with the WordPress HTML API.
* Update AWS SDK; respect host file-modification restrictions during recovery; limit detailed notices to the plugin screen.
* Preparation distinguishes ACF free, PRO and unused ACF; guides creating an initial save for the current free version. ACF PRO fields are outside protection.
* Preserve and recover 15 basic ACF free field types on posts/pages, including values, definitions and field-key references.
* Preserve literal text types and hyphenated field names during ACF recovery.
* For ACF protection after updating, create a new trusted Baseline with the supported ACF free version active. See docs/acf-free.md.

= 0.3.2 =
* Setup readiness shows missing conditions and next actions; storage checks use read-only requests.
* Terms confirmation and a completed first capture guide starting protection.
* Japanese/English administration screens and updated setup/recovery guides.
* Existing settings and protection are retained when updating from 0.3.1.

= 0.3.1 =
* Initial WordPress.org submission candidate based on the current 0.3.1 implementation.
* Public name and installation directory changed to Ozeki Resilience / ozeki-resilience; stored settings and history keys retained.
