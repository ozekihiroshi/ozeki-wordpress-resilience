# Coverage and operations after changes

Install WordPress, themes and required plugins separately from trusted distributors before recovery, and activate the required plugins. Resilience restores information assets and their supported relationships; it does not install or activate software from S3. It keeps the destination theme selection. Unknown settings are reported without being applied.

For first-time setup, follow the [user guide](user-guide.md). This reference explains supported scope and what to do after theme or configuration changes.

This reference covers the current 0.3.3 series. Before installation, check [distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md); WordPress.org approval is pending.

## 1. What is protected

The product reconstructs the **supported site state** from a trusted initial snapshot or complete Checkpoint plus confirmed S3 history. “Complete site” does not mean every WordPress extension or all subsequent settings changes.

Normal supported operations cover Posts/Pages, referenced local images, core comments, Ozeki Markdown Documents, Contact Form 7, Flamingo, WP-Members core subscribers and TablePress core. Read the exact inclusions, exclusions and tested versions in the [support table](../README.md#supported-content-and-plugins). Native-only Baselines do not require Markdown Documents; activate it if Markdown documents or originals are present; see the [Baseline prerequisites](user-guide.md#3-create-the-first-baseline). Install other optional plugins only for content that needs them.

The administrator judges the initial site trustworthy. Later complete Checkpoints are built from S3's baseline and confirmed history; they do not import untracked live-site changes. Unconfirmed operations are excluded. Saved publish status is reproduced; server/network exposure and DNS are administrator responsibilities. Use [the stated verification boundaries](../README.md#what-the-product-checks) to choose the Baseline and history, then inspect the recovery result before returning to service.

Baseline is the first independent complete recovery point. A normal Checkpoint uses only S3 assets and confirmed history; current WordPress recapture is a separate new Baseline. See [operations and dependencies](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md). The legacy Markdown asset-level path is separate.

## 2. Changes requiring administrator attention

The next candidate's source adds daily tracking for completed publication/comment/deletion operations, author changes, classic menu content, and the explicitly listed core settings. These changes are not included in the submitted rc.21 ZIP. Until the new candidate is distributed, follow the guidance for the ZIP you installed. For new Markdown setups, use Markdown Documents 0.1.3 on the source and the same recorded version on the prepared destination; see [update order](install-update.md).

| Change | What to do |
|---|---|
| Supported article/image/comment/adapter operation | Use its normal editor. Check formal-history confirmation; resolve reported pending saves when the source survives. |
| Classic menu content, categories/tags, and core settings listed in the next candidate's update contract | In that candidate, check formal-history confirmation. This does not include arbitrary theme settings or block-navigation layouts. |
| Software names/versions; templates, theme selection, block-navigation layouts and settings outside daily tracking | Pause editing and create a **new trusted complete initial snapshot** when the change is within initial-capture scope. Prepare destination software/settings separately; a snapshot does not make them automatically applicable. |
| Captured plugin settings outside adapter history; live-file changes outside recorded uploads | Determine whether initial capture includes that resource, then create a new trusted initial snapshot if it does. A tested earlier version does not certify an updated plugin. |
| Uncaptured plugin tables/settings, external/CDN files, external services or secrets | A new snapshot does not automatically add support. Keep an independent preservation/setup procedure or exclude this resource from the promised recovery scope. |

Do not replace trusted pre-incident recovery points with a new capture of a suspected compromised source. A new baseline requires the administrator's trust decision. Keep earlier recovery resources according to the retention plan; this guide does not authorize deletion. The current UI does not automatically detect every untracked change or prompt for a new baseline.

## 3. Minimum setup: source and destination

| Requirement | Saving WordPress | Recovery WordPress |
|---|---|---|
| Host | Existing operating site | Newly prepared dedicated WordPress with a different URL; need not run permanently |
| Software | Product ZIP and plugins needed for the protected content | Product ZIP, compatible WordPress release line and recorded dependencies required by the recovery checks |
| Runtime | InnoDB managed tables, ZipArchive, writable resource paths; PHP compatible with the chosen plugins | Same requirements plus private writable staging outside the web root |
| AWS authentication | Standard AWS SDK provider chain; EC2 role where available | Standard SDK authentication; read-only role/access is sufficient for recovery |
| S3 scope | Versioned bucket and dedicated prefix ending in `/`; one writing installation per prefix | Same bucket/region/prefix; protection disabled, no unresolved local pending saves |
| Permissions | Prefix-scoped ListBucket, GetObject, GetObjectVersion, PutObject; PutObjectRetention only when configured retention requires it | Prefix-scoped ListBucket, GetObject, GetObjectVersion; no write/delete needed for recovery |

The product declares WP6.4+/PHP8.1+, but this is not acceptance of every combination. Tested CF7 6.2.3 needs PHP8.3+. Use the [README's tested dependencies](../README.md). Recovery enforces the recorded WordPress release line and same/newer maintenance patch; record dependency versions before source loss. IAM/bucket/KMS conditions may impose additional requirements; no universal IAM policy is implied. Object Lock retention needs a correctly configured bucket and permissions. Ordinary saving/recovery does not require retention bypass or deletion rights. Version-list rights for retention preview are separate from recovery access.

No permanent second EC2, Python worker, SSH credential helper, shared bridge or Docker dependency. Docker is an optional way to prepare the destination. Administrator credentials and AWS/mail transport settings are configured independently, not recovered from source credentials.
