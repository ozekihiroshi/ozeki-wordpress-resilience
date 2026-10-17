# Ozeki WordPress Resilience

WordPressが利用不能になっても、外部の復旧資産から事業に必要な情報と機能を取り戻すための基盤です。バックアップ機能を内包し、資産の組合せ、固定版取得、独立復元、復旧の証拠を管理する製品を目指します。既存のOzeki Database Backup for S3とは、共通バックアップ部品と保存形式を共有する方針です。

## 開発環境の準備

[初版のセットアップと検査](docs/guides/development-setup.md)を参照してください。GPL-2.0-or-laterで公開します。実環境の証拠原本・資格情報・AWS接続設定は配布に含めません。

## 現在の状態

2026年10月18日：Phase 5までの実行・評価を完了しました。元の模擬WordPress・DBを停止し、S3の固定版から新しいDockerボリュームへ2回復元して、各回DB・ファイル16項目とHTTP14項目に合格しました。初回RTOは約4分6秒です。

**Phase 3のIAM権限分離は未達です。** 今回は利用者の合意により保存・取得ともExampleSharedRoleを使用しています。また、同じWSLホストでの試験であり、ホストOS侵害・バックアップ汚染・署名による真正性は未検証です。本番向けの完成品ではありません。

- [M1最終評価](docs/m1/10-milestone-1-evaluation.md)
- [復元試験結果](docs/m1/08-recovery-test-results.md)
- [時間・費用](docs/m1/09-metrics-and-cost.md)
- [次の開発優先順位](docs/m1/11-next-milestone-recommendations.md)

## 初版公開と既存製品との関係

GitHub初版はM1研究・開発版として準備します。別バックアッププラグインを必須にせず、それぞれ単独で導入できる二製品が共通部品を使う構成を採用しました。現在のM1は既存製品の内部クラスを利用しており、共通部品への抽出・単独導入パッケージは未実装です。公開前の整理事項を含め、[責任分担と初版の位置づけ](docs/spec/04-product-boundaries-and-initial-release.md)に記録しています。

## 初めて使う方へ

[S3・IAM設定ガイド](docs/guides/s3-iam-setup.md)から進めてください。AWS管理画面での操作、EC2ロールによる認証、Versioning、確認コマンド、費用、AccessDeniedの切り分けを説明しています。長期アクセスキーをWordPressへ入力する方式は使いません。

今回の実験先は東京リージョンのowr-example-bucket/wordpress-test/です。保存用owr-writer、取得用dmという既存SSH環境を前提にした実証コードです。他の利用者がそのまま実行できる汎用インストーラーではありません。

[独立復旧手順](docs/m1/07-independent-recovery-procedure.md)と[固定版転送の開発手順](docs/guides/versioned-transfer-development.md)を参照してください。

## 現在の模擬サイト

[復元したサイト](http://localhost:18081/)は2回目の復元環境owr-m1-e3-2で動作しています。元環境owr-m1と初回復元環境owr-m1-e3-1は停止しています。元環境を起動するとポートが競合するため、現在は元環境のupコマンドを実行しないでください。

復元環境を停止する場合、Ubuntuのプロジェクトルートで次を実行します。ボリュームは削除しません。

    docker compose --env-file .local/e3-run-2/runtime.env -f .local/e3-run-2/compose.json stop

再起動は同じコマンドのstopをup -dに置き換えます。実験用の新しい資格情報は.local/e3-run-2/runtime.envに保存され、公開ドキュメントや証拠には含めません。

## プロジェクトと仕様

正式な保存先はD:\workspace\ozeki-wordpress-resilience、Ubuntuでは/mnt/d/workspace/ozeki-wordpress-resilienceです。開発・Docker実行はWSL Ubuntuを基本とします。既存バックアップ製品は別製品として維持し、そのコードは変更していません。

- [基本仕様](docs/spec/01-product-specification.md)
- [Milestone 1仕様](docs/spec/02-milestone-1.md)
- [未決事項と決定履歴](docs/spec/03-open-questions.md)
- [提供された作業指示書原文](docs/reference/milestone-1-instructions-v1.0.txt)
- [M1実証の設計判断](docs/adr/0003-m1-capture-and-shared-role-evaluation.md)

新しい発見は、採否・理由・仕様への影響を記録して取り込みます。過去の証拠は当時の観測として残し、後続の成功で書き換えません。

## 実装と証拠

- [RAMスキーマ](schemas/recovery-asset-manifest.schema.json) / [Recovery Setスキーマ](schemas/recovery-set.schema.json)
- [実S3の固定RAM](evidence-public/README.md) / [Recovery Set](evidence-public/README.md)
- [外部保管・取得のE2](evidence-public/README.md)
- [復元・動作確認のE3](evidence-public/README.md)
- [元の基準データ](docs/m1/04-baseline-data.md)
- [Phase 0調査](docs/m1/00-environment-inventory.md) / [既存機能](docs/m1/01-existing-backup-capabilities.md) / [不足分析](docs/m1/02-gap-analysis.md)
- [模擬環境](docs/m1/03-test-environment.md) / [メタデータBootstrap](docs/m1/05-recovery-bootstrap.md) / [保存の実測記録](docs/m1/06-backup-and-storage.md)

Python41件、転送PHP14件、一時認証PHP8件のオフライン試験にも合格しています。これらの試験と実S3・実復元の証拠は区別します。
## 共通部品への移行

- [単独導入と共通部品の設計決定](docs/adr/0004-standalone-products-shared-backup-components.md)
- [段階的な実装計画と完了条件](docs/spec/05-shared-backup-component-plan.md)

共通化後も、必要資産の判定や復旧成功の認定はResilienceが担います。既存製品との併用は初期の推奨構成とせず、どちらか一方を選ぶ運用と移行手順を整えます。