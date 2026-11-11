# 0.3.3 rc.11 — GitHub公開候補（WordPress.org未提出）

提出済みrc.10は審査担当者の回答待ちであり、公開承認済みではありません。rc.11は次回の申請更新に備えた候補です。今回の作成・確認・GitHub公開だけではWordPress.orgへの送信を行いません。

## rc.10からの変更

- WP-Membersの会員項目で、通常の編集による真偽値の表示フラグ、選択肢、チェック時の値、区切り文字など、対応する項目を使うために必要な定義を復旧します。
- ACF無料版のDB定義の作成・変更・削除を、記事とは独立した正式履歴へ保存します。記事がなくても定義を保全します。後の記事履歴で古い定義へ戻しません。
- 日英の導入・更新手順とreadme.txtに、新しい定義履歴の確認方法と互換性を記載しました。
- 独立した適用契約・欠落照合は開発用です。配布ZIPには同梱しません。

既存の原本・正式履歴は書き換えません。既存の原本は更新版で読めます。新しいACF定義履歴と、それを含むBaseline・Checkpointにはrc.11以降の対応する復旧処理が必要です。旧版は新しい復旧点を拒否します。復旧先のWordPress・テーマ・プラグインは引き続き信頼できる配布元から別途準備します。

## 候補と確認結果

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.11/ozeki-resilience-0.3.3.zip) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.11/packages/markdown-m1)。ヘッダー・Stable tagは0.3.3、候補識別子はrc.11。
- 8,285,733 bytes / 3,813 files。SHA-256: `0fcbbac0a7e8dcadbbb5d5b247248a3c8081ceb1b4ee6c2771f7e19cc5233c1c`。
- [パッケージ監査](../../evidence-public/wordpress-org-033-rc11/package-audit.json): 製品ファイルは対応ソースと一致、vendor変更なし、同梱8ガイド・相対リンク78件が解決、開発資料・試験コードの混入なし。
- 最終ZIPを隔離WordPress 7.1.3 / PHP 8.3.36へ新規導入・有効化。全ファイル一致、別プロセスで管理画面の描画に成功。
- rc.10から通常のプラグイン更新を実施。設定・未確定状態・復旧結果のハッシュ、投稿件数、有効化状態を保持し、全配置ファイルがZIPと一致。キューは空であり、未確定操作を抱えた更新の実証とは区別。
- 既存の実S3履歴22件から会員・問い合わせ・表・記事を復旧し、次のプロセスで管理画面を描画。原本・履歴ハッシュ不変。不適合ACF値と参照は原本に残して未適用。
- 最終ZIPのコードでACF定義・凍結キュー・共通適用規則・会員履歴の回帰確認が合格。会員契約の欠落166件・URL境界10件を検出／照合。会員試験の初回は試験用ソース参照先不足で停止し、参照先を修正して再実行。製品修正は不要。
- Plugin Check 2.1.0: **エラー0 / 警告99**。[結果](../../evidence-public/wordpress-org-033-rc11/plugin-check.json)。rc.10とファイル・種別・コード・メッセージを重複込みで比較し差分0（行番号は除外）。既存警告の解消・審査承認を意味しない。
- [確認サマリー](../../evidence-public/wordpress-org-033-rc11/validation.json)。今回の導入・更新・復旧はCLI/APIであり、新たなブラウザ操作・タイムアウト試験ではない。

前段の実S3・管理画面・再保存／再復旧確認の範囲は[ACF取り込み記録](../review/acf-definition-history-20261111.md)、会員項目の背景と共通基準は[構築方針](../review/recovery-construction-policy-20261111.md)を参照してください。今回の結果で他のすべての対応データの確認が完了したとは扱いません。

## 保全と送信状態

- rc.10 ZIP SHA-256: `a762c181772ded58ac403ad520a731278c4c73ed91181d3326bd1cab6420acbf`。ZIP・タグは変更しません。
- 研究側の未コミット変更は含めません。
- **rc.11はWordPress.org未提出。メール返信も未送信。** 補足説明案は下記であり、受付記録ではありません。

## Draft supplementary explanation

This candidate retains the previous nonce and input-validation corrections. It adds complete supported WP-Members field definitions/flags for use after recovery and records ACF free database-definition changes independently of article saves.

Existing S3 originals and formal history are not rewritten. New ACF definition history and the Baselines/Checkpoints containing it require the updated recovery implementation; older readers reject those points rather than silently applying stale definitions. Administrators continue to install trusted WordPress, themes and plugins separately. Recovery does not deploy archived executable software.

Source, ZIP and verification: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.11
