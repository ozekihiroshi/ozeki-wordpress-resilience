# Ozeki Resilience

**0.3.3 rc.14 is the latest GitHub candidate, not yet submitted to WordPress.org.** It adds setup guidance and recovery prerequisite checks. Submitted rc.13 remains awaiting the reviewer response; publication is not approved. [Distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

Preserve the articles, images and inquiries your site has accumulated, so you can resume publishing and serving users after a cyberattack. Ozeki Resilience saves supported content and provides a path to recovering it on a separate WordPress.

English | [日本語](RAADME-jp.md)

See the [Flamingo correction, missed-check cause and regression coverage](packages/markdown-m1/docs/flamingo-recovery-fix.md). This fix is included in rc.13, not submitted rc.12.


## Keep a path to recovery after an attack

Ozeki Resilience helps you resume your work with accumulated articles, images and supported inquiry and member information when a cyberattack or other incident leaves the original site untrustworthy. Keep your backup and restore arrangements; **Resilience provides a path to recovering information when bringing back the original environment as it stood is not an option.**

This purpose leads to a design principle: preserve information as independent originals, separate from the system that created it. **Preserved originals have value independent of the recovery engine.** Coverage balances the value of the information with the work needed to recover it safely.

Prepare a fresh WordPress destination, then separately install and activate the necessary trusted software. S3 supplies supported information assets and their required relationships. **Recovery does not deploy or execute archived theme/plugin code, and applies only recognized settings.** It keeps the destination theme selection and reports items it did not apply.

The aim is not to minimize storage or make restoration as fast as possible. Independent originals and additional recovery points provide reserves and room to recover when needed, so information can remain usable. Storage, transfers and read-back time are part of maintaining that reserve.

Protecting standard WordPress Posts and Pages requires no additional plugin. Recovering information specific to an integration requires its compatible plugin version, installed separately. The table below distinguishes recovered content from software you prepare.

| Item | Handling |
|---|---|
| WordPress core | Install fresh |
| Themes | Reinstall from trusted distributors |
| Plugins | Reinstall from trusted distributors |
| Posts and Pages | Recover from independent originals preserved in S3 |
| Images and attachments | Recover saved supported formats from S3 originals |
| Settings and metadata | Apply only recognized items selectively |
| Members, inquiries and tables | Recover according to the supported adapter rules |


## Download and start

1. Check [current distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md) for installable ZIP availability. Use the ZIP and SHA-256 on that page; do not select an earlier review package or `Source code (zip)`.
2. Read the [first-time setup guide](packages/markdown-m1/docs/user-guide.md) and prepare [AWS access](packages/markdown-m1/docs/aws-setup.md).
3. Install the ZIP, open **Tools → Resilience**, follow the preparation checklist, confirm storage access and create a trusted initial Baseline, then enable protection. Installing or activating alone does not protect a site.

Use the installable ZIP, not GitHub's source archive. Runtime libraries are bundled. **No Python worker, SSH helper, external runtime kit, Docker or continuously running recovery server is required.** Standard AWS SDK credentials must be available to PHP; the guide uses an EC2 instance role. AWS charges are separate.

## Requirements and supported content

WordPress 6.4+, PHP 8.1+, ZipArchive, InnoDB and writable resource paths are required. Prepare a versioned S3 bucket and dedicated prefix, one writing site per prefix, and appropriate IAM permissions. Recovery requires a compatible WordPress release line, recorded plugin dependencies and private writable staging outside the web root. The controls follow your WordPress admin language: Japanese or English.

**Markdown dependency:** Native-only Baseline and recovery do not require Markdown Documents. If active it is included; if documents or `_ozmd_source` originals remain while inactive, capture stops before saving. For Markdown recovery, install and activate the recorded compatible version first (tested 0.1.1).

<a id="supported-content-and-plugins"></a>

## What remains and what you can recover

Restore successfully saved content through the recovery point you select. Integrations cover the plugins named in this table.

| What is preserved | What you can recover |
|---|---|
| Posts, Pages and local images | Body, supported images, publication state, categories, tags, featured images and related information needed to use the articles |
| Core comments | Comments and moderation state, including saved edits and deletions |
| Markdown documents | Source and supported relationships. Ozeki Markdown Documents 0.1.1 |
| Inquiry forms and received inquiries | Forms and the inquiries you received. Contact Form 7 6.2.3 / Flamingo 2.6.4 |
| Member access | Core subscriber information and supported fields, settings and viewing restrictions. WP-Members 3.5.8.1 |
| Tables | Table content, supported display settings and references. TablePress 3.4.1 |
| ACF free basic fields | Values, definitions and field keys for 15 basic types on posts/pages. ACF free 6.8.10. Create a new trusted Baseline including ACF after updating |
| Site appearance included in the initial capture | Supported presentation settings for the separately prepared theme; software names and versions help reinstallation |

Install the integration plugins you need separately. Versions above are the tested versions. Contact Form 7 6.2.3 requires PHP 8.3+. Source text can be up to 5 MiB and supported images and attachments up to 32 MiB per file.

<a id="what-the-product-checks"></a>

## What is excluded from recovery, and why

Preserving content is separate from carrying over the original site's administrative access and entire operating environment.

| Excluded from recovery | Reason and handling |
|---|---|
| Original administrator logins, active sessions, AWS and mail connection secrets | Use access prepared on the destination instead of carrying over the original environment's administrative access and connections. Supported core subscriber information is covered above |
| Server/PHP configuration, DNS and external service or CDN resources | These belong to the destination or external service. Prepare their configuration and protection through those systems |
| Plugin-specific features and data outside the coverage table, and arbitrary custom settings | Each needs dedicated support to restore its behavior safely. This product focuses on the scope listed above |
| Saved settings whose handling is not defined | To avoid bringing back unknown behavior, these are withheld from automatic application and listed in the result. Saved information remains in S3 |

Use backups or the relevant service's protection for assets outside this scope. Resilience preserves and restores the content needed to resume your site's work.

## From preservation to resuming service

1. Capture a trusted initial site state as a **Baseline** and enable protection.
2. Save supported changes during daily use. A **Checkpoint** is a recovery point made from what has already been saved. Follow [the change procedures](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/start-here.md) after changes such as theme updates.
3. When needed, prepare a separate WordPress and select the initial capture or recovery point and the changes to restore.
4. Check the articles, images, inquiries and other content you need, along with items reported as not applied, then reopen the site and resume service.

Check completed saves under **Save protection status**. If operations remain pending, follow [save resumption](packages/markdown-m1/docs/save-resume.md). Recovery also restores saved publication state, so restrict public access while checking the destination. When responding to an attack, select a trusted initial capture and the changes you decide to adopt.

The [user guide](packages/markdown-m1/docs/user-guide.md) covers schedules, retention and cleanup. See the [recovery FAQ](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/recovery-faq.md) for details of recovery behavior.

## Documentation and support

- [Terms of use](packages/markdown-m1/docs/terms-of-use.md): license, operational roles, data, costs, warranty and liability
- [Install and update](packages/markdown-m1/docs/install-update.md), including migration from the old prerelease folder
- [Recovery procedure](packages/markdown-m1/docs/user-guide.md#6-recover-onto-a-separate-wordpress) and [recovery FAQ](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/recovery-faq.md)
- [Application rules and withheld information](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/application-rules.md)
- [External-service and privacy disclosure](packages/markdown-m1/readme.txt)
- [Current distribution status and matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md)

**Problems or questions?** Use [GitHub Issues](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues). For a bug, choose the [English or Japanese report template](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues/new/choose) and describe the operation, expected result, actual result and versions as far as you know. Questions can use a blank issue. Reports are public; omit credentials and private content.

After publication on WordPress.org, the plugin page's **Support** tab will also accept questions and bug reports. The reviewer requested changes to rc.8; rc.9 addresses that feedback. We track fixes in GitHub Issues; if a report is already on one service, link it from the other instead of repeating the details. WordPress.org review emails are separate from user support.

Existing verification records describe their specific builds and environments; they are linked from the candidate record, not additional installation requirements.

[License](LICENSE). Ozeki Database Backup for S3 is an independent product.

Preparation: [current setup checklist](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/setup-readiness.md).

[ACF free basic fields — 0.3.3 coverage](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/acf-free.md).

[文書案内 / Documentation index](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/README.md)
