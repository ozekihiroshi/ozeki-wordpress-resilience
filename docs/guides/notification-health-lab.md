# 通知設定と配送健全性の専用環境試験

2026-10-19。[利用者向け設定仕様](../spec/12-notification-settings-and-health.md)を参照。WordPress設定画面は未実装。既存の個人用Pushover設定や実機試験用DBはこの作業で実行・変更しない。

## 作成する記録

`notification-dispatch-lab.py`を正常完了すると、その`state`ディレクトリに以下を生成する。

- `delivery-health.json`：完了時刻、宛先ID別の問題、事件ID、閾値。キー、宛先アドレス、receipt、APIエラー本文は含まない。
- `delivery-heartbeat.json`：既存watchdogが読める生存記録。未解消の健全性条件がある場合は`undelivered`が正の値になる。
- `dispatch.sqlite`の`delivery_health_clock`、`delivery_health_meta`：待ち時間の起点と最終完了時刻。既存の配送記録を削除しない。

検知するのは、宛先初期化失敗、配送拒否・結果不明、長期滞留、確認照会失敗、確認待ち期限超過・期限切れ。台帳の読み取りエラー等でワーカーが完了できない場合はheartbeatを更新せず、watchdogが停止を検知する。

CLIは送信待ちやエラーがあれば非0で終了する。空のキューでも宛先の初期化失敗を健全扱いしない。単なる未到来の確認待ちは直ちに障害としない。

## 専用設定

新しく作る試験設定には次の任意項目を指定できる。既存の固定設定へそのまま追記すると設定変更扱いになるため、現在の実機試験設定は変更しない。

```json
"health": {
  "monitor_id": "owr-delivery-lab",
  "backlog_seconds": 300,
  "ack_seconds": 300
}
```

省略時は閾値を300秒とし、stateパスから安定したmonitor_idを生成する。具体的なIDは生成されたheartbeatから取得する。watchdogは同じIDだけを受け付ける。

対象警報は各channelの`kinds`で指定する。省略時は全種類、指定時は1種類以上。空配列、未対応名、重複、未実装プロバイダーは配送前に拒否する。方式として現在指定できるのは`pushover`、`smtp_tls`、`smtp_starttls`、ローカル試験用の`smtp_test`。

`examples/monitoring/notification-health-watchdog.example.json`は独立watchdogの接続例。heartbeatファイル、専用state、monitor_idを合わせる。配送先はローカルSMTP試験受信機であり、外部メールへは送信しない。

```sh
python3 tools/monitor-runtime-lab.py watchdog --config /path/to/watchdog.json
```

専用環境では別のSQLite状態と注入したローカル受信先で検証する。本番では生存記録を専用SSH等で別ホストへ渡し、失敗中の通常配送とは異なる認証・経路を用意する。今回、dmの設定やタイマーは変更しない。

## 検証

```sh
python3 -m unittest discover -s tests -p 'test_notification_health.py' -v
python3 -m unittest discover -s tests -p 'test_notification_dispatch_lab.py' -v
python3 -m unittest discover -s tests -p 'test_monitor_runtime_lab.py' -v
python3 -m unittest discover -s tests -p 'test_operations_monitor_lab.py' -v
```

外部APIは模擬。通知処理の失敗を独立watchdogが一度だけ通知し、健全性回復時に解消すること、停止検知、壊れたheartbeatで以前の異常を解消しないこと、watchdog自身の配送失敗を保存して再試行することまで試す。

試験結果は`evidence-public/notification-health-lab.json`に保存する。定期実行、別ホストへの配置、WordPress画面、設定移行とエラー照合の運用操作は今後の段階。
