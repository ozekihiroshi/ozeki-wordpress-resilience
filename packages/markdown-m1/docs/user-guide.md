# First-time setup — from preparation to protection

[日本語](user-guide-ja.md) · [Updating an existing installation](install-update.md) · [Recovery](#6-recover-onto-a-separate-wordpress)

Prepare to preserve articles, images, comments and supported inquiry and member information, so you can resume publishing and serving users if an attack makes the original site unusable. Read [what is protected and how its role differs from backups](../README.md#keep-a-path-to-recovery-after-an-attack). Follow **prepare → configure storage → create a Baseline → confirm protection**. Scheduling, retention and recovery can follow the initial check.

## 1. Check your environment

Start by identifying what you need to resume service: Posts, Pages, images and comments, plus integrations such as inquiries, membership and tables. The [README](../README.md#what-remains-and-what-you-can-recover) lists what is saved and restored, and explains exclusions. Check the [coverage table](../README.md#supported-content-and-plugins) for integrations. Native-only sites do not need Markdown Documents.

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
3. In the **Checkpoint** selector, find `administrator_initial` with the time of this capture. This is your first Baseline (`history 0` for a new prefix). For an error, record its message and use [troubleshooting](#troubleshooting) below.
4. Scroll down, enable **Protect supported operations (one writer per prefix)** and click **Save settings**. Resume editing.

A Baseline initially captures current supported state. Later Checkpoints use saved resources and confirmed history. For untracked changes such as themes, consult the [changes table](start-here.md).

## 4. Confirm protection

Create a test post with an identifiable title and content suitable for public viewing in the normal WordPress editor, then **Publish** it. Saving a new draft alone does not start tracking. Open **Tools → Resilience → Save protection status**.

- **Protection setting: Enabled** is shown.
- **Last confirmed sequence** and the confirmation time have updated, and the **Confirmed formal history / Individual recovery** table farther down lists your post title and its related information. The latest **Title** may be something like `Article details #7` rather than the post title. Only inspect the table; do not click a recovery button.
- **Locally pending operations: 0** is shown, with no outstanding error from that save.

These checks complete initial setup and the post-save check. Next, check the inquiry, membership or other integrations your site uses. Continue backing up assets outside this product’s scope.

### Troubleshooting

| Situation | Next step |
|---|---|
| ZIP upload fails | Ask the server administrator to check PHP upload/POST limits, web-server request limits and write permissions for the uploads directory |
| Authentication error / AccessDenied after setup | Check the [AWS worksheet](aws-setup.md), web PHP credentials and prefix permissions with the administrator |
| Pending operations remain | Resolve the cause, then use **Resume history**; see [save resumption](save-resume.md) |
| Unclear error | Record the operation and error for support; omit credentials and private content |

Only confirmed history is available after source loss. If an original save failed before being queued, resolve the cause and save again through the normal editor.

## 5. Checkpoint schedules and retention

In Tools → Resilience, check the displayed timezone. For example, enable weekly Sunday 02:00 / keep 2 weeks, monthly day 1 at 02:00 / keep 3 months, yearly January 1 at 02:00 / keep 1 year. Choose settings to suit the period you want to preserve and your storage usage. Coincident dates **and times** produce one set with all labels. A still-active label preserves the whole point. Unchanged content is copied into every new independent point. Stagger sites on a shared server.

**Detailed history recovery window in days** controls how far detailed history is kept with its boundary point; `0` retains the latest Checkpoint and necessary tail, not zero resources. Historical GFS points can remain without all intervening history. **Optional S3 deletion protection** is a separate AWS lock request; `0` does not remove existing locks. [GFS details](gfs-checkpoints.md).

After saving, check **Next complete-site Checkpoint (UTC)**. Arrange a regular execution opportunity with your server administrator; WP-Cron is not an exact-time timer. After a run inspect the actual success/failure and next reservation. On failed capture, cleanup is skipped; an older successful cleanup result may still be shown with its old timestamp.

Start with **Preview complete-site retention**, which does not delete. Review retained points, required resources, candidates and blocked reasons. Enable deletion only after your recovery check and the [cleanup policy change](aws-setup.md#4-choose-and-install-one-complete-policy). With that permission, the confirmation checkbox and **Delete expired complete-site resources** execute the reviewed plan. Automatic cleanup is a separate checkbox and runs only after successful scheduled capture. This is not arbitrary deletion of retained points or a reset button. Do not create an S3 Lifecycle age-expiry rule for the product prefix as a substitute.

## 6. Recover onto a separate WordPress

Restore saved articles, images, inquiries and other supported content on a separate WordPress to resume publishing and serving users. Recovery uses what remains in S3 even when the original site is offline. After an attack, choose a trusted initial capture (Baseline) and the changes to restore. Prepare administrator access and external service connections on the destination, and check it with public access restricted before reopening.

1. Prepare a clean, dedicated destination with the same WordPress release line as the capture, at the same or a newer maintenance patch (for example, 7.1.2 to 7.1.3), the product ZIP, required plugins and a working administrator login. If WP-Members requires activation, activate the destination administrator separately; source administrator credentials are not restored. Do not use a live unrelated site as the destination.
2. Apply the **recovery-read-only** policy to its AWS identity. Enter the same bucket/region/prefix/owner under **Storage and optional scheduling settings** and click **Save settings**. Leave protection, schedules and cleanup **off**; do not create a Baseline on the destination. Keep unresolved local pending work out of the recovery environment.
3. Under **Site-wide recovery — primary workflow**, use the **Checkpoint** selector below **Create complete Checkpoint**, next to **Formal history end**, to choose the Baseline (`administrator_initial`) or a Checkpoint and **Formal history end**. The end is inclusive: selecting the point's own `through` restores that point alone; a later end needs all necessary subsequent confirmed records/resources. It is not necessarily a complete editing-session boundary. For example, if body history is 1 and related information is 2, select through 2 to adopt both.
4. Confirm replacement and use **Restore complete site**. It replaces destination content. Keep source S3 resources intact.
5. Under **Last site-wide recovery result**, check success/failure, the used Checkpoint and requested/applied history boundary. Review **Preserved in S3 — not automatically applied** too. Post counts include revisions and other post types; zero files written can mean identical existing files were reused. Also keep detailed JSON if investigating. If an error occurs, inspect the message and destination state, resolve the cause, then rerun.
6. Re-login with the administrator prepared on the destination and inspect representative body, author display, images, links and relevant member/table/form behaviour. The site name may change to the source name; keep checking the destination URL. Saved `publish` state is reproduced. DNS/network exposure is a separate administrator decision. Mail replay is not a recovery function.

[Detailed recovery](site-snapshot.md) · [Application rules and withheld information](application-rules.md)

## 7. Help

See the [README](../README.md#what-remains-and-what-you-can-recover) for saved and restored content, and [troubleshooting](#troubleshooting) for setup errors. For help, provide version/tag, operation, error, confirmed boundary and relevant runtime versions; redact credentials, tokens, personal data and private originals.

[Known operational limits](remaining-confirmations.md) and [candidate checks](wordpress-org-candidate.md) distinguish existing evidence from the packaging checks for this ZIP. The later [readiness record](recovery-readiness.md) includes the sample-only IAM acceptance; it supersedes earlier notes that those templates were unverified.
