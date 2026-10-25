# GFS Checkpoint candidate — review and verification

English / 日本語 · 2026-10-25 · Unpublished candidate

Work: final review and evidence organization. Status: verified with limitations. Completion condition: reviewed cumulative changes, matching package identity, aligned English/Japanese scope, and a reviewable pull request. This work supports independent recovery-point preservation; it does not publish a release.

## Package and implementation

[Candidate ZIP](../../release-candidates/20261025-gfs/ozeki-wordpress-resilience-0.3.1-gfs.zip) — 7,442,476 bytes, 3,829 files.

SHA-256: `88367d9c9b1fd3e201fb1066ca7e6695122915fb9e892b57ae7cce0ff11e3829`

The cumulative changes after PR #46 include weekly/monthly/yearly schedules, coincident-slot coalescing, independent complete copies even without edits, recorded retention labels, recent-history boundary preservation, and complete-site cleanup using an exact-version preview. Any active GFS label keeps the point. S3 deletion protection is optional and separate; positive protection invokes fixed-version deadline checks/extension before confirmation. The earlier manual renewal backend remains outside the normal GFS screen. See [English specification](../../packages/markdown-m1/docs/gfs-checkpoints.md) / [日本語仕様](../../packages/markdown-m1/docs/gfs-checkpoints-ja.md).

Published v0.3.1-pre.1 and the earlier checkpoint-verification ZIP are unchanged. Vendor files match the published ZIP; all packaged executable files match the reviewed source. This candidate is identified by its filename/hash, not the unchanged 0.3.1 display version.

## Evidence boundaries

| Evidence | Confirmed | Not established |
|---|---|---|
| Local contracts / memory S3 | Calendar boundaries, simultaneous labels, independent copies, active-year preservation, lock/stale-plan/failure handling | Real AWS deletion or retention extension |
| Existing isolated WordPress | Settings renderer, scheduled-event registration and deliberately due hook execution | Browser interaction or waiting weeks/months/years |
| Real S3 dedicated prefix | Standard EC2-role authentication; one point for three coincident rules; repeated slot causes no extra PUT; fixed-version label/expiry readback; active-year fixture and resources retained | Full version inventory, actual deletion; fixture dates are not elapsed-time acceptance |
| Final ZIP on existing dm service, isolated tables/content | Fresh activation and update from published Pre-release; GFS/S3 settings, scheduled slot, two synthetic pending records, diagnostics, results and content preserved; existing real S3 history/original readable; all installed files match ZIP | Browser ZIP upload, pending-queue resumption, new AWS writes or scheduled execution |

The real-S3 trial created 16 new test objects only in its dedicated scope. Existing assets were unchanged. Missing `s3:ListBucketVersions` permission prevented a complete inventory; the read-only fallback authorizes no deletion candidates. GFS retention was checked by explicit reason and resource membership, not by an empty candidate list. The permission gap is an environment prerequisite, not evidence of a product defect. Actual cleanup remains unaccepted. No IAM changes or real deletion were performed.

The ZIP trial's duplicate `DISABLE_WP_CRON` warning originates in the test bootstrap/shared configuration. Assertions and unchanged-site checks passed. It is recorded separately from product behavior.

[ZIP validation details](../../release-candidates/20261025-gfs/VALIDATION-ja.md), [installed-state results](../../release-candidates/20261025-gfs/install-results.txt), [offline contracts](../../release-candidates/20261025-gfs/zip-contract-results.json).

## 日本語

作業は最終レビューと検証記録の整理、状態は「検証済み・制限あり」です。累積差分・ZIP同一性・英日説明の整合を確認し、PRとして提示することを完了条件とします。独立した復旧点の確保・保持に寄与しますが、リリース公開は行いません。

週次・月次・年次の同日時は一回取得し、更新がなくても独立した完全一式を作成します。有効な保存区分が一つでもあれば保持します。後続履歴の必要範囲と、任意のS3削除保護は別の条件です。累積差分には完全サイトの削除実行経路も含まれますが、実削除は今回も実施していません。

実S3では専用範囲の書込み・固定版読取り・区分と期限・重複抑止・年次保持を確認しています。全バージョン一覧は既存IAMで拒否されるため、完全な削除候補評価と実削除は未検証です。これは権限の環境条件であり、製品不具合と混同しません。試験日時を指定した確認と、実時間の定期実行も区別します。

最終ZIPでは既存dmの隔離領域で新規導入・公開済み版からの更新を確認し、設定・予約・合成未確定操作・履歴・診断・復旧結果を保持しました。展開・有効化・再起動の試験であり、ブラウザアップロードや未確定操作の再開は今回の対象外です。試験用起動処理のCron定数重複警告は環境事象として記録しています。

公開済みZIP、既存S3資産・IAM・会員・コンテンツは変更していません。実削除・リリース公開は行っていません。
