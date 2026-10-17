# 固定版転送とRAM連携の開発手順

2026年10月18日。ロール分離などの環境課題と切り離して、ソフトウェア側の実装を進めた。以下は開発用CLIであり、WordPress管理画面への組込みや本番向け配布は未実施。

## 実装した契約

src/VersionedAssetStore.phpは認証済みAWS SDK呼出しを受け取る小さな転送部品。既存バックアップ製品は変更していない。

保存時は入力サイズ・SHA-256を先に検証し、Versioning=Enabledを確認する。PutObjectへIfNoneMatch=*とSHA-256チェックサムを指定し、既存キーを上書きしない。返された非null VersionIdを受領記録へ固定する。SSE-S3を明示し、ExpectedBucketOwnerとwordpress-test/の範囲も固定する。

取得時は必ずGetObjectのVersionIdを指定する。応答のVersionId、ContentLength、取得した全バイトのSHA-256を照合する。既存出力は上書きしない。検証後に同一ディレクトリ内のハードリンクで公開し、失敗した途中ファイルは除去する。保存先には信頼できるローカルディレクトリを指定する。Linuxファイルシステムが対象で、ハードリンク非対応FSでは失敗する。

保存受領はput_acknowledged、全バイトの取得確認はdownload_integrity_checkedとして区別する。取得成功でもrole_separationとauthenticityはunverifiedのまま。実S3からの取得か、別主体か、信頼できる期待ハッシュかは別途実測・評価する。

## CLIの前提

PHP 8.1以上と固定済み.local/backup-plugin/vendor/autoload.phpを使用する。既存プラグイン同様のAWS SDK標準認証チェーンを使い、長期キー・失効間近の一時認証情報を拒否し、STSでIAMロールと対象アカウントを確認する。CLIにアクセスキー引数はない。

tools/versioned-s3-transfer.phpの引数は次の順番。

    php tools/versioned-s3-transfer.php upload FILE KEY SIZE SHA256 RECEIPT_OUTPUT
    php tools/versioned-s3-transfer.php download RECEIPT_INPUT DESTINATION SIZE SHA256 OBSERVATION_OUTPUT

FILEは収集済み実資産、KEYはwordpress-test/から始まる新しいセット固有のキー、SIZEとSHA256は収集時の期待値。downloadでも信頼できる収集記録からSIZEとSHA256を渡す。受領記録だけを信頼の起点としない。出力記録は新規ファイルとして予約し、既存ファイルは拒否する。

このCLIはクラウドへ実アクセスする。オフライン試験コマンドとは区別する。現在は実S3実行を行っておらず、EC2へのツール配布も未実施。

上限は単一PutObjectの5 GiB。マルチパート、自動再試行、転送の再開は未実装。結果不明のPUTはfailed_or_indeterminateを残し、自動で再送しない。キーの固定版を管理された読取りで調査してから次の操作を決める。実験先のIAMには設定閲覧・PutObjectと、取得主体側のGetObjectVersionが必要。初回Versioning有効化後の15分待機は運用手順で管理する。

## 取得結果をRAMへ結び付ける

tools/bind-m1-observations.pyは次を入力する。

- base：既存RAM。環境情報と必須資産の構造を参照する。
- capture：ローカル収集のE1記録。
- observations：取得観測のJSON配列。各記録に対応するasset_roleを明示する。
- set-id：新しいセットID。同じIDでの差替えを拒否する。
- output：まだ存在しない出力ディレクトリ。

    python3 tools/bind-m1-observations.py \
      --base examples/m1/RS-M1-P2-001/ram.json \
      --capture evidence/m1/e1/CAP-M1-20261017T213910-d65b1396.json \
      --observations .local/observations.json \
      --set-id RS-M1-P3-001 \
      --output .local/bound-RS-M1-P3-001

役割・サイト・保存先・サイズ・SHA-256・非null版を照合し、新RAMとbinding-report.jsonを生成する。アップロードの受領だけでは採用しない。旧RAMの資産参照は一度pendingへ戻し、新観測がない資産を前セットから暗黙に流用しない。runtime_wordpressはRAM上のruntimeへ対応させる。

生成したRAMは既存のrecovery-metadata.py freezeでRecovery Setへ固定できる。RAMを全件確定する処理とは異なり、未収集のrecovery_manifestなどはpendingのまま残す。現在のcaptureは独自E1記録であり、既存製品のodbfs3-recovery-set manifestとは別物。既存manifestとの正式な接続、全実行環境イメージ、Bootstrap配布は残作業。

観測JSONは署名されていない。入力を捏造すればハッシュ欄も捏造できるため、この変換処理を真正性検証やE2認定として扱わない。役割分離を別の監査で確認するまで、binding-reportはrole_separation=unverified。

## オフライン試験

    python3 -m unittest discover -s tests -v
    php tests/test-versioned-transfer.php
    php tests/test-temporary-role-auth.php

Pythonは41項目合格（既存33項目とRAM連携8項目）。
PHP転送は14項目合格。認証条件の試験は8項目。

転送試験は注入した模擬応答を使用し、実SDKによるHTTP通信・S3互換性・実IAMポリシーを証明しない。改変、短い/長い応答、別VersionId、版欠落、Versioning停止、保存競合、範囲外キー、取得先上書き、権限拒否を検査する。環境整備後に同じコードで実S3試験を行う。