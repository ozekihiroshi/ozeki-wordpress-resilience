# 日次状態報告：本番向けsystemd設定とOS再起動

この手順は外部の状態報告サービス用です。バックアップや復元は起動しません。
WordPressのプラグインZIPだけでは配置は完了せず、ホスト管理者による外部サービスの設定が必要です。

## 構成と所有者

生成ホストに `owr-daily-status-publisher.service`、WordPressホストに
`owr-daily-status-relay.service` を配置します。両方とも通常のシステムサービスで、
ログイン中のユーザーサービスやWP-Cronには依存しません。

|対象|必要な権限|
|---|---|
|`/opt/owr/tools` と `/opt/owr/schemas`|root所有。サービスとWebユーザーは変更不可|
|生成用ユーザー `owr-status-publisher`|元の台帳・参照証拠を読取り。書込みは公開報告ディレクトリだけ|
|SSH読取りユーザー `owr-status-reader`|公開報告だけ読取り。元の台帳・取得用秘密鍵は不可|
|取得用ユーザー `owr-status-relay`|専用SSH鍵を読取り。書込みはWordPress向け報告ディレクトリだけ|
|Webユーザー（例：`www-data`）|受信済み報告を読取り。台帳・SSH秘密鍵へのアクセスや報告の変更は不可|

サービス用ユーザーと共有グループは導入先の管理方針に従って作成します。
例の生成サービスは `Group=owr-status-read`、取得サービスは `Group=www-data` を使います。
生成サービスには、元の台帳を読むための専用グループを補助グループとして付与します。
元のバックアップ処理の所有権を一括変更せず、必要な台帳・証拠だけを読める構成にしてください。
SQLiteがWALを使用する導入先では、実際の更新中にも読取りが成立することを配置時に確認します。
状態表示のために台帳への書込み権限を追加する運用にはしません。

公開用ディレクトリはそれぞれサービスユーザー所有、共有グループ読取りの2750とします。
設定はroot所有の0640で対応するサービスだけが読めるグループ、
取得用秘密鍵は `owr-status-relay` 所有の0600とします。
親ディレクトリの通過権限も `namei -l パス` で確認してください。
SSH強制コマンド・鍵・ホスト鍵固定は [定期更新手順](daily-status-periodic.md) に従います。

## サービスに設定した制限

- `ProtectSystem=strict` と `ReadWritePaths`：書込み先を各報告ディレクトリに限定。
- `ProtectHome=yes`：ホームディレクトリを参照しない。鍵・状態は `/etc/owr`、`/var/lib` に置く。
- `PrivateTmp=yes`：一時領域をほかの処理と分離。
- `NoNewPrivileges=yes`、空のcapability集合：権限昇格を禁止し、不要なLinux権限を外す。
- デバイス、カーネル設定・モジュール・ログ、制御グループ、時計、ホスト名を保護。
- 名前空間作成、SUID/SGID変更、リアルタイム設定、実行可能メモリの扱いなどを制限。
- ソケットの種類をUNIX・IPv4・IPv6に限定。これは接続先IPの許可リストではない。
- 生成サービスだけ `PrivateNetwork=yes`：台帳のローカル読取りにネットワークは不要。

取得サービスにはSSH通信が必要です。導入先で接続先を絞る場合は、別途ネットワーク側でも制限します。
これらは非管理者サービスの制限であり、rootやホスト自体の侵害を防ぐ保証ではありません。
生成ホストの侵害から独立した復旧の信頼性は、保管・権限分離・署名の仕組みで別に扱います。

## 配置・有効化

設定ファイルのパス・サイトID・接続先を準備し、対応ユーザーの単発実行が成功することを確認します。
本番データの台帳は既存のものを読み、生成側と取得側で出力先を共有しません。

サービスファイルは実行権限を付けず配置します。生成ホストの例：

```sh
sudo install -o root -g root -m 0644 \
  examples/daily-status-transfer/owr-daily-status-publisher.service \
  /etc/systemd/system/owr-daily-status-publisher.service
sudo systemd-analyze verify /etc/systemd/system/owr-daily-status-publisher.service
sudo systemctl daemon-reload
sudo systemctl enable --now owr-daily-status-publisher.service
sudo systemctl is-enabled owr-daily-status-publisher.service
sudo systemctl status owr-daily-status-publisher.service
```

取得ホストでは `publisher` を `relay` に置き換えます。
`enabled` は起動時の登録、`active` は現在の稼働状態です。両方を確認します。
標準周期は60秒。起動順や通信失敗により最初の取得が失敗しても、次の周期で再試行します。
WordPressの「日次バックアップ・復元」で取得成功と観測時刻の更新を確認してください。
「取得成功」は状態報告の転送結果であり、新しいバックアップを作成した意味ではありません。

`systemctl stop` は現在の処理を止めますが、自動起動の登録は残します。
再起動後も停止させたい場合は `systemctl disable --now` を使います。
台帳・報告・鍵は削除せず、再開時は `enable --now` で戻します。

## 専用VMで確認した範囲

Ubuntu 24.04の独立したKVMゲストで、例のサービスファイルをそのまま使いました。
生成・取得は同一ゲストの別ユーザー、SSHは実接続、データは既存試験用データのコピーです。
外部ネットワークを持たないQEMU実行コンテナで、既存WSL・Docker・72時間観測は再起動していません。

再起動前後に、実行中プロセスのUID・capability・NoNewPrivileges・seccompと、
マウント名前空間内での書込み拒否、ホーム遮断、一時領域分離、ファイル権限を確認しました。
OS再起動でゲストのBoot IDが変わり、手動startなしで両サービスと状態報告が回復しました。
元データのバイト列、過去の復元結果、ホスト側Boot IDは維持されています。

`systemd-analyze security` は設定の点検補助であり、点数だけで安全性を判定していません。
詳細と再起動前後の証拠は [公開検証結果](../../evidence-public/daily-production-systemd.json) にあります。
旧設定の検証結果も別に保持し、制限を補強した後に再起動を含む試験を繰り返しました。

未検証：別物理ホスト間、他のLinux/systemd版、ホスト電源断、本番への配置。
今回の専用VMは試験終了後に停止・撤去します。生の証拠には試験専用鍵やVMディスクも含むためGitへ登録しません。
再現用スクリプトは `lab/systemd-vm/` にあります。新規の専用出力先を使い、既存試験を上書きしないでください。


後続の[別VM障害回復試験](daily-two-vm-recovery.md)で、生成・取得を独立VMに分けた通信断・片側OS停止・起動後の自動回復を確認しました。別物理ホスト間の検証は引き続き未実施です。
