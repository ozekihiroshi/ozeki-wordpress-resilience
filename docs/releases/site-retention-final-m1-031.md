# Complete-site retention preview — final 0.3.1 ZIP acceptance

Date: 2026-10-25. Candidate: [ozeki-wordpress-resilience-0.3.1-site-retention-final.zip](../../release-candidates/20261025-site-retention/ozeki-wordpress-resilience-0.3.1-site-retention-final.zip).

SHA-256: `6d56adf7d62e670b1fc4e2a9df98ed9436efc4731789bdeb8743860ecc0dbbb2`.
Size: 7,395,782 bytes; 3,814 files. Vendor files are identical to editor-save-final. Product files and packaged documentation match build inputs. Earlier ZIPs are preserved.

## Product scope

Read-only complete-site retention preview lists retained Checkpoints/assets, potential deletion candidates and blocking reasons. It uses fixed-version S3 LastModified and the configured recovery-point retention period, always retaining the greatest confirmed-history boundary and required later history. Nested media references are included. Both article and shared pending queues stop calculation. Unknown assets remain protected; legacy snapshots mixed into the stream, ambiguous versions, missing references and history gaps require review. Legacy deletion refuses a stream containing complete-site snapshots. This is not an actual deletion feature or delete-permission certification.

The existing community isolated browser test displayed five retained Checkpoints and 311 assets under the 90-day policy, with history through70. The role lacks ListBucketVersions. Current fixed versions can still be read and displayed, but hidden older versions remain unassessed and no candidates are certified. IAM was unchanged. Positive candidate, Object Lock/Legal Hold, unknown-resource, history-gap, pending-queue and denied-version-list behavior is covered by in-memory contracts, not by deleting or aging real S3 assets. Large synchronous inventories may reach host request limits.

## Exact ZIP installation and update

Reused the existing dm Docker/core/database services and installed into separate test content/table namespaces. Fresh installation used this ZIP; update installed the previous editor-save-final ZIP, seeded isolated fixtures, then extracted this ZIP over it. This is ZIP extraction/activation acceptance, not a new browser Upload/Replace test.

Both paths passed:

- All 3,814 installed files equal ZIP entries.
- Configuration, stable article identity, content, comments, CF7/Flamingo records, WP-Members credentials/settings and TablePress IDs/cells/settings preserved.
- Four synthetic shared pending records and their error preserved. These preservation fixtures were not resumed or sent to S3.
- Individual and complete-site recovery results and last-attempt state preserved.
- Real S3 history70 unchanged: SHA-256 `cc3bac5abe027b212876ee8b24c44955d25e94dd91c726402987671e32b4ba56`.
- New retention UI present; preview stops on the pending queue without changing it.
- No Checkpoint schedule enabled, no mail calls in verification/fixture seeding, and existing live-site probe matches before/after.

## Classification and limits

**Product:** the read-only preview and legacy-path guard are included. Complete-site deletion and scheduling acceptance remain out of scope. No new dependency was introduced.

**Environment:** the source role's missing `s3:ListBucketVersions` is not a product defect. Full-version evaluation needs that permission within the designated scope; retention/hold reads are also needed to evaluate eligible versions. No permission changes were made. The existing dm live probe emits a duplicate DISABLE_WP_CRON definition warning; before/after probe output matches and execution remains disabled.

**Test scope:** new ZIP installation/update used extraction and activation; prior browser-update evidence remains separate. Synthetic nonempty queue preservation is not arbitrary queue resumption acceptance. No new live-S3 deletion, source data changes or repeated recovery was performed.

## 日本語

保持プレビュー入りの最終ZIPで新規導入・旧0.3.1からの更新が成功しました。設定、正式履歴70件、合成未確定キュー4件、復旧結果、試験記事・コメント・フォーム・会員・表を保持し、全3,814ファイルの一致を確認しました。今回はZIP展開・有効化方式で、標準ブラウザ更新の再実証ではありません。未確定操作は再開せず、保持と候補計算の停止を確認しています。

試験ロールの全版一覧権限不足と、製品の保持計算・表示は区別します。現在版は表示できますが過去の隠れた版は未評価です。期限超過候補や保持ロックの分岐はメモリ試験で確認しており、実S3を削除した証明ではありません。同期処理のため大量資産の実行時間制限は残ります。

既存S3資産・会員・コンテンツの変更、実削除・メール送信・定期実行・正式公開は行っていません。ローカル証拠: release-readiness/site-retention-final-20261025/。前回の画面証拠: release-readiness/site-retention-preview-20261025/。
