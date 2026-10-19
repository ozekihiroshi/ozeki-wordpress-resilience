# 開発候補ZIPの導入・停止・再開

この手順の対象は通知管理画面の開発候補。バックアップの開始手順ではない。[機能境界](../releases/plugin-candidate-scope.md)を先に確認する。初回は専用WordPressで試す。

## WordPressへ入れる

1. 配布物のうち `ozeki-wordpress-resilience-0.1.0-dev.1.zip` を手元に用意する。`owr-development-kit` は選ばない。ZIPを展開してから再圧縮する必要はない。
2. WordPressへ管理者でログイン。「プラグイン」→「新規プラグインを追加」→「プラグインのアップロード」を開く。
3. ZIPを選択し「今すぐインストール」。完了後「プラグインを有効化」を押す。
4. 左側の「Resilience」→「通知」を開く。開発・評価版と外部処理が必要な旨の案内が表示される。
5. 外部処理の配置前は、配送状態が未取得になる。これは保護成功を意味しない。初回はここまでで本体導入の確認ができる。

PHP 8.1以上が必要。ZIP用のComposer installやAWS SDK導入は不要。ファイル書込み権限不足でインストールできなければ、サイト管理者へWordPressのプラグイン導入権限を確認する。サイト全体の権限を緩めない。

## 通知先を設定する

1. 「Resilience → 通知」で新しい通知先を追加する。表示名、方式、接続設定名、宛先表示名またはメールアドレス、対象警報を入力し保存する。
2. 接続設定名は外部担当者が用意する参照名。Pushoverキー・SMTPパスワード・AWSキー・署名鍵は入力しない。
3. 保存は設定候補の更新。外部側への反映と配送成功は別。外部連携前にテスト送信しても端末へ届かない。
4. 外部処理の配置には[設定と橋渡し](wordpress-notification-admin-lab.md)、[専用SSH転送](notification-transfer.md)、[定期実行と停止](notification-runtime.md)を使う。これは外部管理者が行う作業で、ZIPの有効化では代行されない。
5. 連携後はテスト要求のIDと配送結果を照合し、サービス受付だけでなく実際の端末受信を確認する。独立watchdogは[専用設定](observer-settings.md)も必要。

## 停止と再開

「プラグイン → インストール済みプラグイン」で本製品の「無効化」を押す。WordPress内の設定を保持する。再開は「有効化」し、以前の通知先が残っていることを確認する。

本体の無効化では外部worker・relay・watchdogは止まらない。全体を止める場合は、外部側の登録済み専用timerを止め、実行中処理の終了を確認する。既存FTP/MySQLや他サービスを止めない。状態台帳・未配送・信頼情報は削除しない。再開は同じ台帳を使用する。[外部手順](notification-runtime.md)参照。

プラグイン削除時の設定自動消去は未実装。停止と設定消去は区別する。

## 開発者が専用環境で同じ検証を行う

WSL Ubuntu、Docker、Python依存、ローカルのWordPress/MariaDB/Chromiumイメージが必要。[開発環境](development-setup.md)を参照。今回の試験中は外部ネットワークを閉じ、実メールやPushoverは送らない。

リポジトリまたは展開した開発キットのルートで実行する。出力先は毎回新しい名前にする。

```sh
python3 tools/build-release.py --output dist/my-candidate
python3 tools/run-notification-admin-lab.py \
  --plugin-zip dist/my-candidate/ozeki-wordpress-resilience-0.1.0-dev.1.zip \
  --output .local/my-package-install-test
```

result.jsonのcontainers_removed=true、失敗なし、plugin_zip_sha256と配布manifestの一致を確認する。この試験はWordPress標準Plugin_Upgrader APIでZIPをインストールし、実管理画面をHTTP/Chromiumで検証する。ブラウザーのZIP選択・アップロード操作そのものを自動試験したとは扱わない。

専用fixtureが外部状態・要求フォルダを準備し、通知サービスは模擬である。管理画面と外部境界の試験結果を、本番のメール配送やバックアップ復旧の受入結果へ読み替えない。
