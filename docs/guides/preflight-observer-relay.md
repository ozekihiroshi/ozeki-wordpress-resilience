# 導入前検査watchdogの状態報告を定期取得する

既存の `tools/observer-status.py` と `tools/observer-status-relay.py` を使います。新しい通知基盤は追加しません。独立watchdogが書く公開状態を固定コマンドSSHで取得し、WordPress側では読取り専用表示に使います。

## 1. 独立watchdog側

[管理画面の設定](preflight-watchdog-admin.md)に従い、各observe設定の `admin_site_id` と `public_status_file` を指定します。検査側と受渡し側は異なるmonitor_id・公開ファイルにします。

`examples/preflight-watchdog/source-endpoint.example.json` と `receiver-endpoint.example.json` を編集して配置します。専用SSHユーザーには公開報告だけを読ませ、監視の秘密鍵・通知設定・状態台帳へのアクセスや書込み権限を与えません。root管理のauthorized_keysに対象ごとの公開鍵を登録します。

```text
restrict,command="/usr/bin/python3 -B /opt/owr/tools/observer-status.py endpoint --config /etc/owr/preflight-source-endpoint.json" ssh-ed25519 検査側報告取得用の公開鍵
restrict,command="/usr/bin/python3 -B /opt/owr/tools/observer-status.py endpoint --config /etc/owr/preflight-receiver-endpoint.json" ssh-ed25519 受渡し側報告取得用の公開鍵
```

SSHの公開鍵認証のみを許可し、TTY・転送を禁止します。

## 2. WordPress側の取得サービス

`examples/preflight-watchdog/source-pull.example.json` と `receiver-pull.example.json` を実環境のパス・サイトID・接続先へ変更します。専用ユーザーが実行し、鍵・ロックのディレクトリーは0700、秘密鍵は0600にします。公開報告ディレクトリーは専用ユーザーだけが書けるようにし、WordPressには読取りだけを許可します。

known_hostsには別経路で確認したwatchdogホストの公開鍵を `owr-notification-example-site` の別名で登録します。両設定のmonitor_idは対応する報告と一致させ、報告・転送記録・各ロックのパスを重複させません。

```sh
python3 -B /opt/owr/tools/observer-status-relay.py --config /etc/owr/preflight-source-pull.json --interval 60
python3 -B /opt/owr/tools/observer-status-relay.py --config /etc/owr/preflight-receiver-pull.json --interval 60
```

各コマンドは継続プロセスです。別々のサービスとして管理してください。このページの専用試験はプロセスの停止・再開を対象としています。systemd配置とOS再起動は [サービス管理手順](preflight-observer-systemd.md) を参照してください。二重起動はロックで拒否されます。

## 3. WordPressの表示設定

既存の `OWR_PREFLIGHT_WATCHDOG_REPORTS` の各対象へ、対応する `transfer_file` を追加します。

```php
define('OWR_PREFLIGHT_WATCHDOG_REPORTS', [
    'source' => [
        'path' => '/var/lib/owr-reports/preflight-source.json',
        'monitor_id' => 'preflight-source',
        'transfer_file' => '/var/lib/owr-reports/preflight-source-transfer.json',
    ],
    'receiver' => [
        'path' => '/var/lib/owr-reports/preflight-receiver.json',
        'monitor_id' => 'preflight-receiver',
        'transfer_file' => '/var/lib/owr-reports/preflight-receiver-transfer.json',
    ],
]);
```

サイトIDは `OWR_PREFLIGHT_SITE_ID` と外部報告で揃えます。定義済みの定数を重複定義しないでください。

## 障害・回復時の表示

- 通信断：最後の正常な報告を保持し、転送失敗を表示します。古くなった報告は現在の状態が不明と表示します。
- watchdog更新停止：SSHへ接続できても、報告の元の時刻が5分以上古ければ更新停止を表示します。
- 取得処理停止：取得記録自体が5分以上古くなると、取得処理の確認を促します。
- 回復：新しい報告・取得記録を受け取ると表示が戻ります。過去の発生・解消履歴は報告に残ります。

受渡しは独立署名による証明ではありません。サイト・監視対象・要求nonce・ホスト鍵・形式を検査しますが、信頼するwatchdogとOS権限が前提です。管理画面自体は通知を送らず、サイト停止中の警報は独立watchdogが担当します。

## 専用試験の範囲

分離したコンテナーと内部ネットワークを使用し、実watchdog・固定コマンドSSH・定期転送・WordPress・Chromiumを動かします。監視元は生成した導入前検査報告を更新する専用プロセスです。過去の報告の再生や時刻の加工は行わず、通知は専用ローカル記録へ配送します。本番収集アダプター・本番通知先・物理ホスト全体の障害試験とは区別します。

## 結果と修正

[専用試験の結果](../../evidence-public/preflight-observer-relay.json) に状態と画面の記録をまとめています。通信断のまま5分以上経過、watchdog更新停止と取得処理停止の実時間310秒以上、再開後の回復を確認しました。初回に報告・更新記録の更新途中を異常とする誤警報が見つかり、100ミリ秒の再読取りでも不十分だったため、その再試験も中止しました。最終的に更新記録の確定済み検査時刻を進捗とする方式へ修正しました。報告だけが進んでも進捗を更新せず、更新記録が止まれば期限超過になります。時刻逆転や形式不正は拒否します。初回失敗は保存し、修正後の試験では同じ誤警報が出ていないことを確認しています。
