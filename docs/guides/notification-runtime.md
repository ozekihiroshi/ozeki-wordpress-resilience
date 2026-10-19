# 通知の定期実行と転送・ワーカーの停止検知

2026-10-19。専用環境で実装・検証。本番ホストへの配置、タイマー有効化、実通知は行っていない。

## 構成

`notification-runtime.py` に3つの独立した実行入口を設けた。

|役割|処理|完了の証拠|
|---|---|---|
|relay|専用SSHでテスト要求を預け、公開用結果を取得|応答照合・ローカル反映まで成功した時刻|
|worker|要求取込み、通常警報・テスト処理、結果公開|その周期の処理・結果公開が完了した時刻と異常件数|
|watchdog|上記2つの生存記録を独立に監視|自身の完了記録と、永続化した警報・解消履歴|

転送の生存記録は**前回の成功時刻**を次回SSH接続に同梱する。外部ホストではその時刻を保持し、受信した現在時刻に書き換えない。初回はまだ成功記録がないため、2回目の成功した接続で外部側に記録が届く。

要求がなくても転送は定期実行する。ワーカー停止中に同じ古い結果を転送し続けても、ワーカーの生存記録は更新されず停止を検知する。SSH断・鍵不一致では転送プロセスが起動していても成功時刻が進まない。

「停止」はPID消失だけでなく、正常な周期の完了が途絶えたことを意味する。転送だけ停止、ワーカーだけ停止、両方停止を、それぞれのmonitor_idで区別する。

## 警報の扱い

- 基準値は転送・ワーカーとも300秒。初回から記録がない場合も起動後300秒の猶予を経て停止警報とする。
- 同じ停止中に何度監視しても新しい警報イベントを増やさない。正常な記録が戻ったときに解消を1回記録する。状態はSQLiteに残り、監視プロセスの再起動でも保持する。
- 記録破損・対象ID違い・未来時刻・時刻の巻戻しは異常扱い。既に開いている停止警報を破損記録で解消しない。
- テスト要求の取込失敗では通常の警報処理を続け、完了記録に異常件数を載せる。処理継続中の異常は `notification_delivery_failed`、完了途絶は `monitor_stopped` と区別する。
- 転送失敗、通常配送処理の中断、公開処理失敗では完了記録を更新しない。
- watchdogの警報は監視対象ワーカーと別の台帳・配送状態・認証情報を使う。Pushover用アダプターへ接続でき、受付・確認待ち・取消・結果不明を既存の配送機構で保持する。結果不明を盲目的に再送しない。
- watchdog自体の警報配送失敗は終了コードと自身の生存記録に反映する。watchdog自身の停止や外部ホスト全体の停止を保証して検知するには、さらに別ホストからその生存記録を監視する必要がある。その本番配置は今回の範囲外。

## 配置設定

[設定例とsystemdユニット](../../examples/notification-runtime/)を用意した。`site-relay` / `site-worker` はサイトごとに固有のIDへ変更する。既存の[SSH受渡し設定](notification-transfer.md)と権限分離が前提。

1. WordPress側の転送設定へ次の2項目を追加する。転送ランタイム設定のmonitor_id・heartbeat_fileと完全に一致させる。

```json
{
  "relay_monitor_id": "site-relay",
  "relay_heartbeat_file": "/var/lib/owr-relay/heartbeat.json"
}
```

2. 外部ホストの受信設定へ次の2項目を追加する。IDは転送側と同一。パスは外部側の固定受信先。

```json
{
  "relay_monitor_id": "site-relay",
  "relay_heartbeat_file": "/var/lib/owr-inbox/relay-heartbeat.json"
}
```

古い設定で生存記録がまだ付いていない要求も従来どおり扱う。ただし記録なしのまま停止監視を有効にすれば、猶予後に停止警報になる。

3. `runtime-relay.example.json` / `runtime-worker.example.json` / `runtime-watchdog.example.json` を各ホストの `/etc/owr/runtime-役割.json` に配置する。プログラム、設定、ユニットは管理者所有で、実行ユーザーが変更できないようにする。Windowsからコピーしたファイルの書込み権限を引き継がず、Linuxでファイル0644・親ディレクトリ0755等を明示する。

4. ワーカー生存記録用 `/var/lib/owr-worker-health` はワーカー所有、監視ユーザーが読める専用グループ、2750とする。生存記録は0640。受信台帳側の生存記録も監視ユーザーは読取りのみ。`owr-watchdog` は既存の共有読取りグループへ参加させるが、ワーカーの秘密情報ディレクトリへはアクセスさせない。

5. `/var/lib/owr-watchdog` はwatchdog所有・0700。独立警報用 `watchdog-alerts.example.json` を `/etc/owr/watchdog-alerts.json` として配置する。Pushoverの秘密値はwatchdog所有0600の別ファイルへ置く。監視対象ワーカーのDBやキーへの依存を作らない。同じサービスを利用しても、実行・保存・権限を分ける。

6. 常設化前に各ユーザーで1周期ずつ実行し、対象IDと時刻、結果の公開権限を確認する。実接続設定では実通知が発生し得る。

```sh
python3 /opt/owr/notification-runtime.py relay --config /etc/owr/runtime-relay.json
python3 /opt/owr/notification-runtime.py worker --config /etc/owr/runtime-worker.json
python3 /opt/owr/notification-runtime.py watchdog --config /etc/owr/runtime-watchdog.json
```

標準のwatchdog設定は独立したPushover配送を使う。既存の直接SMTP配送を使う場合は `alert_dispatch_config` の代わりに従来の `delivery` 設定を指定できる。試験では外部送信を模擬している。

## 定期実行

提供するユニットはシステム用で、ホストに必要な役割だけを配置する。WordPress側はrelay、外部側はworkerとwatchdog。ユーザー・ディレクトリの作成を済ませてから配置する。

|役割|前回終了から次回まで|強制終了の上限|
|---|---:|---:|
|relay|60秒＋最大5秒の分散|45秒|
|worker|60秒＋最大5秒の分散|120秒|
|watchdog|30秒＋最大5秒の分散|45秒|

`Type=oneshot` と排他ロックで同じ役割の重複実行を防ぐ。`KillMode=control-group` でタイムアウト時には子SSHも終了する。タイマーを停止しても残った実行中サービスは別途停止が必要。`NoNewPrivileges`、読取り専用のシステム領域、役割別書込み先を設定する。ホスト再起動後は30秒を基準に再開し、停止中に飛ばした回数をまとめて実行しない。

管理担当が手動試験完了後に行う有効化例（今回は実行していない）：

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now owr-notification-relay.timer
```

外部ホストではworker/watchdogのtimerをそれぞれ有効化する。`systemctl list-timers` と対応サービスのjournalを確認する。watchdogは停止警報を正常に記録・配送できた場合は終了0で、警報が開いていること自体をサービス故障とは扱わない。取込・配送・監視処理の失敗は非0。

## 故障時の確認

- relayのみ停止：転送タイマー・サービス、SSH到達性、専用鍵とホスト鍵、ローカル要求・状態ディレクトリを確認する。
- workerのみ停止：ワーカーのタイマー・サービス、配送DBロック、結果の公開権限、処理時間超過を確認する。古い結果を更新時刻だけ書き換えて復帰扱いにしない。
- 処理継続中の異常：取込や通知配送の記録を確認する。結果不明は照合なしで再送しない。
- 両方停止：各サービスの状況とwatchdogの読取り権限・時刻同期も確認する。外部ホスト自体が停止すると同居watchdogも止まるため、別ホストの監視が必要。
- 復旧後：新しい正常記録が届くまで待ち、該当する対象だけが解消されることを確認する。警報DB・配送DBを消して解消させない。

SSHキー侵害時は虚偽の転送生存記録を送られる余地がある。この生存記録は暗号署名付きバックアップの信頼の起点ではない。

## 専用環境での検証範囲

```sh
python3 -m unittest discover -s tests -p 'test_notification_runtime.py' -v
python3 -m unittest discover -s tests -p 'test_notification_transfer.py' -v
python3 tools/run-notification-runtime-lab.py --output /tmp/owr-runtime-new-result
```

専用コンテナ2台で実SSHを使用し、relay・worker・watchdogを別OSユーザー・別の定期プロセスとして動かす。試験間隔1秒、停止判定8秒へ短縮する。relay停止、worker停止、SSH鍵不一致による通信断、各復帰、警報の重複抑止を確認する。通常の転送・権限分離試験も含む。通知は専用のローカル記録へ模擬送信する。

systemdユニットはLinux上の0644ファイルで `systemd-analyze verify` を通す。専用コンテナ内の周期実行は試験用スケジューラーで行い、systemdデーモンそのものの再起動・OS再起動試験は今回行わない。常設systemdタイマー、本番メール・プッシュ、別ホストからのwatchdog停止検知は未配置。既存community/dm、FTP、MySQLには変更しない。
