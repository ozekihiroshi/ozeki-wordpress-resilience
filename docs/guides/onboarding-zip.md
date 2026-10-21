# 導入・復旧接続の固定ZIP受入

0.1.0-dev.1の試作版。PR #5以降の追加は接続試験と文書で、プラグイン本体の変更はない。新旧のplugin ZIPが同じハッシュになる場合、更新試験は同一内容の再配置であり、新しい製品コードへの移行とは呼ばない。development kitはSSH/S3接続検証と証拠を含む。

既存run-deployment-zip-labの --operator-review に --preserve-state を追加。完了済み実SSH/S3試験のresult-privateからJSON/SQLite/公開鍵/署名のコピーを作り、新規導入・実Plugin_Upgrader上書き・無効化/再有効化の前後でバイト列を比較する。秘密鍵を含む入力は拒否。元の試験領域は読取りだけで、S3保存・再署名・再復元を起動しない。

既存の非既定設定、Cron、wp-config、要求記録、外部監視履歴、担当者確認・承認待ちのfixtureも保持検査する。ブラウザで状態の鮮度、editor拒否、POST405を確認する。コピー内の絶対パスは変更しないため、作業領域移行・そのコピーからの再開・SQLite形式移行の証明ではない。

固定配布物は新しいdistフォルダに生成してmanifest/SHA256を記録する。試験後の証拠はZIP外で追記し、固定ZIPを上書きしない。72時間観測、正式公開、本番環境は対象外。過去の試験用保持記録不足は修正済みの試験基盤問題として保持し、原因未確定WebDriver問題も別に残す。

## 結果

新規導入と前回検証済みcandidate-20261021-admission-validatedからの実上書きが成功。設定/Cron/wp-config/要求/監視・確認履歴の不変と、実SSH/S3接続試験由来の32記録の保持・原本不変を確認。ブラウザで情報の鮮度、権限、読取り専用性を確認。外部設定生成5検査とZIP内コードの回帰22件も成功。試験コンテナ削除済み。[証拠](../../evidence-public/onboarding-zip.json)。

配布物：`dist/candidate-20261021-onboarding-final`。
- ozeki-wordpress-resilience-0.1.0-dev.1.zip：35,162 bytes、SHA256 `0537301b4f85b52cbd363c2b5909806b367c5a3d9bc40933325b31f88af51cfb`。
- owr-development-kit-0.1.0-dev.1.zip：14,456,575 bytes、SHA256 `6c410d8d7ce73af20b0f53ba6f6b91434c66c4ad725e90ab2d531090868686d1`。

plugin ZIPは前回と同一内容。kitだけが変更されており、新版製品コードへの移行とはしない。結果文書は固定ZIPの外に追記し再ビルドしない。新たな環境/試験基盤/製品障害は確認していない。以前のブラウザ原因未確定と前回の試験fixture失敗記録は保持。
