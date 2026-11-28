# 未適用項目の限定修正・確認（2026-11-28）

後続の[4項目修正](recovery-fields-20261128.md)と[実S3確認・取り込み記録](recovery-fields-s3-20261128.md)。以下の「未修正」はこの先行調査時点の状態。

## 実施した修正

TablePressの通常の参照 `[table id="1" /]` が、復旧時に文字列化される問題を修正した。
原因は、WordPressが属性解析前に取り除く末尾の自己終了 `/` を、RecoveryContentが属性に含めて検査していたこと。
同じ解析を使うCF7・Markdownの認識済み参照にも、同じ構文境界を適用した。
属性の許可リストや実行可能なタグは増やしていない。原本・保存形式は変更しない。
すでに文字列化して再保存した内容を、自動的に実行可能に戻す処理は追加しない。

修正前に標準構文の失敗を確認してから変更した。末尾スラッシュあり／なし、空白・改行、
不明属性・余分な引数・重複スラッシュ・不適合IDを確認。既存のHTML、コード例、未認識ショートコード、
動的ブロックの安全処理と静的な編集構造の確認も成功した。

## 隔離確認の範囲

- dm上の専用Dockerネットワーク（internal、公開ポートなし）、専用MariaDB、架空データ。
- rc.23のコピーにRecoveryContent.phpだけを差し替えた。提出済みZIPは不変。
- WordPress 7.1.5 / PHP 8.3、CLIメモリ上限256MB。対応ソフトウェアは既存の公式ZIPから事前導入。
- Markdown Documentsは本番と前回確認に合わせた0.1.2。0.1.3の結果とはしない。
- S3 SDKの既存試験用ローカル転送を使用。実S3・本番・既存原本・履歴へアクセスしていない。
- ページ内の自己終了TablePress参照を保存、復旧、通常のthe_content経路で表示、wp_update_postで編集、
  新しい初回保存、再復旧、再度表示・編集。表要素・セルの内容・追記を確認した。
- 再復旧後は内部HTTPでもページに表・セル・追記があることを確認した。単なるモデル読取りではない。
- 表セル内の未認識ショートコードは実行されない。往復中、保存済み試験オブジェクトのハッシュは不変。
- この試験は初回保存を使う往復であり、保護オンの日常保存による正式履歴確定の追加確認ではない。
- 全画面の対話的ブラウザ操作や実メール配送は対象外。

試験環境調整：同じ使い捨てDBに固定キーのACFフィクスチャを二度投入した際に重複キーで停止した。
今回専用DBを新規作成して最終往復を成功させた。限定調査では、前の合成会員が残る復旧先との
識別衝突を避けるため、復旧前に試験用会員だけを除去した。いずれも製品の検証規則は緩和していない。

## Markdown・CF7の限定調査結果（未修正）

| 対象 | 復旧前 | 復旧後 | 判定 |
|---|---|---|---|
| Markdownの過去版 | WordPressの過去版復元で旧原文に戻る | revisionレコードはあるが原文メタがなく、差し戻すと原文が空になる。現在の原文は差戻し前には存在 | 不具合を確認。現在版の表示・原本復旧の成功と区別する |
| CF7標準のyour-name/email/subject | 指定通りFlamingoへ受信 | 明示指定は除外されるがCF7の既定値と一致し、氏名・メール・件名は同じ | communityで確認した指定について影響なし |
| CF7独自項目名の対応指定 | 指定した項目の値で受信 | 対応指定が除外され、既定の未置換タグが氏名・メール・件名に入る | 一般の対応付けに不整合あり。今回修正していない |

CF7は実際のsubmitとFlamingoの受信フックを通した。skip_mailにより外部送信なし。
`mail_sent`は試験内のスキップ成功状態であり、実メール配送を意味しない。
Markdownは現在原文・旧原文を別に作り、標準wp_restore_post_revisionの前後を比較した。
確認後は試験の現在原文を戻した。本番のリビジョンは操作していない。

## 戻す情報の扱い案（今回の実装対象外）

| 情報 | 扱い案・適用境界 |
|---|---|
| Markdownの過去版原文 | 親が対応Markdown文書であることを照合して戻す。原文は文字列のまま保持し、表示時の安全処理と区別。差戻し後の派生ハッシュ・キャッシュ整合も合格条件にする |
| Markdownの元ファイル名 | 書き出し時の名前として戻す。実パスとしては適用しない。現状は失うとスラッグ／題名からの.md名へフォールバックする |
| ACFのinstructions（今回の実データ4項目） | 正常な入力支援情報として戻す対象にする案。管理画面でHTML表示される境界だけを安全化し、定義・値全体へHTML処理をかけない |
| ACFグループの説明・並び順等 | 利用案内と純粋な表示設定を区別して採用判断。条件分岐・追加取得・任意機能まで一括で許可しない |
| CF7→Flamingoの3つの項目対応 | 既知の氏名・メール・件名と存在するフォーム項目の対応だけを構造化して扱う案。任意の追加指示をそのまま実行しない |
| レンダリングキャッシュ・ハッシュ | 復旧した原文から再生成。保存元のキャッシュを無条件に適用しない |
| テーマ・ウィジェット・プラグイン全体設定 | これまでどおり復旧先の準備済み設定を維持。情報の説明文が欠ける問題と混同しない |

これらの追加修正は未実施。原本の保存形式の変更が必要との判断もしていない。
TablePress修正はブランチ内のソース変更のみで、mainへの取り込み・公開ZIP作成・申請は行っていない。

## 根拠

- [修正前失敗と修正後成功](recovery-embed-20261128/regression.txt)
- [保存・復旧・編集・再保存・再復旧](recovery-embed-20261128/roundtrip-result.json)
- [再復旧後のHTTP表示](recovery-embed-20261128/http-result.json)
- [Markdown過去版とCF7連携の前後比較](recovery-embed-20261128/limited-results.json)
- 再発確認：`packages/markdown-m1/tests/review-safe-content.php`、`review-integrations.php`、`review-roundtrip.php`
- 限定調査：`packages/markdown-m1/tests/recovery-omission-impact.php`
- rc.23 ZIP SHA-256：`062a8c423c4ecca40b0075dc65d4d783e27ed884024fc66c5933f341e7de5447`

## English

The closing slash in a supported self-closing shortcode was incorrectly parsed as an extra attribute.
The fix matches WordPress's grammar boundary before checking the existing attribute allowlist; it does not
enable additional tags or attributes, change archived originals, or reactivate text already neutralized.
A failing-before/passing-after check and a synthetic isolated round trip verified actual TablePress page
rendering, normal editing, recapture and second recovery. Internal HTTP verified the final table and edit.
Existing safety checks passed. Storage was the local SDK test transport, not live S3.

Limited diagnostics confirmed two separate, unfixed issues: restored Markdown revisions lose their source
metadata, so reverting to an old revision empties the source; custom CF7-to-Flamingo field mappings are dropped.
The standard your-name/email/subject mapping used by the investigated site still works through CF7 defaults.
No email was delivered. ACF instructions and original Markdown filenames are proposed as useful recoverable
information, with HTML-display and filename boundaries kept separate from raw structured data.
Production, existing originals/history, submitted ZIPs and tags were not modified.
