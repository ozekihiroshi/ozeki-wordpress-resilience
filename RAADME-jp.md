# Ozeki Resilience

**開発版について：** 現在のソースは `0.3.2-dev` です。[セットアップ前の確認画面と利用条件の確認欄](packages/markdown-m1/docs/setup-readiness-ja.md)を追加しています。申請済みの `0.3.1 rc.2` ZIPは変更していません。

サイバー攻撃でサイトが使えなくなっても、積み重ねた記事や画像、問い合わせなどを失わず、情報発信や業務を再開するために。Ozeki Resilienceは、対応するコンテンツを保存し、別のWordPressへ復旧する道を用意します。

[English](README.md) | 日本語

**0.3.1（rc.2）は2026年10月26日にWordPress.orgへの申請が受け付けられました。** 現在は **審査待ち（Awaiting Review）** で、WordPress.orgでの公開承認・掲載はまだ行われていません。旧0.2.0申請候補を置き換えるもので、旧プラグインや外部処理キットは不要です。

## 攻撃の後も、サイトを再開するために

サイトを失っても、そこに積み重ねた情報や利用者とのつながりまで失わないために。Ozeki Resilienceは、記事・画像・コメントや、対応する問い合わせ・会員情報を残し、別のWordPressへ復旧して情報発信や業務を再開するための製品です。

バックアップ・リストアは、サイトを取得時点の状態へ戻すための備えです。Resilienceは、**攻撃を受けた元サイトをそのまま戻せないときにも、活動の再開に必要な内容を復活させるための備え**です。元の環境を丸ごと引き継ぐことより、守る価値のある内容を残して使えるようにすることを重視します。

残す対象は、業務上の価値と、安全に扱って復旧するための負担を踏まえて定めています。下の表で、保存・復旧する内容と、復旧先で別に用意するものを確認できます。

## ダウンロードと導入

1. **[ozeki-resilience-0.3.1.zip](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.1-rc.2/ozeki-resilience-0.3.1.zip)** を取得し、[リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2)の `SHA256SUMS` と照合します。対応ソースも同じリリースから取得できます。
2. [初回導入ガイド（準備から保護開始まで）](packages/markdown-m1/docs/user-guide-ja.md)を読み、[AWS設定](packages/markdown-m1/docs/aws-setup-ja.md)を準備します。
3. ZIPを導入し、**ツール → Resilience** で設定、信頼できる初期Baselineを作成してから保護を有効にします。インストール・有効化だけでは保護は始まりません。

GitHubのソースアーカイブではなく、上記のインストール用ZIPを使います。実行時ライブラリは同梱しています。**Pythonワーカー、SSHヘルパー、外部処理キット、Docker、常時稼働する復旧サーバは不要です。** PHPからAWS SDK標準認証を使える環境が必要で、ガイドはEC2ロールを例にしています。AWSの利用料金は別途必要です。

## 必要環境と対応範囲

WordPress 6.4以上、PHP 8.1以上、ZipArchive、InnoDB、書込み可能な領域が必要です。バージョニング有効なS3バケット、専用prefix、必要なIAM権限を用意し、1つのprefixへ書き込むサイトは1つにします。復旧先には互換性のあるWordPress系列、記録された依存プラグイン、Web公開領域外の非公開一時領域が必要です。現在の操作画面は英語です。

**Markdownの依存条件：** Markdown未使用ならBaseline作成・復旧にMarkdown Documentsは不要です。有効なら収録し、文書や `_ozmd_source` 原文が残るのに無効なら保存前に停止します。Markdown復旧時は記録した互換版を事前に導入・有効化してください（確認版0.1.1）。

<a id="supported-content-and-plugins"></a>

## 残るもの・復旧できるもの

保護開始後に保存が完了した内容を、選んだ復旧時点まで戻します。連携機能は、表に記載したプラグインが対象です。

| 残すもの | 復旧できる内容 |
|---|---|
| 投稿・固定ページ・ローカル画像 | 本文、対応する画像、公開状態、カテゴリー・タグ、アイキャッチなど、記事として使うための内容と関連情報 |
| 標準コメント | コメントと承認状態。保存した編集・削除の結果も反映 |
| Markdown文書 | 原文と対応する関係情報。Ozeki Markdown Documents 0.1.1 |
| 問い合わせフォームと受信情報 | フォームと届いた問い合わせ。Contact Form 7 6.2.3 / Flamingo 2.6.4 |
| 会員向けの情報提供 | 基本購読者の会員情報と、対応する項目・設定・閲覧制限。WP-Members 3.5.8.1 |
| 表 | 表の内容、対応する表示設定と参照。TablePress 3.4.1 |
| 初期保存に含まれるサイトの見た目 | 選択したテーマと対応する表示設定。後からテーマなどを変更した場合は、新しい初期保存へ取り込みます |

連携プラグインは必要なものを別途導入します。上記は確認済みの版です。Contact Form 7 6.2.3はPHP 8.3以上が必要です。原文は5 MiB、対応画像は32 MiBまでです。

<a id="製品が確認する範囲"></a>

## 復旧に含めないものと、その理由

コンテンツを残すことと、元サイトの権限や実行環境を丸ごと引き継ぐことを分けています。

| 復旧に含めないもの | 理由・扱い |
|---|---|
| 元サイトの管理者ログイン、ログイン中の状態、AWSやメール接続の秘密情報 | 元環境の管理権限や接続情報を持ち戻さず、復旧先で用意したものを使うため。対応する基本購読者の会員情報は上の表の対象です |
| サーバ・PHPの設定、DNS、外部サービスやCDNの資源 | 復旧先や外部サービスの管理に属するため。それぞれの設定・保護手順を用意します |
| 対応表にないプラグイン固有の機能・データ、任意の独自設定 | 個別の仕組みを安全に復旧するには専用の対応が必要なため。現在の製品は上の対応範囲に集中しています |
| 保存されていても扱い方が定まっていない設定 | 不明な動作まで持ち戻さないため、自動では適用せず結果に表示します。保存済みの情報はS3に残ります |

対象外の資産は、バックアップや各サービスの保護手段で補います。Resilienceは、サイトの活動を再開するための保存・復旧を担います。

## 保存から業務再開まで

1. 信頼できるサイトの初期状態を **Baseline** として保存し、保護を開始します。
2. 日々の対応する変更を保存します。**Checkpoint** は、それまでに保存した内容から作る復旧点です。テーマなどの変更時は、[変更後の手順](packages/markdown-m1/docs/start-here-ja.md)に従います。
3. 必要になったら別のWordPressを用意し、初期保存または復旧点と、戻す変更の範囲を選びます。
4. 記事・画像・問い合わせなど必要な内容と、復旧結果に表示された未適用項目を確認し、公開して業務を再開します。

保存完了は **Save protection status** で確認できます。未確定の操作があれば[保存再開の手順](packages/markdown-m1/docs/save-resume.md)へ進みます。復旧では保存済みの公開状態も戻るため、確認中の復旧先は外部公開を制限します。攻撃への対応では、信頼できる初期保存と、採用する変更の範囲を選んでください。

定期取得・保存期間・削除の設定は[利用ガイド](packages/markdown-m1/docs/user-guide-ja.md)にまとめています。復旧時の扱いは[よくある疑問](packages/markdown-m1/docs/recovery-faq-ja.md)を参照してください。

## 文書と問い合わせ

- [利用条件](packages/markdown-m1/docs/terms-of-use-ja.md)：ライセンス、運用上の役割、データ・費用、保証と責任
- [導入・更新](packages/markdown-m1/docs/install-update.md)：旧試験版フォルダーからの切替も記載
- [復旧手順](packages/markdown-m1/docs/user-guide-ja.md#6-別のwordpressへ復旧する)・[よくある疑問](packages/markdown-m1/docs/recovery-faq-ja.md)
- [反映規則と反映しない情報](packages/markdown-m1/docs/application-rules.md)
- [外部送信とプライバシー](packages/markdown-m1/readme.txt)
- [申請候補の確認・構築手順](packages/markdown-m1/docs/wordpress-org-candidate.md)

[Issue](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues)にはZIP名・ハッシュ・操作・エラー・環境の版を記載し、認証情報や私有データを除いてください。既存の検証記録は、それぞれの版と環境についての証拠であり、追加の導入条件ではありません。

[ライセンス](LICENSE)。Ozeki Database Backup for S3とは独立した製品です。

セットアップ支援の検討資料：[条件判定の現状整理](packages/markdown-m1/docs/setup-preflight-review-ja.md)（未実装の追加案を含む）。
