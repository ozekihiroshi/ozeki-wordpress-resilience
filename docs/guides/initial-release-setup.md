# 初版候補を試す手順

この版は開発・評価用。現在の専用環境で動かす手順と、実サイト導入時に必要な設定を分ける。実サイトへプラグインを入れるだけでは日次保護は始まらない。

プラグインZIPの導入手順は[専用ガイド](plugin-candidate-install.md)へ分離しています。以下は外部構成・継続試験を含む説明です。

実サイト向けの次期対応範囲は[最初のサイト構成と取得方式](../spec/13-first-site-capture-profile.md)、担当者の操作順は[導入から復旧まで](first-site-operator-runbook.md)を参照。未実装工程を実行済みとは扱わない。

## まず見るもの

1. [初版範囲](../releases/initial-release-readiness.md)で対象と未達を確認する。
2. [開発環境](development-setup.md)に従いWSL Ubuntu・Dockerを用意する。
3. 初回は実データを使わず専用生成データで行う。AWSを使う試験は[実S3実験設定](real-queue-s3-lab.md)のwriter/reader設定が済んだ環境だけで実行する。

## 配置する場所と権限

|場所|置くもの|置かないもの|
|---|---|---|
|専用WordPress|プラグイン、通知設定候補、要求待ちフォルダ、外部状態の読取りコピー|Pushover/SMTPキー、署名秘密鍵、AWS管理者資格情報|
|保存処理側|取得用の最小権限、日次台帳、writerの一時認証|復旧用ロール・署名秘密鍵・保持解除権限|
|署名担当側|候補の確認情報、署名鍵、独立公開ピン|保存元から変更可能な信頼の起点|
|復旧側|reader、独立公開ピン、隔離復元環境|保存先への書込み・削除権限|
|外部監視側|watchdog、通知キー、未配送台帳、SSH固定コマンド|WordPressから書換え可能な通知資格情報|

Linux秘密ファイルは担当実行ユーザー所有0600、私有状態は0700。状態取得用SSHと要求受付用SSHを分け、ホスト鍵を固定する。WP要求ディレクトリだけをWebユーザーと専用転送グループで共有する。[外部通知設定の具体手順](observer-settings.md)を参照。

## 今回こちらで実施する継続試験

大関さんにキーの貼付けや追加のAWS操作をお願いする手順ではない。既存の実験設定を使い、こちらで台帳と結果を確認する。

WSL内の日次台帳：`/home/ozeki/.local/share/owr-release-soak-20261019`。署名担当側：`/home/ozeki/.local/share/owr-release-soak-operator-20261019`。この2つを消して再試行しない。

今回の専用試験では10月19日・20日分は完了済み。次は10月21日03:00 JST以降に限る。実行中処理と台帳を先に確認し、running/unknownがあれば起動しない。以下は実施担当向けで、読者が並行して実行する手順ではない。現在の環境ではプロセス限定ネットワーク補助を使用する。

日次保存の手動起動（最大3保存セット、結果不明の再送は禁止）：

```sh
python3 /mnt/d/workspace/wp-rescue/release-readiness/with-process-network.py python3 /mnt/d/workspace/ozeki-wordpress-resilience/tools/daily-backup-lab.py tick --storage s3 --execute-lab --state-dir /home/ozeki/.local/share/owr-release-soak-20261019
```

変更しない台帳確認は今回の試験専用 `python3 /mnt/d/workspace/wp-rescue/release-readiness/progress.py` を使う。以下の製品開発用statusは中断したrunningをunknownへ評価するため、完全な読取り専用ではない：

```sh
python3 /mnt/d/workspace/ozeki-wordpress-resilience/tools/daily-backup-lab.py status --storage s3 --state-dir /home/ozeki/.local/share/owr-release-soak-20261019
```

`awaiting_approval` は保存成功・署名未承認。`approved` は承認取込み済みであり、復元成功は別の復元台帳で確認する。`failed` は事前失敗、`unknown` は処理結果不明。unknownは自動再送せず、元のログ・受領情報を照合する。詳細は[日次S3](daily-s3-approval.md)と[承認済みセット復元](approved-daily-restore.md)。

定期起動は今回のチャットの継続作業として設定し、最大3日次枠を超える新規保存をしない。WSL・PCが停止している間は動かず、欠測を記録する。後から過去日の成功を作らない。3枠だけ成功しても72時間の観測が済むまでは継続試験完了としない。

## 管理画面の確認

WordPress管理者で「Resilience → 通知」を開く。通常通知の状態とwatchdog・監視ホストの状態を見る。「Resilience → 独立watchdog」は外部通知先の候補保存・反映・テスト送信を行う場所。候補保存と反映済み、サービス受付と端末受信を分ける。5分以上古い外部報告は履歴として扱う。

初回はテストを1回送り、表示された要求IDと端末通知を照合する。[実機手順と実測結果](observer-pushover-device-test.md)。常設化前に[通常警報との統合試験](observer-runtime-integration.md)も確認する。

## 止める・再開する

今回の継続作業はCodexの該当フォローアップを停止する。実行中の保存・復元は可能なら完了まで待つ。強制停止した場合はunknown/失敗として残し、結果を照合する。停止してもS3保持資産・信頼情報・未配送台帳を削除しない。

systemdを常設導入する場合は、登録した専用timerを先に停止し、対応serviceの実行状態を確認する。既存FTP/MySQLや他の監視サービスを停止しない。再開は同じ設定・同じ台帳で行い、未配送が引き継がれたことを確認する。今回の作業で本番systemdサービスを有効化したとは扱わない。

## 実サイト導入へ進める条件

専用試験の合格後、実サイトの更新経路、停止時間帯、容量、担当・代替担当、承認期限更新、USB配布、期限後整理を別途確定する。本番鍵を日次処理へコピーしたり、未承認セットを承認済みにして導入を早めない。
