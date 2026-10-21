# 外部設定生成・systemd配置 PRレビュー

## 範囲

0.1.0-dev.1の試作版。限定構成の導入計画と設定下書き、既存SSH/定期ワーカー/systemdの専用環境配置、ZIP導入/同一コード置換と保持の証拠をまとめる。WordPress本体・共通部品・Backup for S3は変更しない。本番自動配置、稼働中サービス更新、S3/署名/復元の新規実行、正式リリースは対象外。

生成処理はオフライン。既存出力を拒否し、新規ディレクトリとファイルを0700/0600で作成する。DB認証・通知先・ホスト鍵確認・ACL・ユーザー・独立棚卸し・サービス対応付けを必須手作業として残し、production_ready/apply_supportedはfalse。ホスト名の分離は物理障害領域の証明ではない。

## 固定済み成果物

`dist/candidate-20261021-deployment-final`。ZIPは検証後に再生成しない。

- Plugin: `fc6175a7497b63009c3e11654ce52b1535611084e136b80298186d3cf849fb58`（前回候補と同一バイト）
- Kit: `ed57169791d61a8d3a270cfacf4021712e8a689f0500f2cdca18f963b3b88a3e`

検証後の文書・証拠追記は固定キットに含まれない。ステージ済み内容をmanifestと照合し、コードの差は `lab/external-deployment-plan/exercise.py`、`tests/test_external_deployment_plan.py`、`tools/run-deployment-zip-lab.py` のCRLFからLFへの改行正規化だけであることを確認した。文書差はZIP結果追記と現状更新。CIはPRツリーから別のキットを構築するため、追加資料により固定キットとはハッシュが異なる。

## 実証済み範囲

設定生成19契約テスト、オフライン配置計画9項目、実SSH配置13項目、3VM systemd24項目とブラウザ5場面、展開キット5項目とWordPress ZIP新規導入/置換・設定/Cron/要求/外部報告・台帳保持。3VMは同一物理PC、WordPressへの最終ファイル渡しは9p。通知は試験ローカル受信先。

[配置](../guides/generated-deployment-lab.md)・[systemd](../guides/generated-systemd-lab.md)・[ZIP](../guides/deployment-zip.md)に証拠と制限を記載。

## 問題を混同しない

- 専用SSHサービスの/run/sshd再作成不足：今回の試験基盤不備。原因特定、RuntimeDirectory追加、OS再起動再検証済み。
- WebDriver POST /sessionタイムアウト：WordPress画面へ移動前の試験基盤症状。根本原因未確定。事後のメモリ確認では発生時の状況は証明できない。ready確認・診断保存を追加したが、後続成功で過去原因を確定しない。
- 以前のログイン遷移失敗も原因未確定として保持。永続的な報告不整合は試験失敗とし、公開途中のみ最大15秒の収束待ちを記録する。
- 72時間観測は別判定。3日次枠成功と72時間実経過と観測網羅性を別々に評価する。最短到達2026-10-22 15:55:56 JST。既存の4時間26分33秒・4時間24分8秒の空白を埋めない。

## 最終確認

差分、公開対象の秘密情報パターン、固定ZIP対応、契約テストとGitHub CIを確認する。マージ・タグ・ReleaseはこのPR作成では実施しない。

ローカル最終確認：宣言済み依存を入れた専用venvでPython565テスト成功、PHP9スクリプト154項目成功、差分書式・秘密情報パターン・固定ZIPのハッシュ照合成功。PHPの最初の呼出しはシェル引用/CRLFでテスト開始前に失敗したため、Python subprocessによる呼出しへ変更して全件実行した（製品不具合ではない）。
