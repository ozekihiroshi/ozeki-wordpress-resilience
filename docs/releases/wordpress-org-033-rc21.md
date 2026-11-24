# Ozeki Resilience 0.3.3 rc.21 — candidate verification

2026-11-24。**community本番への導入前の候補です。WordPress.orgへの送信・審査メール返信は行っていません。提出済みrc.20は審査担当者の回答待ちであり、公開承認済みではありません。**

## 今回の向上

- 復旧先で準備したテンプレート・ナビゲーションを維持し、復旧した本文を表示します。保存元の実行可能なレイアウトを自動で有効にしません。
- Markdownの埋込みは参照先文書自身の閲覧条件を確認します。会員向け資料を非会員へ見せず、許可された利用者には見出しや表を表示します。原文は変更せず、表示結果を安全化します。
- 自動保存・編集ロック更新が不要な全添付再照合を起動する原因を修正しました。実際の閲覧条件変更の保存は維持し、競合時は未完了の記録と再開案内を残します。

[原因・共通処理の変更・回帰確認](../review/content-usability-20261124.md)。復旧時に他のプラグインをインストール・初期化せず、管理者が準備したソフトウェアと設定を使う方針は継続します。

## ZIPと対応ソース

- [候補ZIP・GitHub Release](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.21)
- [固定した対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.21): `5ea18068f7dbfffd4d81cb4cecaa5b8898ebe955`
- SHA-256: `ec0b5cbedd7855054d87ef5656ffcfbde25335c25d4e939b0291d73acf0874de`
- 8,326,009 bytes / 3,821ファイル。製品45ファイルが対応ソースと一致。rc.20との差分15ファイル、削除なし、依存ライブラリ不変。
- 同梱ガイド8件・相対リンク86件を確認。開発資料・試験は同梱しません。

## 完成ZIPの確認

| 項目 | 結果 |
|---|---|
| 新規導入・rc.20からの更新 | 成功。更新前の設定・記事・有効化状態を維持 |
| ZIP整合 | 導入後・試験後とも全3,821ファイルが完成ZIPと一致 |
| 初回保存＋正式履歴77 | 91投稿を復旧。確認ページの既存追記も表示 |
| 日英管理画面 | 再復旧後の履歴を含む描画でPHP警告0 |
| Chromeの通常利用 | 準備済みヘッダーと本文、会員ログイン・資料の見出しと表、管理者の追記保存を確認 |
| 非会員・安全な表示 | 会員文書は非表示、未知命令は文字のまま。文書原文は不変 |
| 保護オンの自動保存＋通常保存 | 両方HTTP 200。通常保存12.13秒、続く保存7.23秒。追記確定、未完了なし |
| 実S3への再保存・再復旧 | 新規試験Baseline＋履歴5まで再復旧。Chromeの追記と文書参照も利用可能 |
| データ照合 | 対応する46レコード、ファイル内容・閲覧条件、会員制限が一致 |
| 添付原本 | 対象51件の不足0。公開12件HTTP 200、保留39件HTTP 404を両復旧後に確認 |
| 準備済み設定 | テーマ・TablePress・ウィジェット・WP-Members設定を両復旧後に維持 |
| ソフトウェア | 両復旧で変更なし、install/uninstall.php読込みなし、初期化禁止ガードに抵触なし |
| 原本・障害 | 固定コピー638件のハッシュ不変。S3通信失敗0、サーバーログのPHP Warning/Fatal/Uncaught 0 |

通常保存の時間には隔離環境とSSH/S3中継の時間が含まれ、本番性能を約束する値ではありません。最初の復旧の未適用250件、再復旧の149件は適用結果に残しています。すべての設定を戻したという意味ではありません。

[ZIP監査](../../evidence-public/wordpress-org-033-rc21/package-audit.json) / [対応ソース](../../evidence-public/wordpress-org-033-rc21/source-match.json) / [Plugin Check全件](../../evidence-public/wordpress-org-033-rc21/plugin-check.json) / [実S3・導入更新](../../evidence-public/wordpress-org-033-rc21/real-s3-result.json) / [ブラウザ・日英管理画面](../../evidence-public/wordpress-org-033-rc21/browser-admin.json) / [保全](../../evidence-public/wordpress-org-033-rc21/preservation.json)

対応ソースの[Actions](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/actions/runs/45345737771)は成功しました。確認記録を含むmainのActionsも公開時に確認します。

Plugin Check 2.2.0はエラー0、警告124。rc.20の123件に加え、`RecoveryTemplates.php:68` の `meta_value` 代入にSlowDBQuery警告が1件あります。この行はメモリ上の復旧計画配列を変更する処理で、DB検索の実行ではありません。抑制せず全件を記録しています。

隔離環境はdmの専用Docker（WordPress 7.1.4 / PHP 8.3.37）。完成ZIPをそのまま導入し、製品コードの上書き補正はしていません。communityの初回保存＋履歴77は638オブジェクトの読取り専用固定コピーです。再保存・再復旧は制限付き中継を介し、新規の実S3試験領域だけを使いました。メール・Cron・無関係の外部HTTPは停止しています。

最初のHTTP確認は試験内部ホスト名へのアクセスによる正規URLへの転送で停止しました。試験の接続先とHostを正式な隔離URLへ揃え、記事の正規URL転送を追うようにして再実行しました。製品ZIPは変更していません。日英の管理画面描画試験もWordPress管理画面の補助関数を正しくロードして実施しています。

## 互換性・確認範囲

記録形式は変わりません。既存原本・履歴の書換え、移行、新しい初回保存は不要です。復旧先にも今回の候補を用意してください。以前の版で文字化した埋込みを一括で命令へ戻すことはしません。原本から復旧するか、管理者が正しい文書参照を明示的に設定します。

保存元と同じデザインを自動再現する変更ではありません。復旧先で準備した表示構成を使います。識別できない参照は適用結果に残します。未知の外部プラグイン・任意の描画処理・すべての同時編集負荷まで確認したという意味ではありません。

本番への導入は次の別途確認段階です。本番サイト・既存原本と履歴・提出済みrc.20を含む既存ZIPとタグは変更していません。研究側の未コミット変更も保全しています。

## English summary

rc.21 is a GitHub prerelease candidate, not deployed to community and not submitted to WordPress.org. Submitted rc.20 remains awaiting the reviewer’s response, not approved.

This candidate preserves prepared destination templates/navigation, checks the referenced Markdown document’s own viewing conditions before safe rendering, and prevents revision autosaves/editor locks from triggering unnecessary media reconciliation. Original Markdown, archive formats and existing history remain unchanged. Recovery does not install or initialize third-party software. Previously textified references are not automatically decoded into executable commands.

See the results and evidence above for exact-ZIP installation/update, Plugin Check, browser use and isolated real-S3 resave/recovery scope. Production installation is the next separately reviewed step.

