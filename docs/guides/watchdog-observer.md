# watchdogと監視ホストを別ホストから監視する

独立した観測ホストで `watchdog-observer.py observe` を定期実行する。監視対象は既存watchdogのホスト。WordPress、通知ワーカー、監視対象watchdogに依存しない状態領域と通知資格情報を使う。本番配置は未実施。

## 判定

専用SSHの固定コマンド `watchdog-probe` で、nonceを照合した応答とwatchdogの元の完了日時を取得する。SSH応答時刻でwatchdog完了日時を更新しない。

|対象|判定と意味|
|---|---|
|`<monitor_id>-reachability`|最後の認証済み応答から期限超過。ホスト・ネットワーク・SSH・鍵設定のいずれかで到達不能|
|`<monitor_id>`|watchdogの完了日時が期限超過。処理完了を確認できない|
|heartbeat_invalid|形式異常、未来日時、時刻巻戻し。同じ日時で内容が変わった場合も拒否|

通信断時は両方が警報になり得る。ホスト電源停止とネットワーク障害の断定はしない。SSHだけ復帰してもwatchdogの古い記録では復旧扱いにしない。初回の記録未取得には期限分の猶予がある。状態・警報・未配送記録はSQLiteで維持し、再起動で初期化しない。設定変更時は状態の移行計画が必要であり、安易に状態ディレクトリを削除しない。

## 配置手順

1. 別の障害領域のLinuxホストを観測用に用意する。同一EC2内のコンテナ分離だけではホスト障害対策にならない。専用環境のコンテナは試験用。
2. 対象ホストでwatchdogの `heartbeat_file` を専用公開ディレクトリに配置する。watchdogだけ書込可能、専用 `owr-probe` ユーザーにはディレクトリ検索とファイル読取だけ許可する。通知鍵・SQLite状態のある私有ディレクトリを公開しない。
3. toolsのPythonモジュール群を `/opt/owr` にroot所有・一般ユーザー書込不可で配備。endpoint.example.jsonを `/etc/owr/endpoint.json` に置く。SSH専用公開鍵のauthorized_keysに次を指定する。

```
restrict,command="/usr/bin/python3 /opt/owr/watchdog-observer.py endpoint --config /etc/owr/endpoint.json" ssh-ed25519 <公開鍵>
```

4. 専用ユーザーへのパスワード・TTY・転送を禁止する。接続元を観測ホストへ限定する。観測側の秘密鍵は専用ユーザー所有0600。known_hostsには信頼できる経路で取得したホスト公開鍵を `owr-notification-<site_id>` の名前で固定する。
5. observer.example.jsonのhost、鍵・known_hosts、monitor_id、stateを環境に合わせる。stateは専用ユーザー所有0700。alertsは既存notification-dispatch-labの設定形式で、専用outbox・配送状態・Pushover等の資格情報を指定する。監視対象の配送ワーカーを経由しない。資格情報をWordPress管理画面から読み出させない。
6. サービス・タイマー例を確認し `systemd-analyze verify` 後に配置する。既定は60秒周期、300秒の停止期限、SSHは20秒上限。検知時刻には周期・接続待ち・負荷分の遅延が加わる。全ホストで時刻同期する。
7. 手動実行で正常状態、watchdogのみ停止、ホスト到達不能、復帰、通知失敗を順に確認してから有効化する。これは本番変更を実行済みという意味ではない。

## 運用

到達不能警報では先に対象ホスト・通信・SSH鍵を確認する。watchdog警報だけならサービスログ・処理ロック・通知失敗を確認する。status.jsonに判断と未配送件数を保存する。終了コード非ゼロは警報または配送障害を含み、systemdの起動失敗だけを意味しない。

この観測ホスト自身の停止や共通AWS障害、通知サービス障害は残る。必要に応じて別事業者の外形監視で観測ホストを監視する。無限に監視を増やす前提ではなく、運用上の障害領域と責任を明示する。

## 専用環境の検証

2026-10-19: 外部通信できないDockerネットワーク上の2コンテナ間で実SSHを使用。完了記録の更新停止、監視対象コンテナ全体の停止・再起動、ホスト鍵不一致、不正記録、未配送の再送、再起動時の重複防止、読取専用権限を検証した。watchdog処理全体をこの試験で再実行するのではなく、完了記録の更新停止を再現している。既存watchdog処理はnotification-runtimeの試験対象。

単体試験9件ではnonce、リプレイ、未来日時、時刻巻戻し、同時刻の内容変更、異常中の通信断、独立配送処理も検証。外部通知はテスト用プロバイダーに置換。systemdの2ユニットは構文検証のみで、本番タイマーは未有効化。

再試験はWSL Ubuntuで `python3 tools/test_watchdog_observer.py` と `python3 tools/run-watchdog-observer-lab.py`。後者には既存イメージ `owr-external-lab:local` とDockerが必要。試験資源は終了時に削除し、結果をスクリプトと同じディレクトリのwatchdog-observer-lab-result.jsonへ保存する。今回の公開証跡は `evidence-public/watchdog-observer-lab-result.json`。
