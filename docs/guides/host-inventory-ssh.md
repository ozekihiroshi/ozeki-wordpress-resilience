# SSH経由の読取り専用ホスト棚卸し（試作）

この入口はホスト側のMariaDB・ファイルの実測を導入前検査へ渡します。設定変更、バックアップ、署名、通知は行いません。更新経路・キュー・信頼管理など未確認項目は残るため、SSH取得成功だけで本番導入可能とは判定しません。

## 1. 対象ホストを管理者が準備する

専用の `inspector` OSユーザーと、対象DBだけのSELECT権限を持つDBユーザーを用意します。sudo、Dockerソケット、通常業務の管理権限を与えません。サイトは読取り・ディレクトリー検索だけを許可します。ACLは管理者が設定し、このツールから変更しません。

`host-inventory-ssh.py`、`notification-transfer.py`、`host-inventory.php` を `/opt/owr/` に配置します。ディレクトリーとコードはroot所有で専用ユーザーから書込み不可にします。Python 3、PHP 8.1以上のmysqli、MariaDBが必要です。WordPressのコードは起動しません。

`/etc/owr/endpoint.json` をroot所有・専用ユーザーのグループ・0640にします。site_idとconfig_sha256は検査対象プロファイルの値に固定します。ハッシュは既存導入前検査のconfig_sha256と同じ正規化形式です。DBパスワードをコマンドラインや公開リポジトリへ記載しないでください。

```json
{
  "site_id": "example-site",
  "config_sha256": "プロファイルの64桁ハッシュ",
  "php": "/usr/local/bin/php",
  "probe": {
    "DB_HOST": "127.0.0.1",
    "DB_NAME": "example_db",
    "DB_PREFIX": "wp_",
    "DB_USER": "inspector",
    "DB_PASSWORD": "対象ホストで設定",
    "ROOT": "/var/www/html"
  }
}
```

PHPの絶対パスは実ホストに合わせます。独立した検査用SSH公開鍵に、以下のauthorized_keys制限を設定します。鍵ファイル自体もroot管理とし専用ユーザーが変更できない場所に置きます。

```text
restrict,command="/usr/bin/python3 -B /opt/owr/host-inventory-ssh.py endpoint --config /etc/owr/endpoint.json" ssh-ed25519 公開鍵
```

sshdの対象ユーザー用設定で `PasswordAuthentication no`、`KbdInteractiveAuthentication no`、`DisableForwarding yes`、`PermitTTY no`、`PermitUserEnvironment no` を指定します。既存SSH全体を置換せず、管理者がMatch User等で適用してください。通常のシェル要求、別サイト指定、任意コマンドは拒否されます。SSHユーザーがDBのSELECT秘密情報を読めることは必要な権限であり、root侵害からの隔離を保証する構成ではありません。

## 2. 検査側を準備する

専用秘密鍵を0600で保存します。対象ホスト公開鍵は管理者から別経路で照合し、known_hostsへ `owr-inventory-example-site ssh-ed25519 ...` として登録します。初回接続時の自動信頼や自動鍵更新はしません。

```json
{
  "site_id": "example-site",
  "host": "host.example.net",
  "user": "inspector",
  "port": 22,
  "identity_file": "/secure/inventory-key",
  "known_hosts": "/secure/inventory-known-hosts"
}
```

接続先はホスト名またはIPv4を指定します（この初版ではIPv6リテラル未対応）。設定と鍵・known_hostsは他ユーザーが書換えられないよう管理します。

## 3. 導入前検査を実行する

既存のプロファイル、申告棚卸し、0700作業領域を用意し、以下を実行します。

```sh
python3 -B tools/host-inventory-ssh.py inspect \
  --config /secure/connection.json \
  --profile /secure/profile.json \
  --inventory /secure/inventory.json \
  --workspace /secure/work
```

結果は標準出力JSONだけです。検査自体は結果ファイルや前回値を書き換えません。SSHは接続10秒・応答全体20秒、ホスト側PHPは15秒で打ち切ります。上限を超える大規模サイトは未取得として扱います。要求は1024バイト、PHP応答は64KiB、SSH応答にも転送層の上限があります。

`host_observation.state=validated_report` は実測の形式・サイト・プロファイル・今回のnonce・鮮度を検査できた状態です。SSHのホスト鍵確認はホストの健全性やマルウェア不在の証明ではありません。`authenticated=false`という既存の棚卸し属性は独立した実測証明がないことを示し、SSH鍵の照合とは区別します。

通信断、鍵不一致、タイムアウト、不正応答は `unavailable` とし終了コード2を返します。前回成功で代用しません。原因未確定のSSH失敗は `unclassified` とし、運用者が接続・権限・応答を調査してから環境問題／設定問題／製品問題へ分類します。正常転送されたDB・ファイル検査失敗は既存の検査失敗として表示します。

## 検証範囲

専用コンテナー間の実OpenSSH、実MariaDB、生成したWordPress形状のテーブルとファイルで検証します。実サイト、既存EC2、72時間観測の資産には接続しません。独立した物理ホストの障害耐性・本番ACL・全WordPress構成の対応は、この試験の合格範囲に含みません。
