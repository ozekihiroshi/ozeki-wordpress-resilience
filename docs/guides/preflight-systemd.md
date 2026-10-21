# 導入前検査のsystemdサービス

`examples/preflight-relay/owr-preflight.service` を専用Linuxホストへ配置するための手順です。プローブ対象ホストとサービス実行ホストはSSHで接続します。WordPressへはローカル報告ディレクトリーを読取り専用で渡します。別ホストへのSSH受渡しは [別VM間の手順](preflight-two-vm.md) に分けています。

## 配置と権限

[定期更新手順](preflight-relay.md)に沿ってSELECT専用のDB権限、固定コマンドSSH、照合済みホスト鍵、プロファイルと棚卸し入力を用意します。以下は配置先を統一した例です。

- `/opt/owr/tools/` と必要な `schemas/`：root所有。サービスユーザーから書換え不可。
- `owr-preflight`：ログイン不可の専用OSユーザー。実行グループは `www-data`。
- `/var/lib/owr-preflight/`：専用ユーザー所有0700。秘密鍵、入力ファイル、ロックを置きます。`work/` も0700。
- `/var/lib/owr-preflight-web/`：専用ユーザー所有、www-dataグループ、2750。報告と更新記録は0640で生成されます。WordPressには書込みを許可しません。
- `/etc/owr/preflight-relay.json`：root所有0640、www-dataグループ。秘密の値そのものを入れず、非公開ディレクトリーのファイルパスを指定します。

出力は `/var/lib/owr-preflight-web/report.json` と `health.json`、ロックは `/var/lib/owr-preflight/loop.lock` とします。WordPress定数もこの2ファイルに合わせます。親ディレクトリーやマウントを含め、サービスユーザーが書ける範囲を限定してください。

## 起動・停止・再開

管理者がサービスファイルを `/etc/systemd/system/owr-preflight.service` へ配置します。

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now owr-preflight.service
systemctl status owr-preflight.service
sudo journalctl -u owr-preflight.service --no-pager -n 50
```

60秒間隔（処理時間を除く）で更新します。サービスがactiveでもSSH取得が成功したとは限らないため、管理画面の更新状態と検査結果の両方を確認します。取得失敗は状態記録に残り、ループは次回再試行します。設定不正や更新記録自体の書込み失敗で終了した場合は、systemdが10秒後に再起動します。原因修正が必要です。

```sh
sudo systemctl stop owr-preflight.service
sudo systemctl start owr-preflight.service
```

停止しても記録は削除しません。5分以上経過すると管理画面は更新停止・情報の古さを表示します。再開後、新しい対応する報告と更新記録が揃うと回復します。停止だけではenable状態は解除されません。OS起動時にも停止しておきたい場合は `sudo systemctl disable --now owr-preflight.service` を使います。

## OS起動と制限

`WantedBy=multi-user.target` によりenable済みサービスはOS起動時に開始します。`RequiresMountsFor` で状態・公開ディレクトリーのマウントを要求します。`network-online.target` は接続先の正常性を保証しません。

`NoNewPrivileges`、`ProtectSystem=strict`、`ProtectHome`、`PrivateTmp` と `ReadWritePaths` を設定しています。停止時はサービスの子プロセスも対象にし、30秒の停止期限を設けています。これらはroot侵害からの独立性を保証するものではありません。

## 専用環境の受入試験

既存72時間観測から分離したUbuntu KVMゲストで、配布テンプレートを変更せず使用します。実SSH/MariaDBと生成データからの報告を専用9p共有領域へ出し、別のWordPressコンテナーが読取り専用マウントで表示します。

確認項目はenabled/active、実行ユーザーと制限、WordPressからの鍵読取り・報告書込み拒否、重複起動拒否、60秒周期、実停止310秒以上、再開、ゲストOSのBoot ID変更、手動startなしの自動復帰、管理画面の回復です。検証用共有領域を使う同一物理ホスト上の試験であり、物理障害や本番環境のマウント構成は別途検証が必要です。WSLおよび既存サーバーの再起動は行いません。
