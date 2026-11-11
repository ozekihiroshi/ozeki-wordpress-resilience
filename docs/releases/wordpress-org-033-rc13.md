# 0.3.3 rc.13 — 更新受付・返信完了、審査担当者の回答待ち

Flamingoの復旧時に受信値が欠落する問題を修正した公開候補です。**申請者からrc.13のWordPress.org更新受付と元の審査メールへの返信完了の報告を受けました。審査担当者の回答待ちであり、公開承認済みではありません。**

## 変更と互換性

各受信の項目名から必要な値の適用規則を組み立て、Flamingoでの閲覧・再保存・再復旧につなげます。未知のメタデータを一括許可する変更ではありません。原本保存処理・形式・正式履歴に変更はなく、既存原本の移行や書換えは不要です。欠落した状態で再保存した受信は、値が残る以前の原本から復旧します。復旧先にも更新版を用意してください。

rc.12までの修正を含みます。参照情報を持つ原本・Baseline・Checkpointにはrc.12以降の対応readerが必要という既存の条件は変わりません。WordPress・テーマ・プラグインは信頼できる配布元から別途導入します。

[修正・見逃し原因・再発防止・実S3での前段確認](../../packages/markdown-m1/docs/flamingo-recovery-fix.md)。前段では初期保存と正式履歴からの復旧、実管理画面、標準save()、追加受信、第三サイトへの再復旧、旧原本の互換性を確認しました。今回のZIP確認と区別し、今回新しい実S3復旧サイクルを再実行したとは扱いません。

## 最終ZIPの確認

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.13/ozeki-resilience-0.3.3.zip) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.13) / [GitHubリリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.13)。ヘッダーとStable tagは0.3.3、候補識別子はrc.13。
- SHA-256: `34eee728e5c6d78f6e8368256d60676a0df7085e8a35ed343f787afd2898c2b8`
- 8,289,284 bytes / 3,814 files。変更は製品PHP 2ファイルと説明4ファイル。vendor変更なし。同梱8ガイド・相対リンク80件を確認し、開発資料・試験コードの混入なし。[パッケージ監査](../../evidence-public/wordpress-org-033-rc13/package-audit.json)。
- WordPress 7.1.3 / PHP 8.3.36。ローカル専用DB・ボリューム・内部ネットワーク、ポート非公開、メール・Cron停止。community本番・既存S3には接続しません。
- 最終ZIPの新規導入・有効化成功。全3,814配置ファイルのハッシュが一致し、余剰ファイルなし。別PHPプロセスで管理画面描画成功。
- 更新前が提出済みrc.12の全3,814ファイルと一致することを確認し、WP-CLIの通常置換で更新。更新後はrc.13の全ファイルと一致。設定値・有効化状態・投稿4件が維持され、記録した状態ハッシュが一致。未確定操作・復旧結果は未記録のため、それらが存在する更新の実証とは区別します。
- 最終ZIPのコードで既存適用規則とFlamingoの実効値・欠落検出・旧形式の契約確認が成功。形式確認はメモリS3。導入・更新はCLI、管理画面は別プロセス描画で、ブラウザからのアップロード試験ではありません。
- Plugin Check 2.1.0：**エラー0／警告100**。rc.12と種別別件数も一致。[結果](../../evidence-public/wordpress-org-033-rc13/plugin-check.json)。警告ゼロ・審査承認とは扱いません。
- [確認サマリー](../../evidence-public/wordpress-org-033-rc13/validation.json)。外向き通信を遮断しているため、導入時のWordPress更新サービスへの接続警告は試験環境によるものです。導入・有効化・更新自体は成功しています。

## 保全と次の手順

本番サイト・既存原本・履歴・研究側の未コミット変更は変更していません。提出済みrc.12のZIPとタグを保全しています。rc.12 ZIP SHA-256: `8084a992fb593a65ca239fc8dc5b30b01061237424d768f106a2d1c63788ac6b`。

communityの空き容量が少ないため、新しい試験負荷を加えずローカルに分離しました。communityで次の大きな試験を行う前には容量確保が必要です。

**申請者によるrc.13のアップロード受付・審査メール返信が完了しました。** 受付・送信完了は本チャットでの申請者からの報告を根拠に記録しています。エージェントによる受付画面・送信済みメールの独立確認ではありません。

## Supplementary explanation / 申請用補足案

Ozeki Resilience 0.3.3 rc.13 retains the previous review-response fixes and corrects missing Flamingo receipt values during recovery. Only values declared by each receipt's field map are applied through the existing data validation; arbitrary metadata is not admitted.

Existing S3 originals and formal history are unchanged and need no migration. A receipt already re-saved with missing values must be recovered from an earlier original that still holds them. Administrators continue to install trusted WordPress, themes and plugins separately; recovery does not deploy archived executable software.

Earlier isolated real-S3 checks verified restored receipt viewing, standard resaving, new submissions and recovery into a third site, including compatibility with pre-fix originals. The exact rc.13 ZIP separately passed fresh installation, replacement of submitted rc.12, file/source checks and the Flamingo regression contract. Plugin Check 2.1.0 reports 0 errors and 100 warnings, with the same per-code counts as rc.12. The author confirmed rc.13 upload acceptance and sending the reply to the original review email. We are awaiting the reviewer's response; publication is not approved.

## 更新受付・返信完了の記録

申請者が手動でrc.13を既存申請へアップロードし、元の審査スレッドへ返信したことを、本チャットで報告しました。画面操作ツールがURLを確認できず操作を停止したため、エージェントが送信・受付確認を行ったとは扱いません。

今回更新するのはmain上のREADME・配布状況・申請記録とGitHubリリースの説明だけです。提出済みrc.13および以前のZIP・タグ・対応ソースは変更しません。タグ内文書・ZIP内README・ビルド時の確認サマリーの未提出表記は作成時点の記録として残り、現在の申請状態はmainの本記録とリリース説明を参照してください。

The author manually uploaded rc.13 to the existing application and replied in the original review thread, then confirmed both actions in this chat. This status relies on that confirmation, not an independent inspection of the receipt or sent email. The submitted ZIPs, tags and matching source remain unchanged. Packaged/tagged documents and build-time validation retain their original status; current submission status is recorded here on main and in the release description.
