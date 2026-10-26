# User guide — from installation to recovery

[日本語](user-guide-ja.md) · [AWS setup and complete policy files](aws-setup.md)

This guide is for the [0.3.1 submission candidate](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.1). A WordPress administrator performs the daily steps; an AWS/server administrator may be needed for setup. No AWS keys are entered into the plugin. This guide uses the verified EC2-role route. Shared hosting without a usable standard SDK credential provider needs separate administrator preparation.

**Markdown dependency:** Native-only Baseline and recovery do not require Markdown Documents. If active it is included; if documents or `_ozmd_source` originals remain while inactive, capture stops before saving. For Markdown recovery, install and activate the recorded compatible version first (tested 0.1.1).

[Questions about reconstruction](recovery-faq.md) explains the five common concerns, the design measures, existing evidence and required conditions.

## 1. Understand what you will do

You first capture a trusted current site as a **Baseline**. Normal supported edits then produce independent S3 originals and confirmed history. A **Checkpoint** collects a complete supported reconstruction set from those saved resources. When needed, you prepare a separate WordPress and restore a selected point plus confirmed history. The destination does not update automatically after each source edit.

Start with a small site you control. Check the [supported content and plugins](../README.md#supported-content-and-plugins): Posts/Pages, local images, core comments, Markdown Documents, CF7/Flamingo, WP-Members core subscribers and TablePress core have defined limits. Unsupported extensions, external/CDN resources and arbitrary later settings changes are not automatically protected. Preserve other backup arrangements until you have confirmed your own supported recovery scope.

Record the source WordPress/PHP/plugin versions and the AWS settings worksheet. The declared minimum is WordPress 6.4/PHP 8.1, not proof of every combination; tested CF7 6.2.3 requires PHP 8.3+. You need InnoDB tables, ZipArchive and writable paths. Recovery needs private writable temporary storage and a compatible WordPress release line/same-or-newer maintenance patch. See [installation details](install-update.md).

## 2. Prepare AWS, then install

Use `ozeki-resilience-0.3.1.zip` and `SHA256SUMS` from the linked candidate release. The version remains 0.3.1; identify the build by tag, filename and checksum.

1. Complete [AWS setup](aws-setup.md). Begin with the **source-no-delete** policy, a versioned dedicated prefix and automatic cleanup off. Do not share one writing prefix between sites.
2. Download the installable ZIP and verify its SHA-256 against `SHA256SUMS` from the [candidate release](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.1). Do not install Source code (zip).
3. Before uploading, check that PHP `upload_max_filesize`, `post_max_size` and the web-server request limit allow the actual ZIP size recorded in its manifest plus request overhead. If too small, ask the server administrator to adjust the limits for the destination; do not change the ZIP. See [upload requirements](install-update.md). In WordPress **Plugins → Add New Plugin → Upload Plugin**, choose the ZIP, install and activate. For replacement, follow [update precautions](install-update.md); do not uninstall the product as an update method. Keep a copy of your settings and resolve pending work first where possible.
4. Open **Tools → Resilience**. The current controls are English; labels below match the product.
5. In **Storage and optional scheduling settings**, fill `bucket`, `region`, `prefix` (ending `/`) and `owner` (12-digit AWS account ID). Initially leave **Protect supported operations**, GFS **Enabled** boxes and automatic cleanup off. Set **Optional S3 deletion protection in days** to `0` only if you have chosen not to request product-level locks. Save settings.

Saving settings is not a connection test or proof of protection. Successful Baseline creation and subsequent confirmed history are the next checks. Never switch the configured prefix to another site's data to resolve an error.

## 3. Create the first Baseline

1. Make sure the source is trustworthy, pause editing and resolve pending history. For this candidate, native-only sites do not need Markdown Documents. If it is active, it is included; if documents or `_ozmd_source` originals remain while inactive, activate it before capture. Do not delete originals to bypass this check. Version 0.1.1 was tested. Activate other supported plugins only as needed.
2. Under **Site-wide recovery — primary workflow**, check **I trust the whole current site and have paused editing.** Select **Create complete initial snapshot**. This reads the supported live data/files; do not do it on a suspected compromised site merely to silence an error.
3. Wait for the result. Success means a confirmed point is listed and the initial-snapshot result reports success, not merely that the request was submitted. The resource set is saved and fixed-version verified before manifest confirmation. A failure or missing result is not success; record its reason and stop to investigate.
4. Enable **Protect supported operations (one writer per prefix)** and save settings. Resume normal editing.

The Baseline is independently recoverable. Creating another initial snapshot is a new trust decision. **Create complete Checkpoint** instead uses an existing point and subsequent confirmed S3 history; it does not recapture unrecorded live changes. See [the three principles](site-snapshot.md#baseline-and-checkpoint-operations).

## 4. Everyday editing and failed saves

Use the normal WordPress or supported plugin editor. After a representative save, check **Save protection status**: protection enabled is a setting, while the latest confirmed sequence and pending/error information describe actual saved operations. One user edit can create separate body and related-information records; confirmation of one is not confirmation of every related operation.

Supported body saves put originals in S3 before WordPress application. Comments and some adapter/detail operations capture completed operation data, so a visible change can still be pending. Current newly saved resources are fixed-version retrieved and checked before their history is confirmed. The status screen is not a fresh audit of every older original.

| What you see | What to do | Finished when |
|---|---|---|
| Original save failed before a pending record exists | Resolve the reported storage/permission issue and save again in the normal editor; Resume history cannot recover a request that was never queued | The intended content is saved and its history confirmed |
| Pending operation / history save failed | Investigate the reason; when storage is usable, use **Resume history** | Pending records clear and the intended formal records confirm |
| Source lost before confirmation | Restore only the confirmed boundary | Do not count the last unconfirmed change as recoverable |
| Unknown/error result | Preserve the message and inspect it; do not assume success or repeatedly click | Cause is understood before retry |

[Detailed pending-save procedure](save-resume.md). Changes to themes, menus, runtime plugins or other captured information outside supported history may require a **new trusted Baseline** after editing is paused. Normal Checkpoint does not discover these changes; [the existing operations table](start-here.md#3-changes-requiring-administrator-attention) explains the distinction.

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
