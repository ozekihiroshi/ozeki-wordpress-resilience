# Ozeki Resilience

対応するサイト内容をAmazon S3へ保存し、元のサイトが失われたり信頼できなくなったとき、準備したWordPressへ再構築します。

[English](README.md) | 日本語

**0.3.1（rc.2）は2026年10月26日にWordPress.orgへの申請が受け付けられました。** 現在は **審査待ち（Awaiting Review）** で、WordPress.orgでの公開承認・掲載はまだ行われていません。旧0.2.0申請候補を置き換えるもので、旧プラグインや外部処理キットは不要です。

## ダウンロードと導入

1. **[ozeki-resilience-0.3.1.zip](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.1-rc.2/ozeki-resilience-0.3.1.zip)** を取得し、[リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2)の `SHA256SUMS` と照合します。対応ソースも同じリリースから取得できます。
2. [初回導入ガイド（準備から保護開始まで）](docs/user-guide-ja.md)を読み、[AWS設定](docs/aws-setup-ja.md)を準備します。
3. ZIPを導入し、**ツール → Resilience** で設定、信頼できる初期Baselineを作成してから保護を有効にします。インストール・有効化だけでは保護は始まりません。

GitHubのソースアーカイブではなく、上記のインストール用ZIPを使います。実行時ライブラリは同梱しています。**Pythonワーカー、SSHヘルパー、外部処理キット、Docker、常時稼働する復旧サーバは不要です。** PHPからAWS SDK標準認証を使える環境が必要で、ガイドはEC2ロールを例にしています。AWSの利用料金は別途必要です。

## 必要環境と対応範囲

WordPress 6.4以上、PHP 8.1以上、ZipArchive、InnoDB、書込み可能な領域が必要です。最低版の宣言は全組合せの動作保証ではありません。バージョニング有効なS3バケット、専用prefix、必要なIAM権限を用意し、1つのprefixへ書き込むサイトは1つにします。復旧先には互換性のあるWordPress系列、記録された依存プラグイン、Web公開領域外の非公開一時領域が必要です。現在の操作画面は英語です。

**Markdownの依存条件：** Markdown未使用ならBaseline作成・復旧にMarkdown Documentsは不要です。有効なら収録し、文書や `_ozmd_source` 原文が残るのに無効なら保存前に停止します。Markdown復旧時は記録した互換版を事前に導入・有効化してください（確認版0.1.1）。

<a id="supported-content-and-plugins"></a>

| 対象 | 対応範囲 |
|---|---|
| 投稿・固定ページ | 本文、記録対象の属性、ゴミ箱・復元・削除、アイキャッチ、カテゴリー・タグ割当 |
| ローカル画像 | 対応する原本・参照ファイル・添付情報 |
| 標準コメント | 追加・編集・承認・削除 |
| Ozeki Markdown Documents | 原文と対応する関係情報。確認版0.1.1、必要時に別途導入 |
| Contact Form 7 / Flamingo | 対応するフォーム定義・受信情報。確認版6.2.3 / 2.6.4 |
| WP-Members | 基本購読者、認識する項目・設定・閲覧制限。確認版3.5.8.1 |
| TablePress | 基本テーブル、認識する設定・参照。確認版3.4.1 |

任意プラグインは別途導入します。確認済みのContact Form 7 6.2.3にはPHP 8.3以上が必要です。任意の拡張・すべてのメタ情報・外部CDN資源・全バージョンへの対応ではありません。原文は5 MiB、対応画像は32 MiBが上限です。[導入と対応範囲](docs/start-here-ja.md)を参照してください。

## 保存と復旧

管理者が信頼できる現在のサイトを最初の **Baseline** として保存します。その後の対応操作で原本と正式履歴をS3へ保存し、**Checkpoint** は保存済み資源から独立した復旧一式を作ります。現サイトの未追跡変更は発見しません。テーマ・実行プラグイン・追跡外の設定変更には新しい信頼済みBaselineが必要になる場合があります。

本文はWordPressへ反映する前に原本を保存します。コメントや一部の付随操作は反映後に記録するため、画面に見える変更でも未確定の場合があります。元サイト喪失後に復旧できるのは確定履歴までです。[未確定保存の手順](docs/save-resume.md)に従ってください。WordPressとS3を一括確定する仕組みではありません。

復旧は専用の復旧先の対応状態を置き換えます。**公開状態 `publish` を含めて保存済み状態を再現します。** 結果を確認し、ネットワーク公開・DNSは管理者が判断します。レプリケーション、マルウェア除去、サーバ自動構築、無条件の復旧保証ではありません。

任意の定期処理はWP-Cronの実行機会に依存します。保持プレビューは削除せず、自動削除には明示設定と削除権限が必要です。必要な固定版とアクセス権を保持し、有効化前に[利用ガイド](docs/user-guide-ja.md)を確認してください。

## 文書と問い合わせ

- [導入・更新](docs/install-update.md)：旧試験版フォルダーからの切替も記載
- [復旧手順](docs/site-snapshot-ja.md)・[よくある疑問](docs/recovery-faq-ja.md)
- [反映規則と反映しない情報](docs/application-rules.md)
- [外部送信とプライバシー](readme.txt)
- [申請候補の確認・構築手順](docs/wordpress-org-candidate.md)

[Issue](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues)にはZIP名・ハッシュ・操作・エラー・環境の版を記載し、認証情報や私有データを除いてください。既存の検証記録は、それぞれの版と環境についての証拠であり、追加の導入条件ではありません。

[ライセンス](LICENSE)。Ozeki Database Backup for S3とは独立した製品です。
