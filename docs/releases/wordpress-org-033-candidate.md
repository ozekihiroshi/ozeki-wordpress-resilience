# WordPress.org 0.3.3 rc.1 公開準備記録

2026-10-28 JST。**準備完了・未送信**。既存の0.3.2 rc.1申請は審査待ちで、公開承認済みではありません。

## 変更と提出予定

PR #60のACF無料版基本15型対応。投稿・固定ページの値・定義・キー参照を保全して復旧します。文字列型保持・ハイフン名の修正を含みます。日英README・導入更新案内・readme.txtを整理。更新後にACFを保護へ加える場合は新しい信頼済みBaselineを作成し、既存の記事保護は継続します。

- 名称 Ozeki Resilience / slug ozeki-resilience / contributor ozekihiroshi
- Version 0.3.3 / tag wporg-0.3.3-rc.1
- ZIP ozeki-resilience-0.3.3.zip / 7,466,296 bytes / 3,859 files
- SHA-256 `723a0e37316da77281d871dffeb0e5cb6a7f82c1e34017866d09f2455d43661e`
- [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.1/packages/markdown-m1)
- [申請補足説明案](../../evidence-public/wordpress-org-033/submission-draft.txt)

## 確認結果

- [最終ZIPの隔離確認](../../evidence-public/wordpress-org-033/validation.json)：WordPress 7.1.3 / PHP 8.3.35 / 一時MariaDB / 模擬S3。新規導入、CLIで初期保存・保護開始、日本語描画、0.3.2 rc.1からの更新、設定・履歴・未完了の保存・復旧結果の保持、更新後の保存継続が成功。配置全ファイルがZIPと一致。
- 公式Plugin Check 2.1.0：**0 errors / 117 warnings**。[全件](../../evidence-public/wordpress-org-033/plugin-check.json)。追加8警告はACFのDB照会/キャッシュとメタデータキー/値に関するもの。[PR受入レビュー](../../evidence-public/acf-free-20261028/public-review.md)で確認済み。
- [静的確認](../../evidence-public/wordpress-org-033/static-validation.json)：マニフェストと製品ソースが一致。依存ライブラリ3,785ファイルは提出済み0.3.2 rc.1と同一。
- ACF回帰・日英画面・準備条件の契約試験も成功。既存の実WordPress/実S3証拠は[ACF検証記録](../../packages/markdown-m1/docs/acf-free-verification-ja.md)を参照。今回はブラウザー操作・実AWS・ACF全サイト復旧の新規再試験ではありません。

## 保全と次の操作

提出済み0.3.2 rc.1（SHA-256 `09fc645f156b1c3a887e189a506b0fdc632776ac12c3e570690279bac6cf25c2`）と0.3.1 rc.2、旧タグ・申請記録は保全。既存サイトと未コミットの研究作業は変更していません。管理者がZIPと補足説明を確認した後、既存申請を更新します。まだ送信していません。
