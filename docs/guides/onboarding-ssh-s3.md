# 取得判定から実SSH・実験S3を通した隔離復元（専用試験）

試作版0.1.0-dev.1。PR #5後の接続検証であり、本番配置・正式リリース・72時間観測の最終評価とは別。既存の棚卸し、取得、S3、署名、復元、結果登録を再利用する。

## 経路

1. 新しいnetwork noneのWordPress/MariaDBに生成投稿と画像を用意する。
2. 同じDBとWordPressファイルを対象とする専用SSH endpointを作る。DBは専用SELECTユーザー、サイトは読取り専用マウント、専用クライアント鍵・固定ホスト鍵・固定コマンドを使う。接続先は専用コンテナで、本番サイトではない。
3. 既存host-inventory-ssh.inspectで実測し、導入前検査へ結合。誤ったホスト鍵はunavailableとなり、正しい鍵へ戻した実測だけを使う。更新経路などプローブで確認できない項目は担当者確認として残す。
4. 日次用確認を発行し、tick_admittedへ渡す。取得は既存DockerBackendで同じ生成WordPressを停止・排出・取得・解除する。取得自体のSSHリモート化を新たに実装した試験ではない。
5. 既存queue-s3-adapterで実験バケットへDB/ファイルを保存。communityへのSSHでwriterロール、dmへのSSHでreaderロールを確認し、期限付きの対象限定要求で転送する。認証情報や署名URLはログへ保存しない。
6. 保存完了と承認待ちを確認。別ディレクトリの使い捨て試験鍵で候補を署名し、独立文書/鍵ハッシュを使って既存approveで承認する。
7. 取得workspaceを利用不可にし、既存recovery workerが固定Version IDと署名を再検証して隔離復元する。日次状態への結果登録と同一要求の重複防止を確認する。

## 保存先と影響範囲

- 東京リージョンの既存実験バケット `ceri-link-resilience-lock-lab-121426368082`。
- 対象キーは `sites/isolated-queue-lab/sets/AWS-<ランダムID>/` の新規セット。
- writer `my-ssm-role`、reader `OwrM1RecoveryReader`。既存EC2は要求認可にのみ使用し、コード配置・IAM変更・既存FTP/MySQL変更はしない。
- 既存アダプターがVersioning/Object Lock/暗号化/公開遮断を事前確認し、PUTにGOVERNANCEで35日+10分の保持を指定。固定版GETの実応答から保持を検証する。
- DBとファイルの2 PUTのみ。結果不明を再送しない。試験データは保持対象なので、終わっても削除しない。新しい試行で無条件に追加保存しない。
- 署名は試験専用。実運用鍵・USB・72時間観測の台帳/資産/署名は使用しない。

## 実行と失敗時

```sh
python3 -B tools/run-onboarding-ssh-s3-lab.py --execute-lab --output /home/ozeki/.local/share/owr-onboarding-ssh-s3-new/result.json
```

既存のロール設定、SSH接続、Dockerイメージが必要。未使用の私有出力先を選ぶ。再実行前に出力先の `result-private/accepted-daily` の台帳、receipt、transfer-receipts、recovery-attemptsを確認する。結果JSONがないだけで未送信とは判定しない。保存済み・結果不明なら原因を確認して既存の明示的照合/承認/結果登録を利用する。台帳を消して繰り返さない。

## 証明する範囲と残る制限

棚卸しは実SSH、保存/取得は実S3、保持とVersion IDは実応答。宣言inventoryと担当者確認は生成環境の既知構成に基づく。読み取りプローブで全更新経路や無感染は証明できない。

SSHコンテナと取得/署名/復元処理は同じWSLホストにあり、物理障害の独立性や本番の秘密鍵隔離を証明しない。生成資産はnetwork noneの新規DBとその名前空間を共有するWordPressへ復元する。本番コード実行や侵害コードの安全性を保証しない。

WordPress管理画面への定期転送・systemd・再起動は既存の別試験で確認しており、今回同じ一実行内で再検証しない。72時間観測の既知空白と、原因未確定のWebDriver起動問題も別に保持する。

## 結果

2026-10-21の専用試験は9項目成功。実S3へ29,811,488 bytesを2 PUT、固定版GETは保存時・承認時・復元時の計6回。結果不明PUTは0。保持情報とハッシュを検証し、実隔離WordPressで投稿・画像・HTTP 200を確認。結果登録recorded、日次状態restore_verified、試験資源削除まで成功。同一要求の再投入で追加転送なし。SSH4・S3アダプター11・日次判定7の回帰試験も成功。[証拠](../../evidence-public/onboarding-ssh-s3.json)。

今回の実経路では予期しない環境・試験基盤・製品の失敗は確認していない。前回ローカル代替の保持証拠不足とその修正は別記録のまま保持。既知のWebDriver原因未確定も解決扱いにしない。S3試験オブジェクトは保持し、削除やIAM変更はしていない。
