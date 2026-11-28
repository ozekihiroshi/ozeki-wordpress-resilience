# 復旧項目・埋込み修正：実S3確認と取り込み記録

2026-11-28 JST。対象はrc.23後の開発ソース。提出済みrc.23・本番は更新しない。

## 最終レビュー

- [TablePress等の標準埋込み構文](recovery-embed-20261128.md)：末尾スラッシュを構文として扱い、許可属性・タグは増やさない。
- [Markdown過去版・元ファイル名、CF7連携、ACF説明文](recovery-fields-20261128.md)：親文書・フォーム項目・表示用HTML・ファイル名という適用境界をそれぞれ照合。
- 原本保存、履歴・記録形式、ソフトウェアの事前準備方針は不変。第三者ソフトウェアのインストール・初期化を復旧に追加しない。
- 既存のapplication-rules / ACF契約と、今回の適用契約・安全処理テストを確認。
- 日本語READMEの古い「本番未導入」を既存運用記録に合わせて訂正し、開発ソースの追加修正と提出済みrc.23を日英で区別。

## 実S3確認の構成

dmの新規専用Docker環境を使用。internalネットワーク、公開ポートなし、独立DB、合成データのみ。
WordPress 7.1.5、PHP 8.3、CLIメモリ256MB。対応プラグインは前回と同じ公式配布物を事前導入
（Markdown Documents 0.1.2、CF7 6.2.5、Flamingo 2.6.4、ACF無料版6.8.11、TablePress 3.4.1、WP-Members 3.5.8.3）。

既存のSDKブローカーを再利用し、毎回新しいランダムな試験prefixを発行。中継側でもそのバケット・prefix以外を拒否。
書込みは`IfNoneMatch=*`と`AES256`を要求する新規作成限定。削除・上書き・本番バケットの操作は行わない。
WordPressへAWS認証情報を渡していない。ブローカーはSDKのみを読み込み、本番WordPressは起動・設定変更しない。

## 確認範囲

結果：両往復とも成功。4項目の試験は114個、TablePress等の試験は202個、計316個の書込み版を固定バージョンで再読取りし、すべて内容一致。本番バケットへの操作は両試験とも0件。変更した製品ソース4ファイルは、隔離環境の実行ファイルとローカルの取り込み対象でSHA-256が一致した。

1. Markdownの現在原文と過去版、元の.md名、独自項目名の問い合わせ、ACF説明・値を実S3へ保存。
2. 復旧後に標準の過去版差し戻しと派生ハッシュ、書き出し名生成、ACFの項目描画を確認。
3. CF7のsubmitからFlamingoへ実際に受信登録し、標準／独自項目名の氏名・メール・件名を確認。外部メールはスキップ。
4. ACFの項目定義・値とCF7フォームを通常APIで保存し、新しい初回保存を実S3へ作成。再復旧後も同じ利用確認。
5. 別の試験prefixで既存の往復フィクスチャを実行。TablePressのページ内表示・編集・再保存・再復旧と、HTML/Markdownの表示境界、会員・問い合わせ・ACFの既存確認を実施。
6. 各試験で書いた全オブジェクトを固定VersionIdで読み戻し、書込み時の内容ハッシュと照合。

確認結果は[4項目の往復](recovery-fields-s3-20261128/fields-result.json)、[S3照合](recovery-fields-s3-20261128/fields-s3-audit.json)、
[TablePress等の往復](recovery-fields-s3-20261128/integrations-result.json)、[そのS3照合](recovery-fields-s3-20261128/integrations-s3-audit.json)を参照。
TablePressフィクスチャ内の保存先比較はcreate-only中継の書込み版一覧を使用し、最後にホスト側で実S3から全固定版の本文を照合した。

## 保全・限界

本番サイト、既存原本・履歴、提出済みZIP・タグは不変。新しい公開ZIP・リリース・申請・審査メール返信は作成／実施していない。
試験は保存・復旧APIと通常の編集／描画／受信処理を使った。全ブラウザ画面操作、実メール配送、
保護オンの日常保存の正式履歴確定、community実データ全件の再確認へは拡大していない。
Markdown Documents 0.1.2の保存元側の差戻し後ハッシュの既知の観測は、[前記録の補足](recovery-fields-20261128.md)どおり別扱い。
今回の復旧済みサイトでは差戻し後もハッシュが一致する。0.1.3での確認と読み替えない。

提出済みZIPのSHA-256：`062a8c423c4ecca40b0075dc65d4d783e27ed884024fc66c5933f341e7de5447`。
検証用コンテナ・ネットワークだけを撤去し、試験S3資産と非公開記録は残す。

## English

Final review covers supported shortcode syntax, parent-bound Markdown revision sources, safe export names,
existing-field CF7 mappings and presentation-only ACF instructions. Storage/history formats and trusted-software
preparation remain unchanged. No third-party installation or initialization was added.

Two fresh random trial prefixes were used through an existing scoped real-S3 broker. An internal-only Docker
environment on dm received no AWS credentials. All writes were encrypted and create-only; production bucket
operations and deletions were excluded. Synthetic data was recovered, used, normally saved, recaptured and
recovered again. The second run also covered TablePress page rendering/editing and existing integration checks.
Every written object was read back at its fixed version and compared with the submitted bytes.

This is development-source evidence, not a new release or a production update. Submitted rc.23 and its tag
remain unchanged. Full interactive-browser coverage, external email delivery, protected daily-history commits
and a rerun of the complete community dataset are outside this check.
