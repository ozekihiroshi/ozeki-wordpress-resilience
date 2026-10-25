# Start here: package, protection scope and recovery

English | [日本語](start-here-ja.md)

Status: publication preparation, not a release announcement. This guide is included in the documentation-corrected preparation ZIP. Product code is identical to the validated save-verification-final candidate. Prioritize the integrity of irreplaceable recovery resources; keep failure handling for rerunnable recovery simple.

## 1. Identify the package

The prepared package is **0.3.1 prerelease-prepared**, for labelled GitHub Pre-release distribution.

- Filename: `ozeki-wordpress-resilience-0.3.1-prerelease-prepared.zip`
- [Package](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/v0.3.1-pre.1/release-candidates/20261025-prerelease/ozeki-wordpress-resilience-0.3.1-prerelease-prepared.zip) · [SHA-256 and verification record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/v0.3.1-pre.1/docs/releases/prerelease-package-m1-031.md)

Only documentation differs from save-verification-final. All other archive entries, including product code and dependencies, are byte-identical. New install/update runtime evidence belongs to that earlier candidate; this repackaging checks archive contents and links, not a new live installation. Identify by full filename and external SHA-256, not 0.3.1 alone. Older candidates remain evidence. Do not install GitHub source archives or the old 0.2.0 research distribution.

This package is for GitHub Pre-release `v0.3.1-pre.1`, not WordPress.org submission or a stable release. Plugin version remains 0.3.1 because code is unchanged. A new isolated WordPress trial verifies actual S3 original PUTs, fixed-version GETs and formal-history PUT with standard EC2-role credentials; all three newly stored resources were read before history confirmation. This is a normal WordPress API save, not browser or all-adapter acceptance. Earlier injected-failure tests remain separate.

## 2. What is protected

The product reconstructs the **supported site state** from a trusted initial snapshot or complete Checkpoint plus confirmed S3 history. “Complete site” does not mean every WordPress extension or all subsequent settings changes.

Normal supported operations cover Posts/Pages, referenced local images, core comments, Ozeki Markdown Documents, Contact Form 7, Flamingo, WP-Members core subscribers and TablePress core. Read the exact inclusions, exclusions and tested versions in the [support table](../README.md#supported-content-and-plugins). Install optional plugins only for content that needs them.

The administrator judges the initial site trustworthy. Later complete Checkpoints are built from S3's baseline and confirmed history; they do not import untracked live-site changes. Unconfirmed operations are excluded. Saved publish status is reproduced; server/network exposure and DNS are administrator responsibilities. This is not replication, malware certification or infrastructure provisioning.

## 3. Changes requiring administrator attention

| Change | What to do |
|---|---|
| Supported article/image/comment/adapter operation | Use its normal editor. Check formal-history confirmation; resolve reported pending saves when the source survives. |
| Theme/parent-theme files or selection; menus, templates, navigation, global styles; captured presentation settings | Pause editing and create a **new trusted complete initial snapshot** after the change. A regular S3-derived Checkpoint cannot capture it. |
| Runtime plugin update or captured plugin settings outside adapter history; global taxonomy administration; live-file changes outside recorded uploads | Determine whether initial capture includes that resource, then create a new trusted initial snapshot if it does. A tested earlier version does not certify an updated plugin. |
| Uncaptured plugin tables/settings, external/CDN files, external services or secrets | A new snapshot does not automatically add support. Keep an independent preservation/setup procedure or exclude this resource from the promised recovery scope. |

Do not replace trusted pre-incident recovery points with a new capture of a suspected compromised source. A new baseline requires the administrator's trust decision. Keep earlier recovery resources according to the retention plan; this guide does not authorize deletion. The current UI does not automatically detect every untracked change or prompt for a new baseline.

## 4. Minimum setup: source and destination

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

## 5. Operational route

1. Follow [installation/update](install-update.md); use the exact package and hash above.
2. In Tools → Resilience configure source bucket, region, prefix and applicable retention. Resolve pending history, pause editing, acknowledge trust and create a complete initial snapshot. Enable protection for normal supported operations.
3. Monitor confirmed versus pending history. Create complete Checkpoints manually as needed. Periodic execution and actual complete-site deletion remain deferred.
4. If recovery is needed, prepare the dedicated destination, administrator login (including WP-Members activation where applicable), dependencies and read-only S3 access. Leave destination protection off.
5. Select the complete Checkpoint and inclusive confirmed-history end in Tools → Resilience. Confirm destination replacement. One formal record need not represent an entire user edit.
6. Inspect the result and restored behavior. On failure stop, investigate the reported cause and decide separately whether to retry. There is no automatic continuation. Internet exposure is a separate administrator decision.

[Detailed site recovery](site-snapshot.md) · [Pending-save handling](save-resume.md) · [Current package acceptance](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/v0.3.1-pre.1/docs/releases/recovery-errors-final-m1-031.md)

Existing browser recovery, earlier browser ZIP upload and current ZIP extraction-update are separate evidence. The new documentation itself has link/content review only; no repeat recovery or new version-migration acceptance is implied. Historical research documents are reference material, not installation prerequisites: [archive](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/v0.3.1-pre.1/docs/archive/readme-before-product-consolidation-20261024/root-en.md).
