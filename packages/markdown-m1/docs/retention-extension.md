# Fixed-version retention checks and manual renewal

> Historical development note: the lifecycle design below was superseded by [GFS Checkpoints](gfs-checkpoints.md). Current `retention_days` is independent of `cleanup_keep_days`; the normal screen no longer offers manual renewal. Its backend remains, but it is not the scheduled lifecycle. The earlier fixture evidence below is not evidence of the current GFS screen or real AWS extension. Real AWS retention inspection subsequently encountered missing `s3:GetObjectRetention` permission. See the GFS document for current behavior and test boundaries.

Development change after PR #46; not included in any published ZIP or the checkpoint-verification candidate. Storage payload schemas are unchanged.

When `retention_days` is positive, confirmation requires protection through the greater of `retention_days` and `cleanup_keep_days`, measured from the start of the confirmation attempt, plus a five-minute processing allowance. Before writing the confirmation object the remaining window must still cover the configured days; an overlong attempt stops. A delayed history resume calculates a fresh deadline rather than treating the original's historical `retain_until` field as the current S3 protection state.

The common fixed-version check reads Object Lock retention. If insufficient, it extends the exact version, keeps its existing GOVERNANCE/COMPLIANCE mode, and reads retention again. Sufficient deadlines are never shortened. No Governance bypass, Legal Hold change, deletion or rollback is used. Read denial, extension failure, invalid retention metadata and an ineffective extension stop the operation. Partial extensions remain; a manual retry rechecks them.

Applied to:

- Formal-history confirmation: original, metadata, split data, referenced media, and references inside reassembled structured adapter originals are checked before the history PUT.
- Initial site snapshots and site-wide Checkpoints: every saved resource is content-checked and retention-checked before manifest PUT.
- Reused immutable keys: identical bytes alone no longer satisfy a write retry when retention is enabled; the returned fixed version must meet its requested deadline.
- Manual **Renew Checkpoint protection**: selects the greatest complete-site history boundary (key order breaks equal-boundary ties), validates that baseline and the captured contiguous tail, and renews their referenced fixed versions and confirmation objects. It writes no new Checkpoint, original or history. Pending article/shared operations block this action. Success/failure/running state is recorded separately from snapshot creation and recovery results.

New history/manifest PUTs request the required retention and rely on the successful S3 write acknowledgement; when a failed/lost PUT response resolves to an existing identical version, that version's retention is checked before reporting success. This is not an atomic transaction spanning several S3 objects. A previously confirmed object is not erased if a later renewal fails.

`retention_days = 0` preserves the existing explicit no-product-retention mode: ordinary content verification still runs, but no deletion-protection claim is made. Manual renewal refuses that configuration. A bucket default alone is not used to infer a product guarantee. The legacy asset-only snapshot workflow is not upgraded into the complete-site renewal workflow.

## Operational boundary

The role needs fixed-version reads plus `s3:GetObjectRetention` and `s3:PutObjectRetention` for the designated resources. The bucket must support the requested Object Lock operations. These changes do not modify IAM or bucket policy. Retention errors must not be hidden by falling back to copies or removing protection.

Keeping the final Checkpoint out of deletion candidates does not renew Object Lock indefinitely. The manual action renews protection to the displayed deadline only, including subsequent history captured by that request. Scheduled renewal, full-site deletion, concurrent external writers, bucket Lifecycle changes and outage survival beyond the deadline are not implemented here. The existing one-writer-per-prefix requirement remains.

## Differential evidence

Local PHP and the existing dm isolated WordPress used memory-only S3 fixtures: no real S3 read/write/retention calls or credentials. Cases cover new/reused/delayed confirmation, insufficient expiry, denied reads/extensions, ineffective extension, fixed-version/mode preservation, nested adapter references, latest Checkpoint plus tail, and no original byte/reference mutation. Failure prevents new history/manifest confirmation. The actual WordPress method and page renderer record failure/success and show the manual action; pending operations replace a prior success with failure. Existing isolated content/member tables remain equal and temporary options are restored.

This is not real AWS permission/extension acceptance or browser interaction. Existing S3 objects, IAM and published/candidate ZIPs are untouched. No full recovery, automatic renewal or deletion test was added. Local evidence is in `release-readiness/retention-extension-20261025/`.

## 日本語

保持を有効にした場合、既存の削除保護日数と復旧点保存日数の長い方を必要期間とし、処理用の5分の余裕を付けます。固定版の期限を読み、不足分だけ延長し、再取得した保持情報で確認します。遅延確定でも必要期限を計算し直します。読み取り不能・延長失敗・延長後も不足の場合は確定を停止します。既に延長できた期限を戻したり原本を削除したりしません。

管理画面の手動保持更新は、最新のサイト全体Checkpointと取得時点の後続正式履歴を対象とします。新しいCheckpoint作成や自動継続ではありません。保持0は従来の無効設定として残し、手動保持更新では拒否します。旧資産単位のスナップショット経路は今回の対象外です。

検証は既存dm隔離WordPressとメモリストレージで行いました。実AWSへの保持延長、IAMの適合性、ブラウザ操作は未確認です。既存S3資産・IAM・公開済みZIP・前回候補ZIPは変更していません。
