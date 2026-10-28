# Ozeki Resilience

**Development version:** Current source is `0.3.2-dev`, with a [setup readiness screen and terms confirmation](packages/markdown-m1/docs/setup-readiness.md). The admin screen follows the Japanese or English user language. The submitted `0.3.1 rc.2` ZIP is unchanged.

Preserve the articles, images and inquiries your site has accumulated, so you can resume publishing and serving users after a cyberattack. Ozeki Resilience saves supported content and provides a path to recovering it on a separate WordPress.

English | [日本語](RAADME-jp.md)

Ozeki Resilience **0.3.1 (rc.2) was submitted to WordPress.org on October 26, 2026**. Status: **Awaiting Review — not yet approved or published in the WordPress.org Plugin Directory**. It supersedes the obsolete 0.2.0 submission candidate; neither the old plugin ZIP nor its external runtime kit is required.

## Keep a path to recovery after an attack

Losing a site should not mean losing the information and relationships built through it. Ozeki Resilience preserves articles, images, comments and supported inquiry and member information, then restores them on a separate WordPress so you can resume publishing and serving users.

Backup and restore prepare you to return a site to a captured state. Resilience prepares you to **bring back the content needed to continue your work when restoring the attacked site as it stood is not an option**. Its priority is preserving valuable content and making it usable again, rather than carrying over the entire original environment.

The scope balances the value of what is preserved with the work needed to handle and restore it safely. The tables below show what is saved and restored, and what you prepare separately on the destination.

## Download and start

1. Download **[ozeki-resilience-0.3.1.zip](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.1-rc.2/ozeki-resilience-0.3.1.zip)** and verify it against the release's `SHA256SUMS`. [Release files and matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2).
2. Read the [first-time setup guide](packages/markdown-m1/docs/user-guide.md) and prepare [AWS access](packages/markdown-m1/docs/aws-setup.md).
3. Install the ZIP, configure **Tools → Resilience**, create a trusted initial Baseline, then enable protection. Installing or activating alone does not protect a site.

Use the installable ZIP, not GitHub's source archive. Runtime libraries are bundled. **No Python worker, SSH helper, external runtime kit, Docker or continuously running recovery server is required.** Standard AWS SDK credentials must be available to PHP; the guide uses an EC2 instance role. AWS charges are separate.

## Requirements and supported content

WordPress 6.4+, PHP 8.1+, ZipArchive, InnoDB and writable resource paths are required. Prepare a versioned S3 bucket and dedicated prefix, one writing site per prefix, and appropriate IAM permissions. Recovery requires a compatible WordPress release line, recorded plugin dependencies and private writable staging outside the web root. The current controls are English.

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
| Site appearance included in the initial capture | Selected themes and supported presentation settings. Capture a new initial state after later theme changes |

Install the integration plugins you need separately. Versions above are the tested versions. Contact Form 7 6.2.3 requires PHP 8.3+. Source text can be up to 5 MiB and supported images up to 32 MiB.

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
2. Save supported changes during daily use. A **Checkpoint** is a recovery point made from what has already been saved. Follow [the change procedures](packages/markdown-m1/docs/start-here.md) after changes such as theme updates.
3. When needed, prepare a separate WordPress and select the initial capture or recovery point and the changes to restore.
4. Check the articles, images, inquiries and other content you need, along with items reported as not applied, then reopen the site and resume service.

Check completed saves under **Save protection status**. If operations remain pending, follow [save resumption](packages/markdown-m1/docs/save-resume.md). Recovery also restores saved publication state, so restrict public access while checking the destination. When responding to an attack, select a trusted initial capture and the changes you decide to adopt.

The [user guide](packages/markdown-m1/docs/user-guide.md) covers schedules, retention and cleanup. See the [recovery FAQ](packages/markdown-m1/docs/recovery-faq.md) for details of recovery behavior.

## Documentation and support

- [Terms of use](packages/markdown-m1/docs/terms-of-use.md): license, operational roles, data, costs, warranty and liability
- [Install and update](packages/markdown-m1/docs/install-update.md), including migration from the old prerelease folder
- [Recovery procedure](packages/markdown-m1/docs/user-guide.md#6-recover-onto-a-separate-wordpress) and [recovery FAQ](packages/markdown-m1/docs/recovery-faq.md)
- [Application rules and withheld information](packages/markdown-m1/docs/application-rules.md)
- [External-service and privacy disclosure](packages/markdown-m1/readme.txt)
- [Candidate checks and build instructions](packages/markdown-m1/docs/wordpress-org-candidate.md)

[Report an issue](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues) with the exact ZIP/hash, operation, error and runtime versions. Remove credentials and private content. Existing verification records describe their specific builds and environments; they are linked from the candidate record, not additional installation requirements.

[License](LICENSE). Ozeki Database Backup for S3 is an independent product.

Setup assistance assessment: [current pre-setup checks](packages/markdown-m1/docs/setup-preflight-review.md) (includes proposals not yet implemented).
