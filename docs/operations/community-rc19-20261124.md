# community本番 rc.19更新・保存確認 / Production update and save verification

確認日：2026-11-24 JST。対象：https://www.community-energy.jp 。既に完了した本番確認の記録です。この文書作成に伴う本番操作は行っていません。

## 更新と保全

- rc.18からGitHub公開候補0.3.3 rc.19へ更新。全3,820配置ファイルが公開ZIPと一致しました。
- ZIP SHA-256: `6651029403cabd57c69e5aba7febe582b5784cfa800687ca7dc8e0182c2a6d9d`
- WordPress 7.1.5 / PHP 8.3.36。更新前のDB・プラグインの切戻し用コピーは本番ホストの非公開領域に保管しています。内容・本番データ・認証情報はリポジトリに含めません。
- 更新直後の既存コンテンツ・対象設定・正式履歴1〜72が不変であることを照合しました。トップページはHTTP 200でした。
- 保護はオン、定期保存・自動削除はオフを維持しています。既存S3原本・履歴の上書き/削除、本番での復旧は行っていません。

## 保存と読み戻し

最初の確認用下書きは、初めて作る未公開記事のため日常保全の対象外で、正式履歴は増えませんでした。これは試験条件の誤りであり、製品コードは変更していません。その後、利用者の明示承認を受け、確認用ページだけを公開して追記しました。

[確認用ページ](https://www.community-energy.jp/resilience-save-check-rc19-20261124/)（ID 144）は機密情報・個人情報を含まない動作確認の説明です。既存記事は編集していません。

- 公開本文は正式履歴73、追記本文は76で確定。別PHPリクエストでS3原本を読み戻し、保存本文との一致を確認しました。
- 追加4件は本文2件、記事付随情報1件、ACF記録1件です。既存履歴1〜72は不変です。
- 各保存後に既存コンテンツ各行・設定・既存履歴の不変を照合しました。追記の公開表示もHTTPで確認しました。
- 最終確認で記事・共通・添付の未完了保存や対応する保存エラーはありませんでした。

保存は通常の `wp_update_post` 等とプラグインフックを使用しました。ブラウザの編集画面操作ではありません。

## 日英表示と通常利用の確認範囲

- 日本語（ja）・英語（en_US）の実際の管理画面PHP描画で全76件の履歴行と記録済みタイトルを確認。PHP警告は0件で、描画前後の履歴ハッシュも一致しました。
- トップ・問い合わせ・会員ログイン・技術資料2ページはHTTP 200。問い合わせフォームとログインフォームが表示され、技術資料ページは匿名アクセス時にログイン案内を表示しました。
- 問い合わせの送信、メール配送、会員情報変更・会員としてのログイン操作は今回行っていません。全アクセス制限や全ブラウザ操作の検証を意味しません。
- 今回の読み戻し対象は確認ページの本文2件です。全76件の添付ファイル再取得や、本番履歴76までの隔離復旧を完了したという意味ではありません。

[更新結果](../../evidence-public/community-rc19-20261124/update-result.json) / [保存・読み戻し](../../evidence-public/community-rc19-20261124/save-result.json) / [日英表示](../../evidence-public/community-rc19-20261124/render-result.json) / [公開ページ表示](../../evidence-public/community-rc19-20261124/public-http.json) / [最終状態](../../evidence-public/community-rc19-20261124/final-status.json)

## 申請状況と次の段階

rc.19はWordPress.orgへ未提出で、今回の審査メール返信も行っていません。公開承認済みではありません。既存ZIP・タグを保全しています。本番で通常利用を進め、その保存内容を隔離環境へ復旧して確認した後に申請更新を判断します。[候補の確認記録](../releases/wordpress-org-033-rc19.md)。

## English

On 24 November 2026, community production was updated from rc.18 to the exact GitHub rc.19 ZIP. All 3,820 files matched. Private rollback copies remain on the host. Existing content, selected settings and formal history 1–72 were unchanged. Protection remains enabled; scheduled saves and automatic cleanup remain disabled.

A newly created unpublished draft did not enter daily history, as expected for that scope; the test assumption was corrected without product changes. With explicit permission, only verification page 144 was published and edited. Its bodies were confirmed at sequences 73 and 76 and matched separate-request S3 readback. Four new records comprise two page bodies, one native-detail record and one ACF record. Existing content/settings/history were preserved, with no unfinished saves or save errors at completion.

Japanese and English administration rendering displayed all 76 history rows with no PHP warnings. Public pages returned HTTP 200; contact/login forms and anonymous login prompts on technical pages were present. No inquiry submission, mail-delivery or member-login test was performed. Saving used normal WordPress APIs/hooks, not browser editor automation. Only the two verification page originals were read back; recovery through history 76 remains a subsequent task.

This documentation-only update does not access or modify production, original/history objects, existing ZIPs or tags. rc.19 has not been submitted to WordPress.org, and no review reply was sent. Publication is not approved.
