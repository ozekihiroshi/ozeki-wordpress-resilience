# SSH棚卸し・導入前検査の定期更新（試作）

外部Linuxホストで `tools/preflight-relay.py` を動かします。WordPressリクエストからSSHを実行せず、専用ユーザーが検査結果と更新記録を原子的に配置します。今回はWordPressと共有するローカルディレクトリー／読取り専用マウントへの受渡しです。別ホストへのSSH受渡しは [別VM間の手順](preflight-two-vm.md) を参照してください。systemd配置と専用VMでのOS再起動試験は [systemd手順](preflight-systemd.md) を参照してください。

## 準備

[SSH棚卸し](host-inventory-ssh.md)の接続設定・固定コマンド・SELECT専用DBユーザーを準備します。検査側の専用ユーザーだけが書ける出力ディレクトリー（例：0750、WordPressの読取りグループ）を作ります。WordPressには読取りのみを与えます。秘密鍵・入力設定・ロックは別の非公開ディレクトリーに置き、WordPressへ渡しません。

報告と更新記録は異なるディレクトリーに置くことを推奨します。同じ領域が書込み不能になった場合、失敗記録も届かず、5分経過後に更新停止として判定されます。

設定例（絶対パス、各ファイルは別々）：

```json
{
  "site_id": "example-site",
  "config_sha256": "対象プロファイルの64桁ハッシュ",
  "profile_file": "/etc/owr/profile.json",
  "inventory_file": "/etc/owr/inventory.json",
  "connection_file": "/etc/owr/ssh.json",
  "workspace": "/var/lib/owr-private/work",
  "lock_file": "/var/lib/owr-private/relay.lock",
  "report_file": "/var/lib/owr-report/preflight.json",
  "health_file": "/var/lib/owr-health/preflight.json"
}
```

```sh
python3 -B tools/preflight-relay.py --config /etc/owr/relay.json --interval 60
```

60秒間隔は前回処理が終わってから数えます。間隔0は1回のみ実行します。同じロックを使う重複起動は拒否します。停止は対象プロセスへSIGTERMを送り、再開は同じコマンドを実行します。プロファイルを変更すると設定ハッシュの更新が必要です。固定された入力自体が読めない場合や更新記録を書けない場合は終了コード2で止まり、過去の記録が古くなります。

WordPressには既存の `OWR_PREFLIGHT_REPORT`、サイトID・ハッシュのほか、以下を設定します。

```php
define('OWR_PREFLIGHT_TRANSFER_FILE', '/var/lib/owr-health/preflight.json');
```

## 判定

- 取得・検査失敗：今回の失敗結果を配置します。過去の成功で置き換えません。
- 受渡し失敗：前回の報告を保持し、別の更新記録へ失敗を書きます。
- 更新停止：更新記録が5分以上古ければ、処理停止または配送停止として表示します。原因はこの情報だけでは断定しません。
- 反映途中・不整合：報告と更新記録の時刻が一致しなければ成功と表示しません。
- 回復：新しい報告と更新記録の組が揃うと更新成功へ戻ります。導入前検査で未確認項目が残ることとは別です。

書込みは一時ファイル、fsync、renameを使います。報告と更新記録は別々に反映されるため、途中状態を時刻照合で検知します。読取り専用のWordPress側から修正や再送はできません。受渡しは署名証明ではなく、信頼する配置ユーザーとOS権限が前提です。

試験では専用の実SSH/MariaDBと生成データを使い、実プロセスを停止して5分以上経過させます。ブラウザ表示はその試験の記録を用い、表示試験用の時刻を再設定します。原本の停止時間は変更しません。既存72時間観測や本番の資産は使いません。
