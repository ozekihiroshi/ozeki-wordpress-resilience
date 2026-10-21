# 別VM間の導入前検査結果の受渡し

検査側VMでSSH棚卸しを実行し、WordPress側VMがその公開用報告だけを固定コマンドSSHで取得します。共有の報告ディレクトリーは使いません。WordPress側に検査対象DBの資格情報や棚卸し用SSH秘密鍵を配置しません。

## 検査側

[systemd手順](preflight-systemd.md)の `owr-preflight.service` を配置します。公開報告の読取りだけが可能な専用ユーザーを追加し、状態・秘密情報の0700ディレクトリーは読めないようにします。専用ユーザーにsudoやDocker権限を与えません。

固定コマンド用の設定はサイトID、プロファイルハッシュ、報告と更新記録のパスだけです。

```json
{
 "site_id": "example-site",
 "config_sha256": "64桁のプロファイルハッシュ",
 "report_file": "/var/lib/owr-preflight-web/report.json",
 "health_file": "/var/lib/owr-preflight-web/health.json"
}
```

root管理のauthorized_keysに、WordPress側の専用公開鍵を以下の制限付きで登録します。

```text
restrict,command="/usr/bin/python3 -B /opt/owr/tools/preflight-transfer.py serve --config /etc/owr/read.json" ssh-ed25519 公開鍵
```

sshdの該当ユーザーには公開鍵認証のみ、転送禁止、TTY禁止を設定します。任意コマンド、別サイト、別設定版、不正な要求は拒否します。報告と更新記録が一致しない場合も配送成功にしません。

## WordPress側

`owr-preflight` 専用ユーザーと非公開ディレクトリー、WordPressが読取りだけできる報告ディレクトリーを用意します。受渡し専用秘密鍵は0600で非公開領域へ置きます。検査側ホスト公開鍵は別経路で照合し、known_hostsへ `owr-preflight-example-site ssh-ed25519 ...` の形式で登録します。

```json
{
 "site_id": "example-site",
 "config_sha256": "64桁のプロファイルハッシュ",
 "host": "検査側ホスト名",
 "port": 22,
 "user": "owr-reader",
 "identity_file": "/var/lib/owr-preflight/transfer-key",
 "known_hosts": "/var/lib/owr-preflight/known",
 "report_file": "/var/lib/owr-preflight-web/report.json",
 "health_file": "/var/lib/owr-preflight-web/health.json",
 "lock_file": "/var/lib/owr-preflight/loop.lock"
}
```

`examples/preflight-relay/owr-preflight-transfer.service` を配置し、以下を実行します。

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now owr-preflight-transfer.service
systemctl status owr-preflight-transfer.service
```

WordPressの報告パスと更新記録パスは、このVMのファイルを指します。ファイルと親ディレクトリーはサービスユーザーだけが書けるようにし、WordPressには読取りだけを許可します。同じ出力へ検査サービスと転送サービスを同時に書かせないでください。

## 通信断・停止時

- 通信断：直前の検査結果を残し、受渡し失敗を表示します。
- 検査側の処理停止：SSHが通っても元の検査時刻を維持します。5分以上古い場合は検査側の更新停止を表示します。
- WordPress側の転送停止：最後の転送時刻が5分以上古くなると更新停止を表示します。
- 回復：新しい報告と転送記録が揃えば表示が回復します。
- WordPress側OS自体の停止：その間は管理画面も利用できません。再起動後にWebサービスと受渡しサービスが起動してから確認します。

転送は許可した項目だけを渡し、出力容量、サイト・設定版・要求nonceを検査します。前回より古い検査時刻や、同じ時刻なのに内容が違う報告は拒否します。ホスト鍵の照合は検査内容の独立署名証明ではありません。

## 専用試験の範囲

独立したUbuntuゲストカーネル2台を同じ物理ホスト上で使用し、ゲスト間データNICの切断、検査サービスの実停止、両ゲストのOS再起動を試します。WordPress PHPは受信側ゲスト内で実行します。生成DBと棚卸し対象ファイルは専用の外部コンテナーに置くため、DBを含めた全資産の単一VM障害試験ではありません。実サイト、既存EC2、72時間観測の資産は使いません。

## 検証結果

専用2VM試験の結果は [公開用記録](../../evidence-public/preflight-two-vm.json) にまとめています。通信断と回復、検査側の実停止310秒以上、両VMのOS再起動とサービス自動起動、WordPress画面の回復を確認しました。各画面ではログイン・管理者権限・POST拒否・モバイル表示も確認しています。

初回は試験準備のアーカイブが180秒でタイムアウトしたため、配布対象ファイルだけをLinux側へ配置する方式に修正しました。補助照会のWSL接続タイムアウトとゲスト照会タイムアウトも別記しています。試験の成功で過去の失敗を消していません。

管理画面とは独立した警報・回復通知の接続は [導入前検査watchdog](preflight-watchdog.md) に記載しています。
