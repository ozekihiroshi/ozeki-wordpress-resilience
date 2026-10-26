# Ozeki Resilience

Preserve supported site content in Amazon S3 and reconstruct it on a prepared WordPress when the original site is lost or cannot be trusted.

English | [日本語](RAADME-jp.md)

This is the **0.3.1 WordPress.org submission candidate**, based on current main. WordPress.org submission and approval are pending. It supersedes the obsolete 0.2.0 submission candidate; neither the old plugin ZIP nor its external runtime kit is required.

## Download and start

1. Download **[ozeki-resilience-0.3.1.zip](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.1-rc.2/ozeki-resilience-0.3.1.zip)** and verify it against the release's `SHA256SUMS`. [Release files and matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2).
2. Read the [installation-to-recovery guide](docs/user-guide.md) and prepare [AWS access](docs/aws-setup.md).
3. Install the ZIP, configure **Tools → Resilience**, create a trusted initial Baseline, then enable protection. Installing or activating alone does not protect a site.

Use the installable ZIP, not GitHub's source archive. Runtime libraries are bundled. **No Python worker, SSH helper, external runtime kit, Docker or continuously running recovery server is required.** Standard AWS SDK credentials must be available to PHP; the guide uses an EC2 instance role. AWS charges are separate.

## Requirements and supported content

WordPress 6.4+, PHP 8.1+, ZipArchive, InnoDB and writable resource paths are required. These are declared floors, not acceptance of every environment. Prepare a versioned S3 bucket and dedicated prefix, one writing site per prefix, and appropriate IAM permissions. Recovery requires a compatible WordPress release line, recorded plugin dependencies and private writable staging outside the web root. The current controls are English.

**Markdown dependency:** Native-only Baseline and recovery do not require Markdown Documents. If active it is included; if documents or `_ozmd_source` originals remain while inactive, capture stops before saving. For Markdown recovery, install and activate the recorded compatible version first (tested 0.1.1).

<a id="supported-content-and-plugins"></a>

| Content | Supported scope |
|---|---|
| Posts and Pages | Body, recorded attributes, Trash/restore/deletion, featured images and category/tag assignments |
| Local images | Supported originals, referenced files and attachment information |
| Core comments | Creation, editing, moderation and deletion |
| Ozeki Markdown Documents | Source and supported relationships; tested 0.1.1, installed separately when needed |
| Contact Form 7 / Flamingo | Supported form definitions and received inquiries; tested 6.2.3 / 2.6.4 |
| WP-Members | Core subscriber accounts, recognized fields/settings and viewing restrictions; tested 3.5.8.1 |
| TablePress | Core tables, recognized options and references; tested 3.4.1 |

Optional plugins are installed separately. Tested Contact Form 7 6.2.3 requires PHP 8.3+. Arbitrary extensions, all metadata, external/CDN resources and every plugin version are outside this coverage. Source text is limited to 5 MiB and supported image files to 32 MiB. See [scope and setup](docs/start-here.md).

## Saving and recovery

The administrator first captures a trusted current site as a **Baseline**. Supported changes preserve originals and confirmed history in S3. A **Checkpoint** builds an independent recovery set from those saved resources; it does not discover untracked changes in the live site. Theme, runtime or other untracked settings changes can require a new trusted Baseline.

Body saves preserve originals before WordPress application. Comments and some adapter operations record changes after application, so visible changes can still be pending. Only confirmed history is recoverable after source loss. Resolve [pending saves](docs/save-resume.md); WordPress and S3 do not form one atomic transaction.

Recovery replaces supported destination state. Use a designated recovery WordPress and inspect the result. **Saved publication status, including `publish`, is restored.** Network access and DNS are the administrator's responsibility. This is not replication, malware removal, infrastructure provisioning or an unconditional recovery guarantee.

Optional schedules depend on WP-Cron execution opportunities. Retention preview does not delete; optional cleanup requires explicit configuration and deletion permissions. Preserve required versions and access. See [the user guide](docs/user-guide.md) before enabling cleanup.

## Documentation and support

- [Install and update](docs/install-update.md), including migration from the old prerelease folder
- [Recovery procedure](docs/site-snapshot.md) and [recovery FAQ](docs/recovery-faq.md)
- [Application rules and withheld information](docs/application-rules.md)
- [External-service and privacy disclosure](readme.txt)
- [Candidate checks and build instructions](docs/wordpress-org-candidate.md)

[Report an issue](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues) with the exact ZIP/hash, operation, error and runtime versions. Remove credentials and private content. Existing verification records describe their specific builds and environments; they are linked from the candidate record, not additional installation requirements.

[License](LICENSE). Ozeki Database Backup for S3 is an independent product.
