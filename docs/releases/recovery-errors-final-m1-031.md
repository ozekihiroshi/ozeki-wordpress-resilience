# Recovery failure detection — final ZIP acceptance

Date: 2026-10-25. Type: evidence consolidation and existing-function verification. Initial status: correction verified in isolation, final package not yet accepted. Final status: fresh installation and same-version extraction update accepted with the limits below. Completion condition: preserve settings/history/pending/result state and pass focused tests against actual ZIP contents. Contribution: ship the corrected outcome reporting without expanding recovery mechanisms.

## Governing principle

Prioritize the integrity of irreplaceable recovery resources; do not overcomplicate failure handling for recovery operations that can be executed again.

「失えば取り戻せない復旧資源の完全性を最優先し、再実行できる復旧処理の失敗対策を過度に複雑化させない。」

## Artifact

[0.3.1 recovery-errors-final ZIP](../../release-candidates/20261025-recovery-errors/ozeki-wordpress-resilience-0.3.1-recovery-errors-final.zip)

SHA-256: `8aa35ca377346125c1b5019a014ada528d54157063a64f7ec80555c54fc5d3a9`.
7,399,496 bytes / 3,814 files. Compared with point-time-final: MemberHistory.php, Plugin.php, SiteSnapshot.php and bilingual packaged README changed. Vendor unchanged; all packaged product files match source. Earlier ZIP preserved. No formal release.

## Focused evidence

Reused existing dm containers/core/database with separate unused `owrrezip_20261025_fresh_` and `owrrezip_20261025_upgrade_` namespaces. Fresh install used the new ZIP; update installed point-time-final, seeded isolated fixtures, then extracted the new ZIP. No browser Upload/Replace claim.

Both paths passed: configuration, test content/identities/comments/forms/member hashes/settings/tables, four synthetic shared pending operations/errors, recovery results and selected boundaries preserved. Unchanged recovery results were accepted by the new persisted-value check. Real S3 history70 remained identical (serialization hash `cc3bac5abe027b212876ee8b24c44955d25e94dd91c726402987671e32b4ba56`). All 3,814 installed files match ZIP entries. Shared live-site before/after probe identical. No queue resume, new cloud recovery, S3 writes/deletes, email delivery, scheduled execution or existing member/content modifications.

ZIP-extracted code passed failure-detection, recovery-result and selected-point contracts plus PHP syntax checks. The new failure contract uses a synthetic database double; preceding [actual WordPress/DB fault-injection acceptance](recovery-errors-m1-031.md) is separate and reused, not repeated. Browser recovery and older browser ZIP-update evidence remain distinct.

## Scope and limits

DB START/COMMIT return errors and persisted-value failures stop the recovery success path. Failure response shows cause; if failure recording also fails, it warns that stored results can be older. Unchanged values are valid. No automatic resume/retry or new rollback mechanism. A post-COMMIT error may leave content applied. Database unavailability prevents guaranteed durable error recording. No acceptance for forced process termination, actual AWS outages or unknown-COMMIT connection loss.

The first correction trial's empty-value get_var issue was a product defect in the new helper, fixed before this ZIP. Existing duplicate DISABLE_WP_CRON probe warning is an environment issue; it did not affect preservation checks. No new packaging failure or new dependency. Synthetic pending records were preserved, not resumed. Existing ListBucketVersions permission limitation remains unchanged.

## 日本語

作業種類はエビデンス整理・既存機能の検証。修正済みコードを最終ZIPへ収録し、新規導入・旧point-time-finalからの展開更新が合格しました。設定・履歴70件・合成未確定キュー4件・失敗理由・復旧結果を保持し、全3,814ファイル一致を確認しました。状態は検証済み・制限あり、今回の完了条件は達成です。

英日READMEに停止・原因表示・記録不能時の制限を記載しました。ZIP内コードの失敗検出・結果表示・指定時点試験は合格。以前の実WordPress/DB故障注入、ブラウザ復旧と今回の展開更新は別の証拠です。全復旧の再試験、自動再開・巻戻し追加、既存会員・コンテンツ変更、メール送信、定期実行、S3削除、正式公開は行っていません。

Local evidence: release-readiness/recovery-errors-final-20261025/ (build-result.json, zip-contract-results.json, installation output, ZIP byte checks, before/after probes).
