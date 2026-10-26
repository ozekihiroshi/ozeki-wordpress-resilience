# Actual deletion and retained-point recovery / 実削除・保持復旧点からの復旧

## Work and completion / 作業と完了条件

- Type: existing-feature verification, followed by evidence/documentation organization. 種類: 既存機能の検証とエビデンス整理。
- State: verified with limits. 状態: 検証済み・制限あり。
- Objective/completion: save disposable resources, review candidates, delete only their fixed versions, verify remaining bytes and restore from the retained Checkpoint plus subsequent formal history. All passed on 2026-10-26 at 08:31 JST. 目的・完了条件: 専用資源の保存、候補確認、固定版削除、残存資源の照合とCheckpoint・後続履歴からの復旧。すべて成立。
- Product contribution: preserve independently usable recovery resources while retiring obsolete points. 製品完成への寄与: 不要復旧点を削除しても、保全した独立資源から再構築できること。

## Identity and scope / 対象と範囲

The 13 product PHP source files used matched the unchanged unpublished candidate `ozeki-wordpress-resilience-0.3.1-gfs-lock-read.zip`, SHA-256 `8b14e94666e733cdc5018dbb4bdb4e7877ca9d91e3360f837d20877cece0a168`. This does not update the published v0.3.1-pre.1 ZIP or repeat installation/update acceptance.

使用した製品PHPソース13ファイルは上記未公開候補と一致。公開済みv0.3.1-pre.1の更新や導入更新の再試験ではない。

Existing community and dm containers/DB services were reused with isolated tables and content directories. Standard AWS SDK EC2 roles were used. Writes/deletes were limited to the previously empty disposable `sites/isolated-queue-lab/delete-validation-20261026/` prefix; older `sets/*` assets were not touched. dm made only S3 reads. No IAM changes were performed by the test, no live-site deployment or release occurred. Cron, updates and mail were disabled in the test bootstrap.

既存コンテナ・DBサービス内の隔離テーブル/ファイル領域を再利用し、AWS SDK標準EC2ロールで実行。書込み・削除は未使用確認済み専用prefixだけで、旧sets範囲は対象外。dmはS3読取りのみ。試験からIAM・既存コンテンツ・公開済みZIPは変更せず、公開なし。試験起動処理でCron・自動更新・メールを抑止した。

## Results / 結果

| Step / 段階 | Evidence / 結果 |
|---|---|
| Save / 保存 | 33 immutable versions: Baseline, history 1, independent Checkpoint through 1, history 2 / Baseline・履歴1・独立Checkpoint・履歴2 |
| Preview / 候補 | Complete inventory; 16 candidates, 17 retained, 0 blocked; history boundary 1→2 / 全版一覧で候補16・保持17・保留0 |
| Delete / 削除 | Old Baseline 13 versions and history 1 plus source/metadata 3 versions deleted by explicit VersionId / 旧基点13版と履歴1・原本・付随情報3版だけを固定版削除 |
| Preserve / 保全 | Remaining 17 versions all matched pre-deletion SHA-256; no delete markers / 残存全17版のハッシュ一致、削除マーカー0 |
| Restore / 復旧 | dm restored through history 2: body, title, publish, PNG SHA-256 and relocated image/page links matched / 本文・タイトル・公開状態・画像・リンク・終了番号一致 |
| Independence / 独立性 | 18 GETs and 1 LIST; GET targets limited to retained Checkpoint, history 2 and its originals. No old Baseline/history 1/source DB needed / 削除済み資源・元DBへの依存なし |

The restore reported four post rows including WordPress seed data; one page was edited and one PNG verified. Eighteen widget settings were reported as not automatically applied under existing rules; their originals remain in S3. This is not an all-settings/appearance guarantee.

復旧件数4はWordPress初期データを含み、編集対象は1ページ、画像は1件。ウィジェット設定18項目は既存規則に従い理由付き未適用として報告され、原本はS3に残る。全設定・外観の無条件一致は主張しない。

## Limits and environment / 制限と環境条件

Product `capture`, `prepare/commit`, `checkpoint`, `siteCleanupPreview`, `siteCleanup` and `restore` methods were called directly. This verifies real AWS writes/deletes/readback, **not browser/admin operation or scheduled automatic deletion**. The cutoff was the current test time, not naturally elapsed weeks/months. Resources had no Object Lock retention or Legal Hold; locked-object deletion and partial-deletion failures were not tested. Other GFS label/lock/error cases retain their earlier, separate evidence scope.

製品メソッドを直接呼び出した実AWS検証であり、**管理画面操作・定期自動削除は未検証**。基準は試験時の現在時刻で、自然な週・月単位の期限経過ではない。今回の資源に保持期限・Legal Hold設定はなく、保護中削除や削除途中の障害は試していない。GFS区分・ロック・異常系の既存検証とは区別する。

An earlier first PUT failed because the actual community role lacked an Allow for this prefix. The administrator corrected the existing policy; the unchanged product then succeeded. This was an environment permission condition, not a product fix. Neither that incident nor this acceptance grants permission to delete any other prefix.

先行する最初のPUT拒否はcommunity実行ロールの対象Allow不足。管理者の既存ポリシー修正後、同じ製品で成功した。製品修正ではなく環境権限条件であり、他prefixの削除を許可するものではない。

Detailed operator evidence is retained in the development workspace under `release-readiness/delete-validation-20261026/`: `plan.json`, `before.json`, `retained-hashes.json`, `delete-result.json`, `after.json`, `restore-result.json`, SDK call logs and `RESULT-ja.md`. These are local evidence, not links to files shipped in the repository. Test scripts have already run and must not be blindly rerun. The 17 retained test assets remain.

詳細証拠は上記開発作業領域に保全している。リポジトリ同梱ファイルではない。試験スクリプトは実行済みで、無条件に再実行しない。残した試験17版は維持。

[Operations / 運用手順](../../packages/markdown-m1/docs/gfs-checkpoints.md) · [日本語運用手順](../../packages/markdown-m1/docs/gfs-checkpoints-ja.md) · [Evidence index / 検証索引](product-evidence-index.md)
