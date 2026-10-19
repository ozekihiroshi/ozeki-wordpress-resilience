# WordPress管理画面で独立watchdogを確認する

Resilience → 通知の上部に、watchdog・監視ホストの状態を表示する。画面を再読込みして確認する。監視対象ホストへの到達性とwatchdog処理の完了を分け、最終確認日時、発報中の警報、通知引渡し待ち、独立配送の異常、最近20件の発生・解消履歴を表示する。

この欄の独立した警報通知は、外部観測ホストの専用配送設定に従う。画面下部の通常通知先を変更しても、独立観測の宛先設定は変更されない。「Resilience → 独立watchdog」からの設定反映については [独立watchdogの通知設定](observer-settings.md) を参照する。

取得不能・記録未取得・形式不正は正常とは扱わない。外部観測の完了日時から5分で報告を古いものと扱い、現在の状態が不明であることを表示する。前回の警報・通知失敗・履歴は残す。SSHで再取得しても元の日時を維持する。通知サービスの受付は端末受信・人の確認を保証しない。履歴20件は表示用の抜粋であり、監査記録の全件を置き換えない。

## データの流れ

1. 独立観測ホストのwatchdog-observer.pyが監視と通知処理を行い、公開用ファイルを原子的に更新する。
2. WordPress側の専用OSユーザーが、観測ホストの固定SSHコマンドobserver-statusから状態だけを取得する。監視対象ホスト・通常通知ワーカーを中継しない。
3. PHPは専用の読取専用ファイルを読み、manage_options権限を持つ管理者だけに表示する。画面アクセスに伴うSSH・通知送信・監視設定変更はない。

公開するフィールドはサイトID、監視ID、元の観測日時、模擬試験の印、対象別の最終確認・警報・未配送数、独立配送の結果、限定した履歴のみ。SSH鍵、通知資格情報、内部パス、例外本文、通知本文、receipt IDは公開しない。サイト照合、SSHホスト鍵固定、nonce照合、サイズ制限、時刻巻戻し拒否を行う。

## 設定

現在は専用環境で検証した開発版。本番への設定変更・配置・実通知は行っていない。

1. 通知画面の「設定候補をエクスポート」からsite_idを確認する。接続例のREPLACE_WITH_WORDPRESS_SITE_IDを必ず置き換える。
2. 観測ホストの設定にadmin_site_idとpublic_status_fileを追加する。例：`"admin_site_id":"サイトID", "public_status_file":"/var/lib/owr-observer-public/status.json"`。設定は状態DBに固定されるため既存設定へ直接追記すると拒否される。既存の未配送記録を消さず、旧観測の配送・確認処理を継続したまま別stateで新設定を検証する。既存stateを消してやり直さない。無停止の設定移行はこの変更には含めない。
3. 公開ディレクトリはwatchdog実行ユーザー所有、専用読取グループ、2750。ファイルは0640。SSHのowr-statusユーザーはこのグループで読めるだけにし、観測の私有状態・通知鍵を読めないようにする。コード・SSH設定はroot所有で書込み不可にする。既存observerサービスのProtectSystem=strictに合わせ、observer-public-status.conf例を `/etc/systemd/system/owr-watchdog-observer.service.d/public-status.conf` に配置して公開ディレクトリへの書込みを許可する。ディレクトリを先に作成し、設定確認後にdaemon-reloadする。
4. examples/watchdog-observerのobserver-status-endpoint.example.jsonを環境に合わせる。専用公開鍵のauthorized_keysを次の形式にする。sshd側でもパスワード・TTY・転送を禁止する。

```
restrict,command="/usr/bin/python3 /opt/owr/observer-status.py endpoint --config /etc/owr/observer-status-endpoint.json" ssh-ed25519 <公開鍵>
```

5. WordPressホストにowr-observer-relayユーザーを用意し、秘密鍵0600をこのユーザーだけに許可する。known_hostsの登録名は `owr-notification-<サイトID>`。公開鍵は信頼できる別経路で照合する。pull.example.jsonのhostは独立観測ホストを指す。
6. WordPress側の報告ディレクトリをrelay所有、Web実行ユーザーが所属する読取グループ、2750にする。PHPに書込みや秘密鍵の読取りを許可しない。relayのlockディレクトリは0700。
7. wp-config.phpで `define('OWR_OBSERVER_STATUS_FILE','/var/lib/owr-observer-report/status.json');` を指定する。パスをWebルートに置かず、HTTPで直接公開しない。
8. 手動pullで受信を確認し、systemdのservice・timer例を検証してから定期実行へ接続する。これらを有効化するまでは自動更新されない。WordPress側に接続先や秘密情報を入力するUIは追加していない。

## 障害時

- 「現在の状態は不明」：観測ホストの稼働と定期観測、SSH転送タイマー、鍵、接続先、時刻同期を確認する。状態ファイルの日付を書き換えて解消しない。
- 「通知失敗」：独立観測ホストの配送状態・認証・通知サービスを確認する。画面の引渡し待ち0件だけでは配送完了と判断しない。
- 管理画面自体が開かない：外部観測からの通知と運用手順で対応する。この画面は外部監視の代替ではない。

WordPressが侵害された場合、この画面の表示自体は信頼の起点にできない。復旧判断は独立観測・署名検証で行う。表示状態は署名済みの復旧証拠ではない。

## 検証

専用WordPress・MariaDBと実ブラウザーで、状態・警報・配送失敗・復帰履歴、未取得・古い報告・異なるサイト・未来日時・不正件数・過大入力、管理者権限、デスクトップとスマートフォン幅を確認する。外部通知は模擬プロバイダーを使い、外部通信できないコンテナで実行する。

再実行コマンド：

```
python3 tests/test_observer_status.py
php tests/test_observer_admin.php
python3 tools/test_watchdog_observer.py
python3 tools/run-observer-status-ssh-lab.py /tmp/observer-ssh-result.json
python3 tools/run-notification-admin-lab.py --output /tmp/observer-admin-new-run
```

既存の専用Dockerイメージが必要。出力ディレクトリは新規のものを指定する。SSH試験では秘密情報除外、元の日時保持、サイト照合、巻戻し拒否、ホスト鍵固定、固定コマンド、読取専用権限も確認する。
