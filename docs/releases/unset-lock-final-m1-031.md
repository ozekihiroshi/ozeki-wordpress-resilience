# Unset Object Lock — final review / 設定なし対応の最終レビュー

2026-10-26 · Unpublished candidate / 未公開候補

Work: final review, regression verification and evidence organization. Status: verified with limitations. Completion: aligned English/Japanese scope, fixed package identity and a reviewable PR. This supports safe recovery-resource retention assessment without treating inaccessible state as unprotected.

作業：最終レビュー・回帰確認・エビデンス整理。状態：検証済み・制限あり。完了条件：英日説明と配布物の一致を確認し、PRとして提示する。復旧資源の保持評価で、確認できない状態を保護なしと誤認しないための修正です。

## Change / 修正

Only HTTP 404 `NoSuchObjectLockConfiguration`, followed by successful HEAD of the same Key/VersionId, means unset retention or Legal Hold. Access denial, network failure, missing versions and other 404s remain blocked. The site-wide and legacy previews share this reader. No deletion logic, permission or bypass is added.

同じ固定版の存在を確認できた場合だけ「設定なし」を許容します。拒否・通信障害・版の不在などは停止／保留します。製品差分は `Store.php` の共通読取り処理です。新規回帰試験はCIのPHP 8.1/8.3に追加しました。

## Evidence boundaries / 検証範囲

| Evidence / 検証 | Confirmed / 確認したこと | Not claimed / 対象外 |
|---|---|---|
| Real S3 preview / 実S3プレビュー | 16 versions; 3 retained points / 12 resources; 4 candidates; unchanged inventory. Existing renderer used in isolation. / 全版一覧不変、既存表示処理を隔離実行 | Actual deletion, live admin browser operation. Cutoff was current time for this test only. / 実削除・稼働管理画面操作・保持設定変更 |
| Injected faults / 模擬障害 | Retention and Legal Hold: unset, denied, network, missing version, unrelated 404, failed HEAD. Three ZIP-code regression suites passed. / 取得不能時の保留と無変更 | Real AWS outages. In-memory dependent tests include simulated deletion only. / 実AWS障害・実削除 |
| ZIP installation/update / ZIP導入更新 | Fresh and published pre.1 replacement in isolated dm tables/content; settings, two synthetic pending items, history references, diagnostics/results preserved; 3,829 installed files match ZIP. Real S3 history/original read-only match. / 設定・履歴・未確定操作・結果保持 | Browser upload, queue resumption, new S3 writes or another reconstruction. Synthetic queues must not run. / ブラウザ更新・合成キュー再開・新規書込み・復旧再実行 |

Read permissions were corrected earlier by the administrator for the test prefix; explicit delete Deny remains. The product defect was interpreting an absent lock configuration as an inspection failure. Duplicate DISABLE_WP_CRON warnings belong to the test bootstrap. During final review the local checkout lacked vendor/autoload.php; tests passed with the unchanged SDK from the verified ZIP. CI installs its declared dependencies before running them. These environment conditions are not new product defects.

一覧・ロック読取り権限は管理者によって先に解消済みです。削除拒否は維持しています。製品修正は「設定なし」の判定のみ。Cron定数の重複警告とローカルvendor未配置は試験環境の事情であり、製品課題と区別します。

## Package / 配布物

[ZIP](../../release-candidates/20261026-gfs-lock-read/ozeki-wordpress-resilience-0.3.1-gfs-lock-read.zip) · [Validation / 導入更新記録](../../release-candidates/20261026-gfs-lock-read/VALIDATION-ja.md) · [Contract outputs](../../release-candidates/20261026-gfs-lock-read/zip-contract-results.json)

SHA-256: `8b14e94666e733cdc5018dbb4bdb4e7877ca9d91e3360f837d20877cece0a168`

7,447,608 bytes; 3,829 files. Product version remains 0.3.1; identify by full filename and checksum. All vendor files match the published ZIP. Prior GFS and published ZIPs remain unchanged. No IAM/S3/content changes or release publication are part of this review.

[English scope](../../packages/markdown-m1/docs/gfs-checkpoints.md) · [日本語範囲](../../packages/markdown-m1/docs/gfs-checkpoints-ja.md)
