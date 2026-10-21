# 外部処理の設定下書きと読取り専用の導入計画

試作版。対象はSSH棚卸し、導入前検査、独立watchdog、WordPressへの状態受渡し。取得・S3保存・署名・復元の設定と起動は対象外で、[担当者操作](first-site-operator-runbook.md)の既存手順に従う。

## 1 入力を準備する

WSL Ubuntuでリポジトリへ移動する。収集プロファイルは既存形式を使用する。`examples/first-site/generated-lab.json` と `examples/deployment/generated-topology.json` は生成データ専用の例で、本番用ではない。

topologyのsite_idをプロファイルと一致させ、hostsのinventory（棚卸し対象）、scanner（検査実行）、wordpress（表示先）、observer（独立監視）のhost、port、userを記入する。site_idは先頭が英小文字で、32文字以内の英小文字・数字・ハイフン。scanner、wordpress、observerは別のホスト名にする。ホスト名の相違だけで物理的な独立性を証明したことにはならない。SSH秘密鍵・パスワード・通知トークンはこの入力へ書かない。

## 2 計画だけを表示する

```sh
python3 -B tools/external-deployment-plan.py plan   --profile examples/first-site/generated-lab.json   --topology examples/deployment/generated-topology.json
```

JSONを標準出力へ表示するだけで、ファイル作成・SSH接続・DB照会・サービス操作はしない。`files` は予定配置先・所有者・モード・下書きのハッシュ、`directories` は予定ディレクトリ、`host_key_pins` は6経路の鍵参照、`ssh_endpoints` は固定コマンド、`commands` は実行案、`required_actions` は未設定事項。

終了コード0は計画作成成功のみ。`production_ready:false`、`apply_supported:false`、`requires_operator_configuration`を維持する。入力不正は終了コード2。計画モードに`--output`は指定できない。

## 3 新しいフォルダーに下書きを作る

```sh
python3 -B tools/external-deployment-plan.py generate   --profile examples/first-site/generated-lab.json   --topology examples/deployment/generated-topology.json   --output /home/ozeki/owr-generated-plan-01
```

出力先は既存の親ディレクトリ配下の未作成絶対パスを指定する。WSLのLinuxファイルシステムを使う。既存フォルダー、シンボリックリンク経由、相対パスへの生成は拒否する。フォルダー0700、ファイル0600で生成し、既存設定を上書きしない。`plan.json`は最後に作る。途中失敗時は部分出力を残すため、その内容を確認し別の新規フォルダーで再作成する。自動削除・自動再開はしない。

## 4 担当者が確認する事項

- `inventory/endpoint.draft.json`のDB_USER・DB_PASSWORDはnull。対象ホストでSELECT専用認証を設定する。下書きのまま起動しない。
- scannerへ実際に収集した独立の棚卸し情報と確認済みプロファイルを配置する。プロファイルの複製を検査証拠にしない。
- 各SSH経路は別鍵と固定コマンドに制限する。`host_key_pins`の別名とホスト鍵を帯域外で照合する。shell・転送権限は与えない。計画に示すknown_hostsや鍵ファイルは生成されない。
- observerの設定は通知先を含まない。既存の通知設定形式に従って設定し、実際の配送を確認する。下書きの実行や正常表示は警報配送の証明ではない。
- Python/PHP/mysqli、実行ユーザー、コード所有者、設定への読取り権限、親ディレクトリの通過権限を確認する。計画の所有者・モードは案で、実ホストでの検証結果ではない。
- `commands`のargvと設定パスを既存systemdテンプレートへ明示的に対応付ける。既存テンプレートの既定設定パスと生成パスは異なるため、コピーだけで起動しない。サービス作成・enableは本ツールでは実行しない。
- `wordpress/wp-config.fragment.php`は既存定義との重複を確認して手作業で統合する。wp-config.phpを置換しない。WordPressにSSH鍵や台帳の書込み権限を渡さない。
- 既存ファイル・ロック・台帳との衝突を確認する。表示用報告、私有台帳、信頼情報をそれぞれ保持する。

## 検証と制限

[専用検証記録](../../evidence-public/external-deployment-plan.json)：単体19件、network none・ルート読取り専用の専用コンテナで9項目。計画の無変更性、生成との一致、ハッシュ、上書き拒否を確認。実SSH、systemd配置、OS再起動、実DB・S3・署名の試験ではない。それらの既存検証を再実施したとは扱わない。72時間観測のデータ、鍵、台帳へ接続しない。

[生成設定から専用環境への配置検証](generated-deployment-lab.md)：既存SSH/定期処理/独立watchdog/WordPressを再利用。限定専用環境での導入経路の検証で、本番自動配置ではありません。

[systemdへの対応と停止・再起動の手順](generated-systemd-lab.md)：既存サービスを再利用し、60秒周期、実停止・再開、OS再起動後の自動起動と画面回復を専用環境で確認。
