# ホスト上の読取り専用棚卸しと導入前検査

`tools/host-inventory.php` は対象ホストのCLIで動く初期アダプターです。MariaDBへSELECT専用アカウントで接続し、サイトファイルのメタデータを読みます。WordPress・wp-config.php・プラグインは読み込まず、変更や停止を行いません。今回の対応はLinux・PHP 8.1以上＋mysqli・MariaDBです。MySQLへの互換性は未検証です。

## 実測できる範囲

- 対象DBのテーブル数・エンジン、指定prefixのoptions/posts/postmetaテーブルの存在。
- DBのupload_path／upload_url_path、マルチサイト用blogsテーブルの有無。
- 指定したサイトルートのエントリ数・ファイルサイズ合計・リンク・特殊ファイル。
- 実行中PHPの版とOS種別。

blogsテーブルがないことだけでマルチサイト無効とは認定しません。設定ファイルを実行しないため、定数やプラグインが上書きする構成は未確認です。ファイルの内容・ハッシュやDB／ファイルの整合スナップショットも取得しません。取得中の変更を防止する処理はありません。

書込み経路の網羅性と停止制御、キュー／外部依存の不存在、実行イメージとの対応、IAM・保持・署名担当の独立性、未完了処理台帳は自動確認できません。これらを設定からコピーして「実測済み」にしません。

## ホスト側の準備

運用担当者が事前に対象DBだけのSELECT権限と、対象ファイルの読取り権限を用意します。プローブ自体はユーザー作成・GRANT・chmod・サービス変更をしません。DBの読取り専用トランザクションと5秒のSQLタイムアウトを使用します。

以下の環境変数を権限制限された実行環境で渡します。パスワードをコマンド引数・公開設定・チャットへ貼らないでください。

|変数（すべてOWR_INV_接頭辞）|意味|
|---|---|
|SITE / CONFIG_SHA256|対象site_idと今回の構成ハッシュ|
|NONCE|要求ごとに取得側で新しく生成する32桁の小文字16進数|
|DB_HOST / DB_NAME / DB_PREFIX / DB_USER / DB_PASSWORD|対象DB接続情報。SELECT専用アカウント|
|ROOT|正規化されたサイトルートの絶対パス。リンク経由は拒否|

取得側ではNONCEを発行し、結果が戻るまで保持してください。同じ値を使い回さないでください。ホスト側で生成した値を無条件で期待値として採用すると要求への対応確認になりません。

```sh
timeout 35s php -d auto_prepend_file= -d auto_append_file= tools/host-inventory.php
```

結果は標準出力のJSONだけです。保存や転送は担当側で行います。新しい保護されたファイルに保存し、既存報告を上書きしないでください。入力・接続・走査失敗は終了コード2と固定のstageだけを返し、例外や認証値は出力しません。外側のtimeout終了も取得失敗です。DB接続先の監査ログやOSのアクセス時刻など、読取り操作に伴う記録の発生まで抑制するものではありません。

## 導入前検査への接続

```sh
python3 tools/deployment-preflight.py \
  --profile /private/profile.json --inventory /private/inventory.json \
  --workspace /private/capture-work \
  --host-report /private/host-report.json --host-nonce "$REQUEST_NONCE"
```

profileと従来のinventoryは引き続き必要です。追加のhost-reportは64KiB上限で読み込み、site_id・設定ハッシュ・要求nonce・5分以内の時刻を照合します。不一致や不正な型は拒否します。報告の生のパスやDB名を評価結果へ再出力せず、必要な件数と理由を返します。

正常に取得できても `host_unverified_scope_remaining` を残し、最終状態は `needs_configuration` です。非対応エンジン・リンク・外部uploads等を実測した場合は `unsupported`。通信／DB・ファイル取得失敗は環境確認項目、設定や報告の不一致は構成確認項目として区別します。これは未確認を隠して合格させないための仕様です。

nonceと時刻は報告の暗号学的真正性を証明しません。今回の標準コマンドはホスト上の実測とJSON受渡しまでで、SSH配備・ホスト鍵固定・固定コマンド権限の自動構築は未実装です。信頼できる管理経路で取得する必要があり、侵害済みホストによる虚偽報告は検知できません。

## 専用環境での検証

`tools/run-host-inventory-lab.py --output <新しい専用出力先>` は、既存観測から独立したDB／PHPコンテナを新設します。実MariaDBにWordPress形式の生成テーブル、読取り専用マウントに生成ファイルを用意します。WordPress全体をインストールした試験や、本番ホストへの接続ではありません。

SELECT専用アカウント、DBダンプ・ファイルハッシュの保持、設定PHPの非実行、実CLI接続、別の否定試験での書込み拒否、MyISAM検出、リンク検出、nonce不一致、DB停止時の秘匿された失敗を確認します。否定試験用のDB変更・DB停止は準備側だけが行い、プローブは行いません。作成したコンテナは終了時に削除します。

検証結果は [host-inventory.json](../../evidence-public/host-inventory.json)。既存の72時間観測・本番DB・IAM・署名鍵には触れません。

SSHによる取得と権限制限は [SSH棚卸し手順](host-inventory-ssh.md) を参照してください。
