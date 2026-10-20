# 独立watchdog報告の定期受渡し

生成側・取得側を監視する独立watchdogの公開用報告を、WordPressとは別の取得ユーザーがSSHで取得します。WordPressの画面アクセスやWP-Cronは転送を起動しません。

## 配置

1. 独立watchdogの各設定で admin_site_id を対象サイトID、public_status_file をそれぞれ別の固定ファイルにします。monitor_id は daily-source と daily-receiver など、対象ごとに異なるIDにします。
2. watchdogホストに読取り専用SSHユーザーを作り、公開用報告だけを読めるようにします。秘密鍵・通知資格情報・SQLite台帳の読取りを許可しません。
3. 対象ごとに専用SSHキーを作ります。authorized_keys は restrict と固定コマンドを使います。

       restrict,command="/usr/bin/python3 /opt/owr/tools/observer-status.py endpoint --config /etc/owr/source-read.json" ssh-ed25519 PUBLIC_KEY

   source-read.json の内容：

       {"site_id":"your-site-id","public_status_file":"/var/lib/owr-public/source.json"}

   receiver用も別のキー・固定設定ファイルを用意します。ホスト鍵は管理者が確認してknown_hostsへ固定してください。鍵の自動承認はしません。
4. WordPress側ホストに owr-relay ユーザーを作り、実装一式を /opt/owr に配置します。転送の秘密鍵・設定はrootまたはowr-relayだけが読める場所に置きます。WordPressのPHPユーザーには公開用報告ディレクトリの読取りだけを許可します。

## 取得設定

/etc/owr/observer-source.json の例です。receiver用は監視ID・鍵・出力・ロックをすべて分けます。

    {
      "site_id": "your-site-id",
      "monitor_id": "daily-source",
      "host": "watchdog.example.invalid",
      "user": "owr-status-reader",
      "port": 22,
      "identity_file": "/var/lib/owr-observer-relay/source-key",
      "known_hosts": "/var/lib/owr-observer-relay/known_hosts",
      "status_file": "/var/lib/owr-status-web/source-observer.json",
      "transfer_health": "/var/lib/owr-status-web/source-transfer.json",
      "lock_file": "/var/lib/owr-observer-relay/source-pull.lock",
      "loop_lock": "/var/lib/owr-observer-relay/source-loop.lock"
    }

known_hostsのホスト別名は owr-notification-your-site-id です。秘密鍵は0600、公開用報告は0640です。公開用ディレクトリをowr-relay所有・PHPの実行グループ・2750にして、原子的置換後もグループ読取りを維持します。実行グループがwww-dataでない環境はサービス例も合わせて変更してください。

まず単発で確認します。

    sudo -u owr-relay python3 /opt/owr/tools/observer-status-relay.py --config /etc/owr/observer-source.json --interval 0

成功は終了コード0、転送失敗または報告期限超過は2です。報告ファイルと取得結果ファイルは別々に保存されます。転送失敗時も直前の報告は消しません。失敗詳細・資格情報・相手からの任意テキストを取得結果へ書き出しません。対象ID不一致・時刻逆行も拒否します。

## 定期実行と停止

examples/observer-status-relay/owr-observer-status@.service を /etc/systemd/system/ に配置し、専用ユーザー・ディレクトリ・読取り権限を確認して実行します。

    sudo systemctl daemon-reload
    sudo systemctl enable --now owr-observer-status@source owr-observer-status@receiver
    sudo systemctl status owr-observer-status@source owr-observer-status@receiver

初期値は60秒間隔です。停止・再開：

    sudo systemctl stop owr-observer-status@source owr-observer-status@receiver
    sudo systemctl start owr-observer-status@source owr-observer-status@receiver

ループ全体のロックで重複起動を拒否します。停止時に報告・履歴・台帳を削除しません。サービスの停止・再開とOS再起動後の自動起動は、別の[専用VM試験](observer-status-systemd.md)で確認しています。

## WordPress設定と確認

前の[管理画面手順](daily-watchdog-admin.md)の各対象に transfer_file を追加します。

    define('OWR_DAILY_WATCHDOG_REPORTS', [
      'source' => [
        'path' => '/var/lib/owr-status-web/source-observer.json',
        'monitor_id' => 'daily-source',
        'transfer_file' => '/var/lib/owr-status-web/source-transfer.json',
      ],
      'receiver' => [
        'path' => '/var/lib/owr-status-web/receiver-observer.json',
        'monitor_id' => 'daily-receiver',
        'transfer_file' => '/var/lib/owr-status-web/receiver-transfer.json',
      ],
    ]);

Resilience → 生成・取得の独立監視を開き、両方の最終取得処理と観測完了時刻が更新されることを確認します。

| 表示 | 意味と確認先 |
| --- | --- |
| 定期取得は成功 | SSH取得成功。監視対象の正常とは別なので、下の警報も確認 |
| 転送に失敗 | 通信、SSH鍵、権限、応答検査などの失敗。直前の報告を保持 |
| 接続できたがwatchdog報告が更新されない | SSH取得は成功したが、元の観測時刻が5分以上古い。watchdog処理を確認 |
| 定期取得の記録が更新されない | 取得結果自体が5分以上古い。転送サービス・取得ホストを確認 |
| 現在の状態は不明 | 元の報告が5分以上古い。下の状態・履歴は過去の記録 |

回復は新しい報告が届いてから表示します。SSHがつながるだけでは元の報告時刻を新しくしません。この画面は自動リロードしないので再読み込みしてください。WordPress停止時は閲覧できません。独立watchdogの通知運用は引き続き必要です。

## 試験の範囲

tools/run-observer-relay-lab.py --output ＜新しい専用フォルダ＞で再現します。4役の専用コンテナとWordPress/MariaDB/Chromiumを使用し、実際のwatchdog処理、固定コマンドSSH、定期取得、通信切断、生成処理停止、watchdog停止、取得処理停止、再開を試します。期限超過は実際に5分以上待ち、人工的な時刻変更はしません。通知先はローカル記録用コールバックです。実通知サービス・別物理ホスト・S3・本番サイトは対象外です。
