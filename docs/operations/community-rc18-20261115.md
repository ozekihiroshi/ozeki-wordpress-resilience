# community本番 rc.18更新・保存確認 / Production update and save verification

確認日：2026-11-15 JST。対象：https://www.community-energy.jp 。完了済みの本番確認を記録したものです。この文書作成に伴う本番操作は行っていません。

## 更新と保全

- rc.16から提出済み0.3.3 rc.18へ更新し、全3,818配置ファイルがZIPと一致しました。
- ZIP SHA-256: `eadc9ec4de01f06014414a9bb709b11905019e525fdbdc918f45d3626d2f2d97`
- WordPress 7.1.4 / PHP 8.3.36。更新前のDB・プラグインを本番ホストの非公開領域へ退避しました。退避内容・本番データ・認証情報はリポジトリに含めません。
- 更新直後の既存コンテンツ・対象設定・正式履歴1〜41のハッシュ一致を確認しました。公開トップページはHTTP 200でした。
- 保護はオン、定期保存・自動削除はオフのままです。既存原本・履歴の上書き/削除、復旧操作は行っていません。提出済みZIPと既存タグは不変です。

## 保存と原本の読み戻し

既存記事を編集せず、機密情報・個人情報を含まない[確認用ページ](https://www.community-energy.jp/resilience-save-check-rc18-20261115/)（ID 130）を新規作成し、追記しました。確認用ページは残しています。

- 新規本文は正式履歴42、追記本文は66で確定しました。それぞれS3原本を読み戻し、保存本文との一致を確認しました。追記内容の公開表示もHTTPで確認しました。
- 追加25件の内訳は本文2件、添付一式21件、記事付随情報1件、ACF記録1件です。保存に伴う関連処理で既存登録添付の一式も新たに保全されました。既存履歴1〜41を上書きしたものではありません。
- 各保存後に既存コンテンツ各行・設定と履歴1〜41の不変を照合しました。
- 最終確認で記事・共通・添付の未完了保存、添付エラー・共通エラー・capture errorはありませんでした。

通常の `wp_insert_post` / `wp_update_post` とプラグインフックによる保存です。ブラウザの編集画面操作ではありません。S3読取りと保存結果の照合は別PHPリクエストで実施しました。

## 日英の履歴表示

日本語（ja）・英語（en_US）の実際の管理画面PHP描画で、全66件の履歴行・記録済みタイトルを確認しました。PHP警告は0件で、描画前後の履歴全体ハッシュも一致しました。フォーム送信は行っていません。

これは66件の正式履歴の読取り・表示と、確認ページ本文2件の原本読み戻しの確認です。全66件に付随する全ファイルの再取得や、本番での復旧確認を意味しません。

[更新結果](../../evidence-public/community-rc18-20261115/update-result.json) / [保存・読み戻し](../../evidence-public/community-rc18-20261115/save-result.json) / [日英表示](../../evidence-public/community-rc18-20261115/render-result.json) / [rc.18申請記録](../releases/wordpress-org-033-rc18.md)

## 審査状況

rc.18の既存申請への更新受付と元の審査メールへの返信は完了しています。審査担当者の回答待ちで、公開承認済みではありません。本番利用開始は公開承認を意味しません。

## English

On 15 November 2026, community production was updated from rc.16 to the exact submitted rc.18 ZIP. All 3,818 installed files matched. Private database/plugin rollback backups remain on the host. Existing content, selected settings and formal history 1–41 were unchanged immediately after updating; the homepage returned HTTP 200. Protection remains enabled, with scheduled saves and automatic cleanup disabled.

A new non-sensitive verification page (ID 130) was created and edited without editing existing articles. Its initial and edited bodies were confirmed at sequences 42 and 66 and read back from S3 with matching content. The 25 additional records comprise two page bodies, 21 attachment bundles, one native-detail record and one ACF record. Existing content rows, settings and history 1–41 remained unchanged. No pending article/shared/attachment saves or corresponding save errors remained at the final check.

Actual PHP administration rendering showed all 66 formal history records in English and Japanese with zero PHP warnings and unchanged history hashes. Saving used normal WordPress functions and plugin hooks, not browser editor automation. This does not claim that all files associated with all 66 records were re-fetched or that production recovery was performed.

This documentation-only change does not access or modify production, existing S3 assets, submitted ZIPs or tags. WordPress.org review is awaiting the reviewer response; publication has not been approved.
