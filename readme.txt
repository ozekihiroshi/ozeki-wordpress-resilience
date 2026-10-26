=== Ozeki Resilience ===
Contributors: ozekihiroshi
Requires at least: 6.8
Tested up to: 7.1
Requires PHP: 8.1
Stable tag: 0.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html
Tags: backup, recovery, amazon s3

Save supported content to immutable S3 generations before applying it to WordPress; reconstruct it with a separately configured worker.

== Description ==

Ozeki Resilience is the WordPress interface for an operator-managed content preservation and reconstruction workflow. Supported posts, pages and PNG/JPEG images are committed to immutable S3 generations before WordPress is updated. Reconstruction uses those materials without the original WordPress database.

This plugin requires a matching external worker and explicit site enrollment. Activation alone does not protect content, configure AWS, or install the worker. It is intended for administrators of dedicated, configured environments. The supplied S3 transport currently requires the dedicated SSH signing environment described in the source kit; it is not a general-purpose AWS account setup wizard. The filesystem test transport does not provide S3 protection.

The standard block editor supports basic paragraph, heading, list, quote and image blocks, with basic links and emphasis. Unsupported input is rejected. Only administrators can use protected editing. Classic Editor, third-party Markdown editors, custom/dynamic blocks, forms, taxonomy/custom fields, scheduling and automatic migration of existing content are not supported.

Reconstruction restores saved post status, INCLUDING published status. It does not configure DNS, TLS, web-server access restrictions or an independent publication approval. On a publicly accessible recovery site, restored published posts may be visible immediately. The operator must prepare and restrict the recovery destination before requesting reconstruction. This is not a whole-site backup, malware scanner or guarantee of recovery from every incident.

= External services and data =

* Amazon Web Services S3: after the administrator explicitly configures the external worker and enrolls the site, supported post/page content, titles, slugs, relationships, publication status, image originals/alternative text and generation/integrity metadata are sent to the configured storage by that worker. Reconstruction reads the selected fixed versions. An AWS account and storage/requests may incur charges. Object Lock retention can prevent deletion until expiry. Service: https://aws.amazon.com/s3/ ; terms: https://aws.amazon.com/service-terms/ ; privacy: https://aws.amazon.com/privacy/ .
* Operator-managed SSH signing hosts: the supplied S3 transport sends storage request metadata (operation, object key/version and integrity/retention parameters) to separately provisioned signing hosts. Content is transferred to S3 using the authorized requests. The operator is responsible for these hosts, access and storage configuration; see the setup documentation.
* Pushover (optional retained notification interface): only when configured with the external notification runtime, alerts and delivery/acknowledgement requests are sent to Pushover using the configured recipient/application credentials. The runtime manages those credentials; this plugin stores channel settings, recipient labels and notification status. Service: https://pushover.net/ ; terms: https://pushover.net/terms ; privacy: https://pushover.net/privacy .
* SMTP (optional): the external notification runtime sends configured alerts to the selected email recipient through the operator's SMTP provider. That provider's terms and privacy policy apply.

The plugin does not automatically enroll a site or start external communication on activation. No AWS credentials or signing keys belong in its administration forms. Local bridge files can contain site content; keep them outside the public document root with restricted permissions. Settings, history and external journals are preserved when deactivated or removed; uninstalling does not delete retained S3 objects. Operators must manage their retention and data-removal obligations separately.

== Installation ==

1. Upload the plugin ZIP in Plugins > Add New > Upload Plugin and activate it. PHP 8.1 or later is required; protected native editing additionally needs PHP DOM.
2. Obtain the matching 0.2.0 operator sources from https://github.com/ozekihiroshi/ozeki-wordpress-resilience . Operator sources are separate from the WordPress plugin ZIP. Use the release-matched revision; do not mix workers and plugin versions.
3. Follow the bundled setup.txt for the source location, dedicated environment requirements, bridge/enrollment settings and recovery target configuration. Provision the external worker/signing environment before enabling protected editing.
4. If replacing a GitHub preview installed as `ozeki-wordpress-resilience`, first deactivate that preview, then install and activate this `ozeki-resilience` package. Do not activate both directories together. Settings and external journals use the same existing keys/paths; no data migration is performed. Remove the old plugin code only after checking the new installation.
5. Retain configuration, journals, receipts and pending requests outside replaceable plugin/runtime directories when upgrading. Update the external runtime together with the plugin.

== Frequently Asked Questions ==

= Does activation alone start protection? =
No. Explicit enrollment, a compatible external runtime and storage configuration are required. Without them the retained status/settings screens show their unconnected state.

= What is the recovery publication boundary? =
Saved draft, pending, private and publish states are restored. Network access and publication approval are the operator's responsibility, not an automatic safeguard provided by the plugin.

= What are the size and workflow limits? =
PNG/JPEG images up to 4 MiB and 10,000 pixels per dimension; 1,000 assets per generation; 6 MiB canonical text per asset, 8 MiB per stored object and 64 MiB decompressed closure. One designated writer host is supported. No automatic existing-site or legacy three-page migration. Internal page-anchor links are rejected. An uncertain storage result needs operator reconciliation; never erase its journal and blindly resend.

== Changelog ==

= 0.2.0 =
S3-first native post/page/image editing, immutable generations, same-operation resume and reconstruction. This submission candidate preserves saved recovery post statuses and documents operator-controlled exposure. Distribution metadata, external-service disclosures and administration script loading have been prepared for directory review.

== Upgrade Notice ==

= 0.2.0 =
Update the matching external runtime as well. Settings, histories and journals remain intact. Recovery preserves saved publication status; restrict the target before reconstruction. No automatic enrollment or legacy migration.
