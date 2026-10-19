# Ozeki WordPress Resilience

> **試作・開発版 / Experimental prototype**
> このリポジトリは、WordPressの侵害・障害後の復旧を研究・開発するための公開基盤です。本番保護が完成した製品ではありません。
> インストール用ZIPは通知管理画面の試作版です。バックアップ取得・署名・復元・監視・通知配送には別の外部処理と設定が必要です。
> 開発への参加・検証を歓迎します。[開発の始め方](CONTRIBUTING.md)と[現在の機能・未達](docs/releases/plugin-candidate-scope.md)を確認してください。

WordPressが侵害や障害で利用不能になっても、復旧資産と復旧手段を残し、サイトを立て直すための基盤です。DB・ファイル・キューの取得整合性、外部保管、固定版の独立取得、署名検証、隔離復元を扱います。通知・watchdogは、その失敗や未完了を見落とさないための機能です。

**研究・開発版です。署名・ハッシュ一致は無感染の証明ではなく、復元成功も安全な本番再公開の承認ではありません。** インストールだけで日次保護が始まる完成版プラグインではありません。

## インストール用開発候補

`0.1.0-dev.1` は通知管理画面のインストール用候補です。[機能と配布構成](docs/releases/plugin-candidate-scope.md)・[ZIP導入と停止／再開](docs/guides/plugin-candidate-install.md)を参照してください。外部ツールは開発キットとして分けます。[公開候補の検証と制限](docs/releases/plugin-candidate-review.md)も参照してください。3日間の外部構成観測と、この候補の導入・配布準備は並行して進めます。

## 最初に読む

1. [初版の範囲・到達点・未達](docs/releases/initial-release-readiness.md)
2. [導入・起動・確認・停止・再開](docs/guides/initial-release-setup.md)
3. [開発環境](docs/guides/development-setup.md)と[ツール一覧](tools/README.md)
4. [検証記録の索引](evidence-public/README.md)と[侵害耐性の公開受入条件](docs/spec/07-cyber-resilience-release-gates.md)

## 現在確認できていること

以下はプラグイン本体と外部処理を含むプロジェクト全体の到達点です。今回の保存・復元試験は外部CLIと専用WordPress fixtureによるもので、プラグインのインストールから復旧までの受入試験ではありません。[検証対象の区別](docs/releases/initial-release-verification.md)と[環境・試験基盤メモ](docs/releases/initial-release-environment-notes.md)を参照してください。

|対象|確認範囲|手順・記録|
|---|---|---|
|取得整合性|専用WordPress/MariaDBで停止・排出・解除。HTTP・REST・cron・SSH・キューを制御し、不整合を拒否|[取得契約](docs/spec/11-capture-consistency-contract.md)、[キュー復旧](docs/guides/queue-recovery.md)|
|実S3保管|三資産を固定Version ID・35日保持で保存し、別ロールで取得|[実S3往復](docs/guides/real-queue-s3-lab.md)|
|日次処理と承認|保存成功と承認待ちを区別。二重保存を防ぎ、結果不明で自動再送しない|[日次S3](docs/guides/daily-s3-approval.md)|
|署名と復元|独立指定の公開鍵・文書ハッシュを検証し、固定版から隔離復元|[承認済みセット復元](docs/guides/approved-daily-restore.md)|
|実サイト候補|約458MB・12固定オブジェクトの隔離復元と基本表示を確認|[実サイト復元](docs/guides/signed-s3-candidate-restore.md)|
|独立信頼情報|PC管理の鍵、暗号化USBコピー、公開ピンの読戻し|[USB記録](evidence-public/usb-candidate-trust-copy.json)|
|監視・通知|取得漏れ・承認待ち・期限切れ・復元失敗、未配送、監視停止|[監視](docs/guides/operations-monitor-lab.md)、[通知健全性](docs/guides/notification-health-lab.md)|
|管理画面・watchdog|設定反映・テスト送信・状態表示。未配送と旧通知先の確認待ちを保持|[通知設定](docs/guides/observer-settings.md)、[処理統合](docs/guides/observer-runtime-integration.md)|
|通知実機|Pushover受付・iPhone受信・画面結果まで照合|[実機検証](docs/guides/observer-pushover-device-test.md)|

各記録の実験時点の結果であり、現在のAWS設定・サイト健全性の常時保証ではありません。実サイト全更新経路、汚染世代の選定、全権限取得経路、別担当者の復旧、資格情報の全面交換、再公開判断は未達です。Dockerを悪意あるコードの安全な実行環境として認定していません。

## 今回の初版整備

1. 現状の棚卸しと初版範囲を確定。
2. 導入・定期起動・停止・再開の手順を統合。
3. 新しい専用セットで取得→実S3固定版→独立試験署名→隔離復元を検証。
4. 3日次枠・72時間以上を観測し、欠測・承認待ち・停止・通知失敗・容量変化を確認。
5. 結果と既知の制限をそろえ、GitHubの研究・開発版候補として整備。

継続試験は進行中です。72時間の実測が終わる前に全項目完了とは表示しません。[初版判定表](docs/releases/initial-release-readiness.md)を参照。以前の開発履歴は[運用化計画](docs/spec/10-operationalization-plan.md)に保持します。

初回実サイト候補の署名期限は2026年10月25日18:15:47（日本時間）。期限切れ時の検証省略は禁止です。今回の試験鍵による承認は、その候補の承認更新ではありません。

## Ozeki Database Backup for S3との関係

両製品は単独導入を目指し、他方の自動インストールや必須依存は採用しません。従来製品にも復旧関連機能があり、単に「保存だけの製品」とは説明しません。

- `packages/backup-core` が共通PHP DBダンプ部品の保守元。利用側は固定版を取り込み、契約試験で互換性を確認します。
- Resilienceはサイト全体の資産の組合せ、保持、独立検証、信頼情報、復旧判定を担当します。
- MariaDB CLIによるストリーム取得の共通部品統合と、旧バックアップ形式の互換読込みは未完成です。

[責任分担](docs/spec/04-product-boundaries-and-initial-release.md) / [共通部品計画](docs/spec/05-shared-backup-component-plan.md) / [共通部品契約](docs/spec/06-backup-core-contract.md)

## 開発と公開

開発・Docker実行はWSL Ubuntuを基本とします。今回の環境は `D:\workspace\ozeki-wordpress-resilience`（WSL: `/mnt/d/workspace/ozeki-wordpress-resilience`）。実験用アカウント・バケット・SSH名を他サイトへそのまま転用しないでください。

資格情報・取得物・実行時の秘密情報はGitへ入れません。公開集計は署名された原本そのものではありません。過去の実測記録と既存タグ `v0.1.0-alpha.3` は保持し、現在の作業ツリーの成果と区別します。新タグを公開済みとは扱いません。

- [利用開始](docs/guides/getting-started.md) / [基本仕様](docs/spec/01-product-specification.md)
- [保管仕様](docs/spec/08-production-backup-storage.md) / [S3・IAM設定](docs/guides/production-storage-setup.md) / [容量・費用](docs/spec/09-initial-site-and-cost-estimate.md)
- [通常通知の画面](docs/guides/wordpress-notification-admin-lab.md) / [設定切替](docs/guides/notification-live-switch.md)
- [SSH転送](docs/guides/notification-transfer.md) / [定期実行](docs/guides/notification-runtime.md)
- [独立観測](docs/guides/watchdog-observer.md) / [状態表示](docs/guides/observer-admin-status.md)
- [M1評価](docs/m1/10-milestone-1-evaluation.md) / [M1合成資産の復旧](docs/m1/07-independent-recovery-procedure.md)

ライセンス：GPL-2.0-or-later。
