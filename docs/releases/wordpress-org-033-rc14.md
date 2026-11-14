# 0.3.3 rc.14 — 復旧前の準備確認・公開候補

**状況更新（2026-11-14）：利用者からの送信完了報告に基づき、rc.14は提出済み・審査担当者の回答待ちです。公開承認済みではありません。以下は2026-11-12の準備時点の記録です。** community本番は、下記の検証済みrc.14 ZIPへ更新しました。

## 今回の変更

- 初回は保護をオフで設定保存し、保存先確認・初回保存と読み戻しの成功後に保護を開始する案内を日英で表示。バケット名欄を拡張。
- 選択した復旧点と正式履歴の終点について、言語パック・WordPress・必要なプラグインなどの不足条件と次の操作を表示。準備後に再確認可能。
- 実際の復旧でも同じ判定を実行し、準備不足なら復旧先の内容変更前に停止。保存した診断結果だけで復旧を許可しない。
- 日英ガイドを更新し、復旧先用の読み取り専用IAM JSONへ案内。

原本・正式履歴の形式変更、既存S3データの書換え、移行はありません。復旧先にも更新版を用意してください。以前のZIPは変更せず、rc.13以前では準備条件を手動で確認します。rc.12で導入した参照情報を持つ復旧点に対応readerが必要という従来の条件は変わりません。WordPress・テーマ・プラグインは信頼できる配布元から別途導入します。

## 完成ZIPの確認

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.14/ozeki-resilience-0.3.3.zip) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.14) / [リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.14)
- SHA-256: `453acc6930d57da11da72eaba5adf9c386d0d79aa179cfd15b12b82ad0ba5a2a`
- 8,293,047 bytes / 3,814 files。rc.13から製品PHP4ファイル・説明8ファイルが変更。vendor変更・削除ファイルなし。同梱8ガイドの相対リンク86件を照合。開発資料・試験コードの追加混入なし。[監査結果](../../evidence-public/wordpress-org-033-rc14/package-audit.json)。
- dmの使い捨てWordPress 7.1.3 / PHP 8.3.36。専用DB・内部ネットワーク、公開ポートなし、メール・Cron停止、AWS認証情報なし。
- ZIPの新規導入・有効化、提出済みrc.13からの通常置換が成功。更新前後それぞれ全3,814配置ファイルをZIPと照合し、余剰ファイルなし。設定・投稿・有効化状態・確認用の復旧結果が保持された。
- 別PHPプロセスで日英の管理画面描画と復旧準備の契約確認に成功。導入・更新はWP-CLI、画面はPHP描画であり、ブラウザからのアップロード試験ではない。
- Plugin Check 2.1.0：**エラー0／警告100**。rc.13と種類別件数が一致。[Plugin Check](../../evidence-public/wordpress-org-033-rc14/plugin-check.json) / [導入・更新結果](../../evidence-public/wordpress-org-033-rc14/validation.json)。

前段の[実S3復旧・不足条件確認](../../packages/markdown-m1/docs/recovery-preparation-check-20261112.md)では、同じ製品コードで言語パック不足・Flamingo未有効時の日英HTTP案内とデータ変更前の停止、準備後の再確認、communityの履歴5までの復旧と記事の追記表示、S3全278バージョン不変を確認済みです。これはrc.13に今回のソースを重ねた隔離試験です。今回の完成ZIP検証とは区別し、完成ZIPで実S3復旧を再実行したとは扱いません。

## 本番反映と保全

community本番（WordPress 7.1.4 / PHP 8.3.36）で、直前のDBとプラグインをサーバー内の非公開ディレクトリへ退避し、同じZIPへ更新。全3,814ファイルが一致しました。投稿・メタ情報・ユーザー・分類・コメントおよび対象設定のハッシュは更新前後で一致しました。保護はオン、GFS定期保存と自動削除はオフを維持しています。ホームHTTP 200、日英の管理画面描画も確認しました。問い合わせの追加送信や本番での復旧操作は実施していません。

[本番更新結果](../../evidence-public/wordpress-org-033-rc14/production.json) / [本番画面描画](../../evidence-public/wordpress-org-033-rc14/production-admin.json)。この記録に本番データ・認証情報・退避ファイルは含めません。

提出済みrc.13 ZIPのSHA-256は `34eee728e5c6d78f6e8368256d60676a0df7085e8a35ed343f787afd2898c2b8` のままです。既存タグ・研究側の未コミット変更を保全し、rc.14は別タグとして公開します。準備記録の時点ではWordPress.orgへのアップロードと審査メール返信は未実施でした。その後の提出状況は冒頭の更新を参照してください。

## Supplementary explanation

Ozeki Resilience 0.3.3 rc.14 retains the previous review-response fixes and adds clearer setup and recovery preparation guidance. Administrators can check the selected recovery point and confirmed-history end, see missing language packs or required software with next actions, prepare them from trusted sources, and recheck. The actual restore independently repeats these checks before changing destination content. It does not install archived software.

Existing originals and formal history are unchanged and require no migration. Update recovery destinations too. Initial-protection guidance and a wider bucket input are included in English and Japanese, with links to recovery IAM examples.

The exact ZIP passed isolated fresh installation, replacement of submitted rc.13, all-file/source checks, bilingual admin rendering and recovery preparation contracts. Plugin Check 2.1.0 reports 0 errors and 100 warnings, with the same per-code counts as rc.13. Earlier isolated real-S3 tests of the same product code confirmed missing-condition handling and successful recovery through history 5 after preparation; this was not a second real-S3 cycle with the final ZIP. The same ZIP is installed on community with existing content/settings preserved, protection on, scheduled checkpoints and automatic cleanup off.

This candidate is not yet submitted to WordPress.org. Submitted rc.13 remains awaiting the reviewer's response; publication is not approved.
