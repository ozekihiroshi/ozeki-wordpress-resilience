# Ozeki WordPress Resilience

> **試作・開発版 / Experimental prototype**
> このリポジトリは、WordPressの侵害・障害後の復旧を研究・開発するための公開基盤です。本番保護が完成した製品ではありません。
> インストール用ZIPは通知・日次バックアップ・復元・独立監視の状態を扱う管理画面の試作版です。バックアップ取得・署名・復元・監視・通知配送には別の外部処理と設定が必要です。
> 開発への参加・検証を歓迎します。[開発の始め方](CONTRIBUTING.md)と[現在の機能・未達](docs/releases/plugin-candidate-scope.md)を確認してください。

WordPressが侵害や障害で利用不能になっても、復旧資産と復旧手段を残し、サイトを立て直すための基盤です。DB・ファイル・キューの取得整合性、外部保管、固定版の独立取得、署名検証、隔離復元を扱います。通知・watchdogは、その失敗や未完了を見落とさないための機能です。

**研究・開発版です。署名・ハッシュ一致は無感染の証明ではなく、復元成功も安全な本番再公開の承認ではありません。** インストールだけで日次保護が始まる完成版プラグインではありません。

## インストール用開発候補

`0.1.0-dev.1` は管理画面のインストール用候補です。[機能と配布構成](docs/releases/plugin-candidate-scope.md)・[ZIP導入と停止／再開](docs/guides/plugin-candidate-install.md)を参照してください。外部ツールは開発キットとして分けます。[公開候補の検証と制限](docs/releases/plugin-candidate-review.md)も参照してください。3日間の外部構成観測と、この候補の導入・配布準備は並行して進めます。

## 最初に読む

1. [現在の到達点と残課題](docs/releases/current-status.md)／[初版判定](docs/releases/initial-release-readiness.md)／[外部設定作成と導入計画](docs/guides/external-deployment-plan.md)
2. [導入・起動・確認・停止・再開](docs/guides/initial-release-setup.md)
3. [開発環境](docs/guides/development-setup.md)と[ツール一覧](tools/README.md)
4. [検証記録の索引](evidence-public/README.md)と[侵害耐性の公開受入条件](docs/spec/07-cyber-resilience-release-gates.md)

次の実装対象：[最初のサイト構成と取得方式](docs/spec/13-first-site-capture-profile.md)／[導入から復旧までの担当者操作](docs/guides/first-site-operator-runbook.md)。実装済み操作と未実装工程を区別しています。

新規の[収集設定検査と取得アダプター](docs/guides/first-site-capture-lab.md)を専用生成環境で検証しました。限定構成でS3保管・署名・隔離復元と日次状態表示まで専用環境で検証済みです。実サイトへの統合導入は未完了です。既存の72時間観測と配布候補は変更していません。

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

2026年10月21日時点で3日次枠は完了、72時間観測は継続中です。最短到達は10月22日15:55:56 JST。既知の2つの観測空白を保持し、日次成功・実経過・観測網羅性を別々に評価します。[現状一覧](docs/releases/current-status.md)を参照してください。

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

共通DB部品の既存製品への採用は別途追跡しています。[採用状況と残作業](docs/releases/shared-core-adoption-status.md)。

## 個別機能の開発記録

以下は開発時点の記録です。後の実装で解消された課題を含むため、現在の判定には[現状一覧](docs/releases/current-status.md)を使います。

2資産の取得から実S3固定版・保持確認・試験署名・新規隔離WordPressへの復元を専用環境で確認しました。[手順・信頼境界・制限](docs/guides/first-site-s3-recovery-lab.md)。既存72時間観測、公開ZIP、共通部品とは別の検証です。

取得中の停止確認タイムアウトを専用環境で再現し、Docker出力の読み取りを継続する修正と確認間隔の修正を行いました。[原因・比較試験・修正後の検証](docs/guides/first-site-timeout-investigation.md)。

二資産取得アダプターの[日次接続と署名承認待ち](docs/guides/first-site-daily.md)を専用環境向けに追加しました。固定版保存完了と独立承認を分け、同日重複・途中停止・送信結果不明を扱います。既存の三資産72時間観測とは別の台帳です。実サイト用スケジューラーや管理画面への統合は未完了です。

承認済み日次セットからの[固定版取得・隔離復元](docs/guides/first-site-daily-restore.md)も専用生成環境で確認しました。保存元の作業ファイルを使わず、独立保管した署名文書とS3二資産から新規WordPressへ復元します。復元結果は保存時の承認記録と分けて保管します。

[日次状態への復元結果集約](docs/guides/first-site-daily-status.md)により、保存完了・署名承認待ち・承認済み・復元検証済みをCLI/JSONで区別できます。復元観測は明示登録で追記し、元の承認記録を上書きしません。失敗・期限切れ・証拠不整合も表示します。

[隔離復元からの結果自動登録](docs/guides/first-site-auto-recovery.md)を専用ワーカーで実装しました。復元結果と登録状態を分離し、登録失敗時は再復元せず登録だけ再試行します。途中停止は結果不明として保持し、同じ要求の重複実行を防ぎます。

途中停止後の明示的な確認・後片付け・新規要求への移行は、[隔離復元の後片付け手順](docs/guides/first-site-recovery-cleanup.md)を参照してください。生成データ専用CLIで実装・検証済みです。

日次バックアップ・隔離復元・途中停止後の後片付け履歴は、[読取り専用管理画面](docs/guides/daily-admin-status.md)で確認できます。専用環境での試作機能です。

日次・復元状態の[実ブラウザ検証結果](docs/guides/daily-admin-browser.md)：権限・読取り専用性と通常幅／狭い幅の表示を専用環境で確認しています。

状態報告の[定期更新・SSH受渡し](docs/guides/daily-status-periodic.md)は生成側とWordPress側を分離し、転送失敗と更新停止を表示します。専用環境で検証済み、本番配置は未実施です。

専用環境での日次状態報告のsystemd停止・再開（実時間5分以上）と管理画面の回復は、[定期状態報告の検証範囲](docs/guides/daily-status-periodic.md#検証範囲)を参照してください。本番常駐・別物理ホスト検証とは区別しています。

[本番向けsystemd設定・権限・OS再起動の検証と導入手順](docs/guides/daily-status-systemd-production.md)を追加しました。専用Ubuntu VMでの確認であり、本番環境への配置は含みません。

[生成・取得を別VMに分けた通信断・片側停止・再起動後の回復試験](docs/guides/daily-two-vm-recovery.md)を追加しました。独立した2台のVMで確認しており、物理ホストは共通です。

[日次状態報告の独立watchdogと警報・回復通知](docs/guides/daily-watchdog.md)を追加しました。2台VMの通信断・OS停止とローカル通知先への配送・再送を検証し、物理ホスト全体の障害と実機プッシュ受信は対象外です。

[生成側・取得側の独立watchdog管理画面](docs/guides/daily-watchdog-admin.md)で、状態・警報発生と解消履歴・配送集計を読取り専用で確認できます。専用環境で検証済み、本番配置は未実施です。

[独立watchdog報告の定期受渡し](docs/guides/observer-status-relay.md)を追加しました。専用環境の実SSHで転送失敗・watchdog更新停止・取得停止と管理画面の回復を確認しています。

[独立watchdog報告転送のsystemd・OS再起動検証](docs/guides/observer-status-systemd.md)を追加しました。専用Ubuntu VMで60秒周期、停止・再開、OS再起動後の自動起動と管理画面の回復を確認しています。

状態報告・定期転送のZIP導入・更新と保持対象は[配布ガイド](docs/guides/status-report-zip.md)を参照。検証済み候補は `dist/candidate-20261021-status-validated`（試作版、未公開）。

[2026-10-21初版候補レビュー](docs/releases/initial-candidate-review.md) / [検証済み固定ZIP](release-candidates/20261021/README.md)。72時間観測の最終判定とは独立した試作版です。

導入前の設定・棚卸し・作業領域は[読取り専用検査](docs/guides/deployment-preflight.md)で確認できます。実ホストやIAMの自動検査・本番適用承認ではありません。

[ホスト上の読取り専用棚卸し](docs/guides/host-inventory.md)を導入前検査へ接続できます。実測できない停止制御・外部依存等は未確認のまま表示します。

SSHによる取得と権限制限は [SSH棚卸し手順](docs/guides/host-inventory-ssh.md) を参照してください。

検査結果の読取り専用表示は [導入前検査の管理画面](docs/guides/preflight-admin.md) を参照してください。

SSH棚卸しの定期実行と受渡しは [導入前検査の定期更新](docs/guides/preflight-relay.md) を参照してください。

導入前検査側とWordPress側を分離する場合は、[固定コマンドSSHによる結果受渡し](docs/guides/preflight-two-vm.md) を参照してください。元の検査時刻を保持し、通信失敗と検査側の更新停止を区別します。

導入前検査の通信断・処理停止を独立監視する構成は [導入前検査watchdog](docs/guides/preflight-watchdog.md) を参照してください。日次バックアップの監視とは対象を分け、既存の通知基盤を再利用します。

独立監視の状態・警報と回復の履歴は [導入前検査watchdogの管理画面](docs/guides/preflight-watchdog-admin.md) で確認できます。既存の読取り専用表示を再利用しています。

導入前検査watchdogの実報告を管理画面へ定期反映する手順は [状態報告の定期受渡し](docs/guides/preflight-observer-relay.md) にあります。

導入前検査watchdogの状態転送を常駐化する手順は [systemdによる停止・再開と自動起動](docs/guides/preflight-observer-systemd.md) にあります。

導入前検査・独立watchdogを含む最終試作ZIPは `dist/candidate-20261021-preflight-validated`。 [導入・更新ガイド](docs/guides/preflight-zip.md) と [新規導入・更新・状態保持の検証結果](evidence-public/preflight-zip.json) を参照してください。72時間観測・公開の判定は別です。
