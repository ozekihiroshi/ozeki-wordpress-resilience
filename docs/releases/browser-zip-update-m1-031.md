# Standard-admin ZIP update acceptance — 0.3.1

Date: 2026-10-25. Documentation-only follow-up; no product or package rebuild.

## Artifact and operation

The existing isolated dm WordPress trial used Chrome's **Plugins → Add Plugin → Upload Plugin → Install Now → Replace current with uploaded**. WordPress reported **Plugin updated successfully**. This replaced a prior trial deployment with the validated ZIP; both displayed version **0.3.1**. It is not evidence of migration between different version numbers.

Artifact: `release-candidates/20261025-editor-save/ozeki-wordpress-resilience-0.3.1-editor-save-final.zip` (7,385,571 bytes).

SHA-256: `901950f74d02d40bb4c21f92cecb6f7a80d30192f211a84191857f4e2bd3e5d2`.

All 3,813 installed files matched the ZIP. Installation was performed by the standard browser replacement flow, not a CLI install or file-copy substitute.

## Preservation and limits

Before/after comparisons matched configuration, all 68 S3 formal-history records, empty article/comment pending queues, recorded errors/notices, individual/site recovery results, latest recovery attempt, member settings and active plugins. The updated admin screen showed confirmed history 68, pending 0, recovery through 68 and 23 post records.

After removing only this test's temporary upload records, full hashes of posts, postmeta, users, usermeta, comments, commentmeta, terms, term_taxonomy, term_relationships and termmeta matched. The separate live site's probe also matched.

**Nonempty pending queues were not tested in this browser update.** Earlier file-extraction/overwrite acceptance preserved four synthetic pending operations; that is separate evidence, not browser-update acceptance. No new recovery execution was performed here.

## Environment and test setup, not product corrections

| Obstacle | Scoped action and outcome |
| --- | --- |
| Trial `DISALLOW_FILE_MODS=true` blocked installation | Trial configuration backed up, temporarily permitted, then restored byte-for-byte. |
| PHP upload limit 2 MiB (POST limit 8 MiB) rejected the ZIP | Trial Apache directory only temporarily used 16/20 MiB limits; override removed afterwards. No shared PHP setting or restart. |
| Mixed UID 1000 / www-data ownership caused a copy failure at `src/NativeHistory.php` | Only the isolated Resilience tree's ownership was normalized to the web-server user. Standard browser upload/replacement then succeeded. No PHP code change. |
| Chrome back navigation left Install Now disabled after file reselection | Reloading the upload form resolved it; no direct HTTP submission or authentication helper. |

The failed upload created a private ZIP attachment. Only that test-created attachment and the two test-upload cleanup reservations were removed using WordPress APIs. Initial mismatching hashes were retained as evidence rather than overwritten by the final successful comparison.

The **Cron option as a whole did change**, because core/admin/update operations registered events. `DISABLE_WP_CRON=true` and mail blocking remained enabled; periodic execution and mail sending were not performed. Event registration is not execution. A separate existing duplicate-Cron-constant warning belongs to the environment.

There was no new product correction in this acceptance. Source content, existing members, S3 assets, IAM, product source and the validated ZIP were not changed. Formal release remains deferred. These updated documents are not repackaged into the frozen ZIP.

## 日本語要約

既存dm隔離環境で、Chromeの標準「プラグインをアップロード」から「アップロードしたもので現在のものを置き換える」を実行し、更新成功を確認しました。同じ表示バージョン0.3.1の旧試験配置から検証済みZIPへの置換であり、異なる版番号間の移行試験ではありません。全3,813ファイルがZIPと一致しました。

設定・S3正式履歴68件・空の未確定キュー・エラー表示用状態・復旧結果・会員設定を保持し、試験アップロードの一時レコードだけを清掃した後、既存コンテンツ／会員のテーブルhashも一致しました。非空の未確定キューはブラウザ更新では未検証です。以前のファイル上書き試験での合成未確定4件の保持とは区別します。

管理画面でのファイル変更禁止、PHPアップロード上限、試験配置の所有権混在は環境設定の問題です。限定的な設定対処と標準画面での再試行で成功し、製品コード修正はありません。Cron予約全体は更新前後で一致せず、コアによる登録がありましたが、定期実行は無効のままです。メール送信・定期実行・正式公開・復旧の再試験は行っていません。

## Evidence provenance

Local acceptance record: `release-readiness/browser-zip-update-20261025/RESULT.md`, with success screenshot, before/after probes, pre-cleanup comparison, cleanup record and final comparison. Guarded execution scripts are not replay instructions. See the [installation/update procedure](../../packages/markdown-m1/docs/install-update.md).
