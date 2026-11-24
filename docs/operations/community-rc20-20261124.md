# community本番 rc.20更新・保存確認 / Production update and save verification

確認日：2026-11-24 JST。対象：https://www.community-energy.jp 。既に完了した本番確認の記録です。この文書作成に伴う本番操作は行っていません。

## 更新と保全

- rc.19からGitHub公開候補0.3.3 rc.20へ更新。全3,820配置ファイルが公開ZIPと一致しました。
- ZIP SHA-256: `90849e809d215b9472fba3c36226a171fffb432922cf7aaf6eb14ea1a516e610`
- WordPress 7.1.5 / PHP 8.3.36。更新前のDB・プラグインの切戻し用コピーは本番ホストの非公開領域に保管しています。本番データ・認証情報はリポジトリに含めません。
- 更新直後の既存コンテンツ・対象設定・正式履歴1〜76が不変であることを照合しました。トップページはHTTP 200でした。
- 保護はオン、定期保存・自動削除はオフを維持しています。既存S3原本・履歴の上書き/削除、本番での復旧は行っていません。

## 保存と読み戻し

既存の[確認用ページ](https://www.community-energy.jp/resilience-save-check-rc19-20261124/)（ID 144）だけに、rc.20更新後の保存確認について追記しました。機密情報・個人情報は含みません。他の既存記事は編集していません。

- 追記本文は正式履歴77で確定。別PHPリクエストでS3原本を読み戻し、保存本文との一致を確認しました。追記は公開ページのHTTP表示でも確認しました。
- 既存履歴1〜76、設定、確認ページ以外の照合対象の既存行は不変です。今回追加した履歴はページ本文1件です。
- 最終確認で記事・共通・添付の未完了保存や対応する保存エラーはありませんでした。
- 検証スクリプトは一度、保存後に付加した読み戻し注記 `source` / `verified` を保存前の記録と比較して停止しました。保存済み履歴の変更ではありません。注記を比較から除いて読み取り確認を続け、既存履歴の不変を確認しました。確認ページの再編集や製品コードの変更は行っていません。

保存は通常の `wp_update_post` とプラグインフックを使用しました。ブラウザ編集画面の操作ではありません。

## 日英表示と確認範囲

- 日本語（ja）・英語（en_US）の管理画面PHP描画で、全77件の履歴行と記録済みタイトルを確認。PHP警告0件、描画前後の履歴ハッシュも一致しました。
- トップ・問い合わせ・会員ログイン・技術資料2ページはHTTP 200。問い合わせフォームとログインフォームが表示され、技術資料ページは匿名アクセス時にログイン案内を表示しました。
- 問い合わせ送信、メール配送、会員ログイン・会員情報変更は今回行っていません。全アクセス制限や全ブラウザ操作の検証を意味しません。
- 今回の保存確認の主対象は確認ページの本文です。新しい履歴77までを使った隔離復旧・再保存・再復旧は、この記録には含みません。候補作成時には履歴76までで往復確認済みです。

[更新結果](../../evidence-public/community-rc20-20261124/update-result.json) / [保存・読み戻し](../../evidence-public/community-rc20-20261124/save-result.json) / [日英表示](../../evidence-public/community-rc20-20261124/render-result.json) / [公開ページ表示](../../evidence-public/community-rc20-20261124/public-http.json) / [最終状態](../../evidence-public/community-rc20-20261124/final-status.json)

## 申請状況

rc.20はWordPress.orgへ未提出で、審査メール返信も行っていません。公開承認済みではありません。既存原本・履歴・ZIP・タグを保全しています。[候補作成時の確認記録](../releases/wordpress-org-033-rc20.md)。この運用記録の反映では本番へアクセスせず、文書と公開可能な集計結果だけを更新しています。

## English

On 24 November 2026, community production was updated from rc.19 to the exact GitHub rc.20 ZIP. All 3,820 installed files matched. Private rollback copies remain on the host. Existing content, selected settings and formal history 1–76 were unchanged immediately after the update. Protection remains enabled; scheduled saves and automatic cleanup remain disabled.

Only existing verification page 144 was appended. Its body was confirmed at sequence 77 and matched separate-request S3 readback and public HTTP output. Other compared existing rows, settings and history 1–76 were preserved. There were no unfinished saves or recorded save errors. An initial verification assertion compared newly added readback annotations against the earlier observation; excluding those annotations confirmed unchanged stored history without another page edit or product change.

Japanese and English administration rendering displayed all 77 history rows without PHP warnings. Public contact/login forms and anonymous login prompts on the technical pages were present. Saving used WordPress APIs/hooks, not browser editor automation. No inquiry delivery or member-login test was performed. Isolated recovery through the newly added sequence 77 remains outside this record; candidate validation had covered recovery/resave/recovery through source sequence 76.

This documentation update does not access production or modify originals, history, ZIPs or tags. rc.20 has not been submitted to WordPress.org, no review reply was sent, and publication is not approved.

## 後続の隔離復旧確認 / Subsequent isolated recovery

同日、履歴77までを使ったrc.20の隔離復旧・実S3への再保存・再復旧を完了しました。[結果と確認範囲](community-rc20-history77-20261124.md)。上記の本番保存確認とは別の作業で、本番への追加変更はありません。

Recovery/resave/recovery through source history 77 subsequently passed in isolation. See the linked record for scope and preservation checks; no further production change was made.
