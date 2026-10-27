# First-time setup — from preparation to protection

[日本語](user-guide-ja.md) · [Updating an existing installation](install-update.md) · [Recovery](#6-recover-onto-a-separate-wordpress)

This product preserves originals and confirmed history in S3 to reconstruct supported WordPress state when needed. Follow **prepare → configure storage → create a Baseline → confirm protection**. Scheduling, retention and recovery can follow the initial check.

## 1. Check your environment

Posts/Pages, supported images and core comments are the basic scope. Check the [coverage table](../README.md#supported-content-and-plugins) for integrations. Native-only sites do not need Markdown Documents.

| Who | What to prepare |
|---|---|
| WordPress administrator | Administrator login, supported content/plugins, and a pause in editing for the initial capture |
| AWS administrator | Versioned S3 bucket, dedicated site prefix and source permissions; provide bucket, region, prefix and the owner's 12-digit account ID |
| Server administrator | WordPress 6.4+, PHP 8.1+, InnoDB, ZipArchive, writable paths, standard AWS SDK credentials usable by web PHP, and upload limits allowing the approximately 7.5 MB ZIP |

The [AWS instructions](aws-setup.md) use an EC2 role. For other hosting, ask whether standard credentials can be provided to web PHP. This plugin has no access-key input field. Integration requirements also apply (tested CF7 6.2.3 needs PHP 8.3+).

## 2. Prepare AWS, then install

1. Complete [AWS setup](aws-setup.md). Start with the `source-no-delete` policy and cleanup disabled.
2. Download **ozeki-resilience-0.3.1.zip** from the [rc.2 release](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2). `Source code (zip)` is not installable. `SHA256SUMS` is available there for verification.
3. In WordPress, use **Plugins → Add New Plugin → Upload Plugin**, install the ZIP and activate it. If an older version is installed, follow [update instructions](install-update.md).
4. Open **Tools → Resilience**, then scroll down to **Storage and optional scheduling settings**. The status and recovery controls above are used after storage setup. If the unconfigured screen reports an S3 history read error, first configure the following fields.
5. Enter these four values.

| Field | Value |
|---|---|
| bucket | Bucket name, without `s3://` |
| region | Bucket region, for example `ap-northeast-1` |
| prefix | Dedicated site prefix, for example `sites/my-site/`, including the trailing `/` |
| owner | Bucket owner's 12-digit AWS account ID |

6. Leave **Protect supported operations**, GFS **Enabled** boxes and automatic cleanup off. If your setup does not request product-level deletion locks, set **Optional S3 deletion protection in days** to `0`. Click **Save settings**.

Next, verify actual storage access by creating a Baseline.

## 3. Create the first Baseline

1. Confirm that the source is trustworthy and pause editing. If Markdown documents are used, activate the compatible Markdown Documents plugin first.
2. Under **Site-wide recovery — primary workflow**, check **I trust the whole current site and have paused editing.** Click **Create complete initial snapshot**.
3. Confirm success and that the new Baseline appears in the recovery-point list. For an error, record its message and use [troubleshooting](#troubleshooting) below.
4. Scroll down, enable **Protect supported operations (one writer per prefix)** and click **Save settings**. Resume editing.

A Baseline initially captures current supported state. Later Checkpoints use saved resources and confirmed history. For untracked changes such as themes, consult the [changes table](start-here.md).

## 4. Confirm protection

Save one identifiable test post through the normal WordPress editor. Open **Tools → Resilience → Save protection status**.

- **Protection setting: Enabled** is shown.
- **Last confirmed sequence**, title and time identify the confirmed history for the post you saved.
- **Locally pending operations: 0** is shown, with no outstanding error from that save.

These checks complete initial setup and a representative post-save check, not validation of every integration or all site content. Body and related operations can confirm separately, so also check the pending count. Keep existing backups until you have confirmed recovery for your own site's scope.

### Troubleshooting

| Situation | Next step |
|---|---|
| ZIP upload fails | Ask the server administrator to check PHP upload/POST and web-server request limits |
| Authentication error / AccessDenied after setup | Check the [AWS worksheet](aws-setup.md), web PHP credentials and prefix permissions with the administrator |
| Pending operations remain | Resolve the cause, then use **Resume history**; see [save resumption](save-resume.md) |
| Unclear error | Record the operation and error for support; omit credentials and private content |

Only confirmed history is available after source loss. If an original save failed before being queued, resolve the cause and save again through the normal editor.

## 5. Checkpoint schedules and retention

In Tools → Resilience, check the displayed timezone. For example, enable weekly Sunday 02:00 / keep 2 weeks, monthly day 1 at 02:00 / keep 3 months, yearly January 1 at 02:00 / keep 1 year. These are examples, not mandatory or capacity-tested defaults. Coincident dates **and times** produce one set with all labels. A still-active label preserves the whole point. Unchanged content is copied into every new independent point. Stagger sites on a shared server.

**Detailed history recovery window in days** controls how far detailed history is kept with its boundary point; `0` retains the latest Checkpoint and necessary tail, not zero resources. Historical GFS points can remain without all intervening history. **Optional S3 deletion protection** is a separate AWS lock request; `0` does not remove existing locks. [GFS details](gfs-checkpoints.md).

After saving, check **Next complete-site Checkpoint (UTC)**. Arrange a regular execution opportunity with your server administrator; WP-Cron is not an exact-time timer. After a run inspect the actual success/failure and next reservation. On failed capture, cleanup is skipped; an older successful cleanup result may still be shown with its old timestamp.

Start with **Preview complete-site retention**, which does not delete. Review retained points, required resources, candidates and blocked reasons. Enable deletion only after your recovery check and the [cleanup policy change](aws-setup.md#4-choose-and-install-one-complete-policy). With that permission, the confirmation checkbox and **Delete expired complete-site resources** execute the reviewed plan. Automatic cleanup is a separate checkbox and runs only after successful scheduled capture. This is not arbitrary deletion of retained points or a reset button. Do not create an S3 Lifecycle age-expiry rule for the product prefix as a substitute.

## 6. Recover onto a separate WordPress

1. Prepare a clean, dedicated destination with compatible WordPress, product ZIP, required plugins and a working administrator login. If WP-Members requires activation, activate the destination administrator separately; source administrator credentials are not restored. Do not use a live unrelated site as the destination.
2. Apply the **recovery-read-only** policy to its AWS identity. Enter the same bucket/region/prefix/owner in Resilience. Leave protection, schedules and cleanup **off**; do not create a Baseline on the destination. Keep unresolved local pending work out of the recovery environment.
3. Under **Site-wide recovery — primary workflow**, select the desired **Checkpoint** (Baseline is also selectable) and **Formal history end**. The end is inclusive: selecting the point's own `through` restores that point alone; a later end needs all necessary subsequent confirmed records/resources. It is not necessarily a complete editing-session boundary.
4. Confirm replacement and use **Restore complete site**. It replaces destination content. A local rollback copy is not a promise of automatic rollback. Keep source S3 resources intact.
5. Check success/failure, used Checkpoint, requested/applied history boundary and counts; keep detailed JSON if investigating. A failed run is failed: stop, identify the reason, prepare the destination appropriately and decide whether to rerun. Do not assume it was unchanged.
6. Re-login and inspect representative body, image, links and relevant member/table/form behaviour. Saved `publish` state is reproduced. DNS/network exposure is a separate administrator decision. Mail replay is not a recovery function.

[Detailed recovery](site-snapshot.md) · [Application rules and withheld information](application-rules.md)

## 7. Known boundaries and help

This is not malware certification or an unconditional recovery guarantee. An AWS AccessDenied, unavailable credentials, missing PHP extension, unwritable temporary path or incompatible runtime is an environment condition to diagnose, not permission to weaken the product's confirmation rules. For help, provide version/tag, operation, error, confirmed boundary and relevant runtime versions; redact credentials, tokens, personal data and private originals.

[Known operational limits](remaining-confirmations.md) and [candidate checks](wordpress-org-candidate.md) distinguish existing evidence from the packaging checks for this ZIP. The later [readiness record](recovery-readiness.md) includes the sample-only IAM acceptance; it supersedes earlier notes that those templates were unverified.
