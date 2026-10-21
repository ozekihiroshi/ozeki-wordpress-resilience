# 導入前検査watchdogの定期転送をsystemdで管理する

既存の `examples/observer-status-relay/owr-observer-status@.service` を変更せず再利用します。独立watchdogの公開報告を60秒ごとにSSHで取得するサービスです。検査処理やwatchdog本体の起動とは別です。

## 配置

[SSH接続・鍵・表示設定](preflight-observer-relay.md)を先に設定します。以下の例では専用ユーザーを `owr-relay`、WordPressの読取りグループを `www-data` とします。実際のWebサーバーのグループが違う場合はユニットと権限を合わせてください。

- コードは `/opt/owr` にroot所有で配置します。
- 鍵・known_hosts・ロックは `/var/lib/owr-observer-relay`（owr-relay所有、0700）へ置きます。秘密鍵は0600です。
- 報告・転送記録は `/var/lib/owr-status-web` に置きます。owr-relayが書込み、www-dataは読取りのみとします。
- source/receiverのpull設定を `/etc/owr/observer-preflight-source.json` と `/etc/owr/observer-preflight-receiver.json` に保存します（root:www-data、0640）。monitor_idはそれぞれ `preflight-source` と `preflight-receiver`、鍵・ロック・出力は別ファイルにします。

既存の日次監視と併用する場合もインスタンス名とファイルを重複させないでください。WordPressの `OWR_PREFLIGHT_WATCHDOG_REPORTS` のpath/transfer_fileを上記の実ファイルに合わせます。

```sh
sudo cp /opt/owr/examples/observer-status-relay/owr-observer-status@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now owr-observer-status@preflight-source owr-observer-status@preflight-receiver
systemctl status owr-observer-status@preflight-source owr-observer-status@preflight-receiver
sudo journalctl -u owr-observer-status@preflight-source -u owr-observer-status@preflight-receiver --since '10 minutes ago'
```

WordPress管理画面の「導入前検査の独立監視」で、両報告と取得記録の時刻が進むことを確認します。activeだけでは取得成功を保証しません。SSH通信失敗時もプロセスは継続し、転送記録へ失敗を残します。

## 停止・再開

```sh
sudo systemctl stop owr-observer-status@preflight-source owr-observer-status@preflight-receiver
sudo systemctl start owr-observer-status@preflight-source owr-observer-status@preflight-receiver
```

停止中も最後の報告と履歴は保持します。5分以上更新されなければ、画面は古い報告と取得処理の停止を表示します。再開後、新しい報告と取得記録を取得すると回復します。`stop` は次のOS起動時の自動起動を無効にしません。廃止時は `disable --now` を使用し、履歴や鍵を一緒に削除しないでください。

OS再起動後は `is-enabled`、`status`、時刻の進行、管理画面を確認します。本番や72時間観測ホストをこの試験のために再起動しないでください。

## 権限と検証範囲

ユニットは専用ユーザー、NoNewPrivileges、ProtectSystem=strict、ProtectHome、PrivateTmp、書込み先の限定を使います。WordPressから秘密鍵を読めず報告を書き換えられない構成です。既存のロックにより同じ対象の二重起動を拒否します。

専用試験は `tools/run-preflight-observer-relay-vm-lab.py --output 新しい専用ディレクトリー` で実行します。生成した導入前検査報告、実watchdog、固定コマンドSSH、変更していない60秒周期のユニット、実WordPress/Chromiumを使います。通知はローカル試験記録です。ゲストVMからWeb試験環境への最後のファイル公開には専用9p共有を使い、物理ホストの独立性や本番構成全体を保証する試験とは区別します。

## 実測結果

[検証記録](../../evidence-public/preflight-observer-systemd.json)：13項目、実ブラウザ4場面、既存probe単体10件を確認しました。実時間310秒以上の転送停止、明示的再開、ゲストBoot IDが変わるOS再起動を実施し、自動起動と管理画面の回復、警報・解消履歴の保持を確認しました。試験では専用VM内のsource/receiverインスタンス名を使い、運用例では既存の日次転送と衝突しないpreflight-source/preflight-receiverを使います。72時間観測ホストのBoot IDは変わっていません。
