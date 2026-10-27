# Preparation for protection (0.3.2-dev)

[日本語](setup-readiness-ja.md) · [Setup and recovery guide](user-guide.md) · [Terms of use](terms-of-use.md)

This screen is in the GitHub development version. It is **not included in the submitted 0.3.1 rc.2 ZIP**. The submitted ZIP is unchanged.

## Start protection for the first time

1. Open **Tools → Resilience** and inspect **Preparation for protection** at the top. Each **Action needed** row names the missing condition, the person responsible and the next action.
2. Choose **Protect this site** in storage settings. Enter bucket, region, prefix and owner using the [setup guide](user-guide.md#2-prepare-aws-then-install). Leave protection, schedules and automatic cleanup off.
3. Read the terms and saved content, select the storage-access confirmation checkbox and click **Save settings**. The checkbox starts unchecked. A fresh installation makes no S3 connection before these settings are saved. After saving, existing history displays also read S3.
4. Click **Check storage**. This checks connection and bucket versioning using reads only. It does not write/delete data or change bucket settings. The [published AWS policies](aws-setup.md) include the necessary `s3:GetBucketVersioning` and `s3:ListBucket` for the dedicated prefix.
5. Resolve environment issues, pause editing and save the trusted current site as the first Baseline. Use **Site-wide recovery → I trust the whole current site and have paused editing → Create complete initial snapshot**. **First save and verified read-back** becomes confirmed. A successful connection alone does not complete this item.
6. Enable **Protect supported operations**, select the terms confirmation and save settings. The confirmation starts unchecked each time so you can review changes. Starting protection requires a completed initial save for this storage destination.
7. Complete the [post-save check](user-guide.md#4-confirm-protection). Enabled protection describes the setting; **Save protection status** confirms the post's actual save.

States are **Confirmed**, **Action needed**, **Not checked** and **Not used**. Results for another storage destination are not reused after a change. Initial capture and starting protection also check the necessary conditions. Consult the [coverage table](../README.md#supported-content-and-plugins) for the integrations you use. Active supported integrations are included by the existing initial capture; this screen does not automatically diagnose every integration.

## Recover another site

Choose **Recover another site**, keep protection off and save settings. Check storage, then select an existing Checkpoint under **Site-wide recovery** and follow the [recovery procedure](user-guide.md#6-recover-onto-a-separate-wordpress). The destination does not prompt for a new initial save. Checking storage needs no S3 write permission.

## Existing installations

Existing storage settings and protection continue operating. The new display does not reclassify older initial saves: **Not checked** does not mean existing data was lost. Confirm the terms when next saving settings. If you disable protection and later restart it, create an initial save in this version first, from a trusted source.

The checkbox confirms understanding of saving and recovery; it is not an additional contract restricting GPL rights. The terms version, confirmation time and administrator ID are recorded locally in WordPress.
