# WordPress.org更新候補 — Ozeki Resilience 0.3.2 rc.1

**未送信。** 2026年10月26日に受け付けられた0.3.1 rc.2の申請を更新するための候補です。受付済み版・タグ・ZIPは変更していません。WordPress.orgでの公開承認を意味しません。

## 更新内容

- 不足条件と次の操作が分かる準備画面、読取りによる保存先確認、利用条件の確認欄。
- 最初の保存と読み戻しを経て保護開始へ進む案内。既存の有効な保護は更新後も継続。
- 管理画面の日英表示と、実際の操作名・位置に合わせたREADME・導入・復旧・更新手順。
- Plugin Check対応として翻訳文出力のエスケープを追加。例外はHTML表示時にエスケープし、ローカルPHPの書込み権限確認は用途を限定して注記。

保存・復旧の対象拡大や依存ライブラリ更新はありません。

## 送信する内容

| 項目 | 内容 |
|---|---|
| アカウント | ozekihiroshi |
| 名称 / slug | Ozeki Resilience / ozeki-resilience |
| バージョン | 0.3.2 |
| ZIP | ozeki-resilience-0.3.2.zip |
| 容量 | 7,452,569 bytes |
| SHA-256 | `09fc645f156b1c3a887e189a506b0fdc632776ac12c3e570690279bac6cf25c2` |
| WordPress / PHP | 6.4以上 / 8.1以上（確認環境は下記） |
| Tested up to | 7.1 |
| Contributors | ozekihiroshi |
| ライセンス | GPLv2 or later |

[ZIPと照合情報](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.2-rc.1) · [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.2-rc.1/packages/markdown-m1) · [送信用補足説明](wordpress-org-032-additional-information.txt)

## 提出済み版の保全

[0.3.1 rc.2](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2)のZIP SHA-256は `537504d9b5be632a277c084ddfacf2a4f8a220498f940b6dde32c9e7bf650dbe` のままです。旧受付記録と送信済み補足説明も残しています。

## 限定確認結果

- 公式Plugin Check 2.1.0（WordPress.org配布版、runtime CLI bootstrap）：**0 errors / 109 warnings**。全件は[記録](../../evidence-public/wordpress-org-032/plugin-check.json)に保存。
- WordPress 7.1.3 / PHP 8.3.35 / MariaDBの隔離環境。実際の候補ZIPをWP-CLIで導入し、管理画面をブラウザーで操作。日本語で設定・利用条件確認・保存先確認・初期保存・保護開始を完了し、英語表示も確認。
- 提出済み0.3.1 rc.2を有効化した別の隔離WordPressへ候補ZIPを上書き更新。設定・投稿・確定履歴・本文/関連情報の未完了テスト記録・過去の復旧結果を保持。更新後の通常投稿も確定履歴へ保存。
- 新規導入・更新とも全3,854ファイルのパス・SHA-256が候補ZIPに一致。製品ファイルは対応ソースと一致し、依存ライブラリは提出済みrc.2とバイト単位で一致。
- PHP構文、準備条件・管理操作・表示・復旧結果の既存限定テスト、同梱Markdownの相対ファイルリンクを確認。

S3は模擬実装、データは生成データです。実AWS・既存サイトには接続していません。未完了記録の更新試験は保持の確認であり、その人工的な記録の再送試験ではありません。ブラウザーでのZIPアップロードは再実行していません。試験用コンテナーは終了時に削除し、利用者向けの既存プレビュー環境は残しています。

## 警告の扱い

| 分類 | 件数 | 確認内容 |
|---|---:|---|
| DB直接照会 | 32 | 履歴・トランザクション・準備条件の現在値。追加分はInnoDBと既存Markdownの有無。テーブル名はWordPress由来、値は固定またはprepareで束縛 |
| DBキャッシュなし | 30 | 保存・復旧状態および現在の準備条件を確認するため |
| メタキー/値検索 | 25 | 既存の対象コンテンツ・識別情報の照会 |
| InputNotSanitized | 12 | nonce確認後の本文保持・列挙値・数値等。追加のsetup_roleは厳密比較でsource/recoveryだけを採用 |
| MissingUnslash | 7 | 操作名・指紋・数値等の比較。追加のsetup_roleに任意入力を保存・出力しない |
| error_log | 2 | 永続的な失敗記録まで失敗した場合の診断。外部送信なし |
| unexpected_markdown_file | 1 | リンク先として使用する日本語README（RAADME-jp.md）を意図して保持 |

前回103件からの増加6件はDB照会/キャッシュ4件とsetup_role入力2件です。警告をカテゴリ単位で隠していません。

初回のPlugin Checkで出た12件のエラーは、翻訳文出力5か所のHTMLエスケープと、内部例外・ローカルPHP書込み条件の行単位の理由付き注記で対応しました。最終ZIPで再実行してエラー0件を確認しています。Plugin Check結果はWordPress.orgの承認ではありません。

## 再現用の確認手順

`packages/markdown-m1/tests/release-candidate.py` に、出力ディレクトリ、新ZIP、提出済みZIP、WP-CLI phar、公式Plugin Check ZIPをこの順で渡します。Dockerは隔離試験のためのもので、製品利用時の要件ではありません。
