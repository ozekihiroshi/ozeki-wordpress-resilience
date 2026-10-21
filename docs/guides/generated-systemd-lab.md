# 生成設定のsystemd配置と再起動検証

試作版の外部設定を、検査側・受渡し側・独立watchdog側の3つの専用Ubuntu VMへ配置する。既存のSSH棚卸し、preflight publisher/receiver、watchdog、observer status pullを再利用する。設定パス・サイトID・monitor IDは生成値を使い、変更点は下記に限定して記録する。

## サービスへの対応

|専用VM|生成設定|systemd|
|---|---|---|
|検査側|scanner/publisher.json|owr-generated-publisher.service、60秒周期|
|受渡し側|wordpress/receiver.json|owr-generated-receiver.service、60秒周期|
|受渡し側|wordpress/source-pull.json、receiver-pull.json|owr-generated-source-pull.service、owr-generated-receiver-pull.service、60秒周期|
|独立watchdog|observer/source-observer.json、receiver-observer.json|各owr-generated-*-observer.service（oneshot）と.timer（60秒周期）|

既存のexamples/preflight-relay、examples/observer-status-relay、examples/watchdog-observerを使い、ExecStartの設定パスとReadWritePaths/RequiresMountsForを生成値へ対応付ける。Userを役割ごとに分け、NoNewPrivileges、ProtectSystem=strict、ProtectHome、PrivateTmpを維持する。今回の専用環境では読取りグループにwww-dataを使用する。本番は各ホストの権限設計を別途確認する。

SSH固定コマンド用sshdとローカルSMTP受信先も専用サービスで起動する。SMTPは試験VM内の127.0.0.1:1025だけを使用し、外部へメールは送らない。既存sshdを置き換えない。

## 専用試験を実行する

既存のVMイメージ・Docker試験イメージを準備したWSL Ubuntuで、未作成の出力ディレクトリを指定する。

```sh
python3 -B tools/run-generated-systemd-lab.py --output /home/ozeki/.local/share/owr-generated-systemd-NEW
```

出力先には専用鍵・VMディスク・私有設定を含むため公開しない。公開証拠には結果と画面だけを抽出する。試験ネットワークは外部接続用ポートを公開しない内部Dockerネットワーク。VMのSSH固定エンドポイントを、このネットワーク内だけで到達可能にする。管理用SSHは別のローカル転送口と鍵を使う。

## 検証の順序

1. 生成設定を配置し、SELECT専用DB認証・ホスト鍵・ローカル通知先を補完する。生成設定だけで本番導入可能とはしない。
2. enable --nowで定期処理を起動し、60秒周期の実更新、各サービスのUser/Group/制限、重複起動の拒否を確認する。
3. 専用WordPressから正常状態を確認する。全対象サービス・timerを停止し、報告ファイルが変わらないまま実時間で310秒以上経過することを確認する。時計・報告時刻は書き換えない。
4. 管理画面の更新停止表示を確認後、同じ設定・台帳で再開し、回復表示を確認する。
5. 3VMのOSを実際に再起動する。Boot IDの変更と、手動startなしで定期更新が戻ること、管理画面の回復を確認する。WSLホストのBoot IDは不変であることを確認する。
6. 試験専用VM・コンテナ・ネットワークだけを除去する。失敗記録・証拠は残す。

## 境界

本番、IAM、S3保存、署名鍵、既存FTP/MySQL、72時間観測の環境・台帳を変更しない。3VMは同じ物理PC上なので物理障害領域の分離試験ではない。WordPress画面への最終表示ファイルはVMから9p共有で渡す。VM間の実際の報告取得は固定鍵SSHを使う。独立watchdogの実通知サービス・iPhone再検証を行ったとは扱わない。

以前のDockerアドレス不足は空きサブネット探索を再利用して回避する。ブラウザはログインセッションを分離し、反映途中の不整合は最大15秒の収束確認とする。持続する不整合は失敗。今回新たに生じた問題は、環境・試験基盤・製品・原因未確定を区別して結果へ残す。

## 再起動試験で修正した試験基盤の不備

初回は停止・再開まで成功し、OS再起動後に専用SSHサービスが `Missing privilege separation directory: /run/sshd` で失敗した。`/run` は再起動で失われるため、初期配置時のmkdirだけでは不十分だった。専用サービスに `RuntimeDirectory=sshd` とモード0755を指定し、既存sshdと共有するディレクトリを停止時に消さないよう `RuntimeDirectoryPreserve=yes` を追加した。これは今回の試験用サービス定義の不備であり、原因不明の環境タイムアウトやプラグインの検査判定不具合として扱わない。初回の失敗記録は私有試験出力に保持し、修正後の新しいVMで再検証する。

修正後2回目は、WordPress画面へ移動する前のWebDriver新規セッション作成が60秒でタイムアウトした。終了後に資源不足は確認できず、当該時点のSeleniumログが不足しているため根本原因は未確定。プラグインの表示不良や環境のメモリ不足とは断定しない。試験基盤に `/status` のready確認と終了前のSeleniumログ・コンテナ状態保存を追加した。これは前回原因の証明ではない。失敗出力はv2として保持する。

## 最終結果

[公開検証記録](../../evidence-public/generated-systemd.json)に合格結果、Boot ID、再起動前後のユーザーと制限を保存。[停止表示](../../evidence-public/generated-systemd-stopped.png)／[OS再起動後の回復](../../evidence-public/generated-systemd-restarted.png)／[独立watchdog表示](../../evidence-public/generated-systemd-watchdog.png)。専用環境での受入であり、本番配置や正式リリースではない。
