# メール通知・定期実行・監視停止の検知

通知方式はメール。通常監視と停止監視（watchdog）を別々に起動し、それぞれ独立した通知台帳とSMTP設定を持たせる。[日次監視](operations-monitor-lab.md)の判定・署名承認・復元条件は維持する。

## 構成と初期周期

- 通常監視：5分ごと。日次台帳と復元記録を読み、発生・解消をメール配送する。処理が正常終了した時だけ `heartbeat.json` を更新する。バックアップの異常を発見しても、監視が正常に動いた場合は更新する。
- 停止監視：1分ごと。heartbeatが15分以上更新されなければ `monitor_stopped` を通知する。再開後に新しい有効な記録を読めたら解消を通知する。検知時間は15分に次のwatchdog実行までの最大1分が加わる。
- 通常通知が未配送なら、watchdogが独立したSMTP経路で `notification_delivery_failed` を通知する。未送信メールは次の実行で再送する。
- heartbeatの破損・対象違い・5秒の許容差を超える未来日時・以前に観測した時刻より古い記録は異常。5秒の許容差は監視とwatchdogの並行実行中の記録時刻差を吸収する。停止中や読取り異常中に、既存の警報を勝手に解消しない。

開始直後にheartbeatがまだなければ15分の猶予を設ける。開始時刻はwatchdogの台帳へ保存し、再起動で猶予をやり直さない。watchdogを先に起動すれば、通常監視が一度も起動しなかった場合も検知できる。

## 通常監視の設定

WSL Ubuntuの運用担当側に `~/.config/owr/monitor.json` を作る。例のパス、メールアドレス、SMTPホストを実環境に合わせる。秘密情報はチャットへ貼らず、Gitにも追加しない。

```json
{
  "monitor_id": "isolated-queue-lab",
  "heartbeat_file": "/home/ozeki/.local/share/owr-scheduled-monitor/heartbeat.json",
  "monitor": {
    "site": "isolated-queue-lab",
    "start_day": "2026-10-19",
    "hour_jst": 3,
    "capture_grace_seconds": 7200,
    "pending_seconds": 86400,
    "daily_state": "/home/ozeki/.local/share/owr-daily-s3-lab-20261019",
    "restore_journal": "/home/ozeki/.local/share/owr-monitor-lab-20261019/restore-journal",
    "monitor_state": "/home/ozeki/.local/share/owr-scheduled-monitor/state"
  },
  "delivery": {
    "transport": "smtp_starttls",
    "host": "smtp.example.invalid",
    "port": 587,
    "from": "owr@example.invalid",
    "to": "operator@example.invalid",
    "timeout_seconds": 10,
    "credentials_file": "/home/ozeki/.config/owr/smtp-credentials.json"
  }
}
```

SMTP認証ファイルは `username` と `password` のJSON。WSLのLinuxファイルシステム上で所有者本人だけが読める通常ファイル（例 `chmod 600`）にする。Windowsドライブ上ではUnixパーミッションの意味が異なるため使用しない。認証不要の信頼されたリレーは `credentials_file` を省略できるが、実配送のTLS要件は同じ。

`smtp_starttls` はSTARTTLS必須、`smtp_tls` は接続開始からTLS（通常465）。どちらも証明書とホスト名を検証し、TLS失敗時に平文へ切り替えない。`smtp_test` は認証なしの数値ループバックアドレスだけで使える試験専用モード。

## 停止監視の設定

`~/.config/owr/watchdog.json`：

```json
{
  "monitor_id": "isolated-queue-lab",
  "heartbeat_file": "/home/ozeki/.local/share/owr-scheduled-monitor/heartbeat.json",
  "watchdog_state": "/home/ozeki/.local/share/owr-independent-watchdog/state",
  "stale_after_seconds": 900,
  "delivery": {
    "transport": "smtp_starttls",
    "host": "alternate-smtp.example.invalid",
    "port": 587,
    "from": "watchdog@example.invalid",
    "to": "operator@example.invalid",
    "timeout_seconds": 10,
    "credentials_file": "/home/ozeki/.config/owr/watchdog-smtp-credentials.json"
  }
}
```

watchdogには通常監視のSQLite台帳、バックアップ、署名鍵は不要。heartbeatの読み取りと、自身の台帳・通知経路だけを与える。同じSMTPサービス・同じ認証情報では配送経路の共通障害を検知できても、その経路で知らせられないため、独立したリレーを使う。

この専用試験は同じWSL内の別プロセス・別systemdユニット・別受信機で実施する。**WSLやPC全体が停止した場合の検知は保証しない。** 本番では常時稼働する別ホストにwatchdogを置き、そこへ安全にheartbeatを届ける経路と、そのwatchdog自体の外部監視を別途用意する。今回の実装のheartbeat入力はローカルファイルであり、別ホストへの同期・受信機構は未実装。

## 手動確認から定期実行へ

設定した宛先へ実際に送信されるため、最初は試験宛先を設定する。以下は手順であり、今回の試験で実運用宛先へは送信していない。

```bash
python3 tools/monitor-runtime-lab.py monitor --config "$HOME/.config/owr/monitor.json"
python3 tools/monitor-runtime-lab.py watchdog --config "$HOME/.config/owr/watchdog.json"
```

終了コード0は異常・未送信なし、2は監視完了かつ対応対象あり、1は処理自体の失敗。systemdは2を成功扱いにして定期実行を継続する。1、タイムアウト、強制終了ではheartbeatが更新されず、別のwatchdogが停止を検知する。重複起動はロックで拒否する。

[systemd設定例](../../examples/monitoring/)を確認し、実行パスと設定ファイルを配置してから使用する。

```bash
mkdir -p "$HOME/.config/systemd/user"
install -m 644 examples/monitoring/owr-monitor.* examples/monitoring/owr-watchdog.* "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now owr-watchdog.timer owr-monitor.timer
systemctl --user list-timers 'owr-*'
```

WSLからユーザーバスへ接続できない場合は `XDG_RUNTIME_DIR=/run/user/$(id -u)` と `DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus` を確認する。ユーザーマネージャーが起動していない場合は環境の管理者が設定を確認する。WSL停止中やPCスリープ中にタイマーは動かない。`Persistent=true` は再開後の取りこぼし実行用であり、停止中の稼働を保証しない。

停止は `systemctl --user disable --now owr-monitor.timer owr-watchdog.timer`。障害試験では通常監視のタイマーだけを止め、watchdogは動かしておく。停止すると通知が出るため、計画停止・抑制の運用は本番導入前に決める。

## メール配送の保証と障害対応

SMTPサーバーが受付を返した時点で配送済みと記録する。人による既読や、迷惑メール判定後を含む最終受信は保証しない。認証・接続・TLS・宛先拒否などの失敗ではoutboxに残し、次回の定期実行で再送する。イベントIDを `Message-ID` と本文へ固定して追跡する。

SMTPの受付直後に接続が切れた場合やプロセスが落ちた場合は、受付済みか判断できず再送することがある。したがってメールの完全な重複排除は保証せず、同じイベントIDのメールは同じ通知として扱う。以前のローカル受信箱が持つID単位の重複排除とは区別する。

生ログ、SMTP認証情報、秘密鍵、署名URLは通知本文へ含めない。配送先変更は未送信イベントの送り先にも反映されるため、変更前に未送信件数を確認する。監視用・watchdog用の台帳を削除して警報を消さない。プロバイダーの最終配送・バウンス確認、再通知・エスカレーションは今後の運用仕様とする。

## 実測結果（2026-10-19）

関連42件（追加18件・既存監視24件）が合格。実際の一時systemdタイマーと2つのローカルSMTP受信機で、周期実行、通常監視の停止検知、再開による解消、SMTP配送拒否の独立通知、復旧後の再送を確認した。試験用タイマー・サービス・受信機は停止済み。systemd設定例もLinux上の通常権限で検証した。実運用メールアドレス、SMTPサービス、別ホストのwatchdogは未設定。[検証記録](../../evidence-public/monitor-email-scheduling.json)。

## 実設定と別ホストへの導入計画

[SMTP実設定・別ホストwatchdog導入計画](monitor-production-setup-plan.md)に、必要情報、dmを候補とした配置、専用SSHによるheartbeat配送案、権限と導入時の合格条件を整理した。計画整理の段階では実メール送信・ホスト変更を行っていない。

別ホストへの生存記録配送は[dm専用SSH試験](dm-heartbeat-ssh.md)で実装・実測した。Googleメールとプッシュの選択は[通知方式の検討](notification-channel-decision.md)を参照。常設タイマーと実配送は未設定。
