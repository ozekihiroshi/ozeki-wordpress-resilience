## 検証範囲と公開ラインへの統合

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

2026-10-28、ACF無料版6.8.10・隔離WordPress7.1.3で、Gutenbergから試験投稿・固定ページを編集し、実S3の固定版原本照合・正式履歴確定、dm管理画面からのサイト全体復旧まで確認しました。基本15型の値・フィールドキー参照・get_field()の結果、および本文・タイトル・公開状態が保存元・S3原本・復旧先で一致しました。全型をブラウザで変更したわけではなく、初期値を維持した型も比較しています。最新ACF履歴は5と10で、Baseline through 0＋履歴10までを復旧しました。本文・記事付随情報・ACFは別履歴で、途中状態のACF履歴も生じます。画面保存1回＝履歴1件ではありません。

値・定義・参照は3つの独立したJSON原本です。未知設定は原本に残っています。未適用151項目には対象外ACF設定・型と試験WordPressのウィジェット等を含み、対応値の喪失件数ではありません。復旧先には同じソフトウェアを事前配置しており、ファイル書込み0件でした。プラグイン本体の新規配置試験ではありません。復旧入力はS3で元DBを参照しませんが、元サーバ自体は停止していません。

先行する隔離CLI・模擬S3試験ではBaseline、独立Checkpoint＋後続履歴、照合失敗、凍結した操作内容の再開を確認しています。失敗注入は実AWS障害ではなく、今回の実S3試験は正常系です。準備スクリプトのPHP重複読込み、ブラウザのメタボックス配置や一時応答遅延は試験基盤の事象として区別します。

このPRでは検証した研究アダプターを公開mainへ移し、導入確認・翻訳・パッケージ構成の既存改善を維持しています。統合後のオフライン契約試験を再実行します。実S3・ブラウザの証拠は研究ビルドに対するもので、新しいmain統合ビルドを実サイトへ配備した試験ではありません。公開済みZIP・リリース版番号は変更しません。マージ・公開判断は公開ラインの担当者が行います。

ACF取得はWordPressのフィールド保存後に行います。確定にはS3再取得照合と正式履歴が必要で、システム間トランザクションや無害性の保証ではありません。キュー登録後の失敗は明示的な履歴再開が必要です。登録前の取得失敗は既存の保存失敗表示に残り、再保存が必要になる場合があります。すべての失敗で再開可能な操作内容が残るわけではありません。

## 差し戻しへの修正と回帰確認（2026-10-28）

ACFメタデータ行の生成にWordPress標準のmaybe_serialize()を使うよう修正しました。a:0:{}などの文字列には外側の文字列エンコードを付け、WordPressが一度デコードすると原文へ戻ります。配列は配列の保存形式を維持します。SiteSnapshotの既存のデコード・URL再配置・再エンコードでも外側の型が保たれるため、共通の復旧形式は変更していません。

フィールド名は英数字・アンダースコア・ハイフンを許可し、固定フィールドキーの検証とは区別します。[ACF Field Settings](https://www.advancedcustomfields.com/resources/field-settings/)の説明に合わせています。

通常の日本語文字列・シリアライズ形式に見える文字列・配列・sub-titleと_sub-titleをオフライン回帰試験へ追加しました。既存dmの隔離WordPress7.1.3／ACF無料版6.8.10では、公開統合候補のcapture・replay・projectionとSiteSnapshotのデコード・URL再配置・再エンコード関数を通し、実DBへ格納してget_post_meta()とget_field()で確認しました。7ケースすべてで保存元のDBエンコード・読取り値・型が一致しました。記録はリポジトリのevidence-public/acf-free-20261028/review-regression.jsonです。これは保存・読取り経路の差分試験であり、全サイト復旧・ブラウザ・実S3の再試験ではありません。当初の広い試験は完了せず、合格には含めていません。試験引数処理と試験定義の重複は製品の問題と区別しました。既存S3資産・公開済みZIPは変更していません。今回の修正版へのPlugin Checkは公開担当者のレビュー項目として残し、過去のリリース結果を今回の合格として扱いません。
