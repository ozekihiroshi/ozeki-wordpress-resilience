# 読取り専用の導入前検査

`tools/deployment-preflight.py` はLinux/WSL用の外部CLIです。WordPressプラグインの管理画面ではありません。構成と担当者の棚卸し情報を照合し、ローカル作業領域のメタデータを検査します。取得・停止・S3送信・署名・復元・設定変更は行いません。レポートは標準出力だけに出します。

## 今できることとできないこと

|対象|確認方法|限界|
|---|---|---|
|サイト・DB・ファイル・全書込み元・キュー・依存|既存取得仕様の検査と、別の棚卸しJSONとの照合|棚卸しは担当者の申告。実ホストを自動調査した情報ではない|
|構成版・取得時刻|設定ハッシュ・サイトIDが一致し、棚卸し時刻が24時間以内、未来5秒以内|申告の署名検証や真正性確認ではない|
|保管先・署名担当|未設定の参照、writer/readerの同一参照を拒否|AWSへの接続や実IAM権限・保持設定・署名ホストの分離は未検証|
|既存処理|棚卸しに未完了／結果不明送信がある場合は拒否|元台帳への接続はしない。件数は担当者が確認する|
|作業領域|実在するディレクトリを読取りで開き、所有者・0700・読取り専用FS・空き容量を検査|書込みテストなし。ACL、クォータ、将来の容量や実書込み成功を保証しない|

必要容量は取得アダプターと同じ `2 × max_bytes + reserve_bytes`。入力は64KiB以下の通常ファイルのみ、シンボリックリンク・FIFO・重複JSONキー等を拒否します。生の入力値、ホスト名、資格情報、ファイルパスはレポートへ転記しません。入力に秘密情報は含めず、参照名だけを使用してください。

## 実行手順

1. [対象構成](../spec/13-first-site-capture-profile.md)に沿ったprofile JSONを用意します。`examples/first-site/generated-lab.json` は未設定項目があり、そのままでは導入前検査を通りません。
2. 別途棚卸しを行い、inventory JSONを作ります。profileからコピーするだけで実環境を確認した扱いにはしません。
3. 作業領域は運用担当者が別途用意します。この検査は作成・chmod・削除をしません。
4. 次を実行し、標準出力JSONの `state` と `issues` を確認します。

```sh
python3 tools/deployment-preflight.py \
  --profile /private/profile.json \
  --inventory /private/inventory.json \
  --workspace /private/capture-work
```

inventoryの必須項目：`format: owr-deployment-inventory-v1`、`config_sha256`、タイムゾーン付き`observed_at`、`site_id`、`wordpress`、`database`、`files`、`writers`、`queue`、`dependencies`、`runtime`、整数の`incomplete_runs`と`uncertain_puts`。構成項目はprofileと同じ形式です。`config_sha256`は既存 `first-site-capture.py` の `digest(profile)` と共通です。棚卸し側の追加書込み元・追加依存・異なるDBエンジンも不一致として停止します。

|state|終了コード|次の操作|
|---|---|---|
|eligible_for_dedicated_trial|0|限定構成の専用環境試験へ進める。本番導入の許可ではない|
|needs_configuration|2|issuesの理由と対処を確認。環境・設定・未完了処理を区別して解決する|
|unsupported|2|マルチサイト、非対応DBエンジン、外部キューなど現仕様の対象外。設定を偽って通さない|

`production_ready`と`capture_started`は常にfalseです。状態報告は復旧セットの署名承認にもなりません。検査後に設定や環境が変わったら再検査してください。取得開始時の既存検査も省略できません。

## 検証と分類

専用一時領域の21テストで、未設定・対象外・不一致・古い時刻・権限・容量・入力上限・読取り専用性を確認しました。容量不足／読取り専用FSは模擬条件です。通常CLIは別の生成データ領域で実行し、入力と既存ファイルのハッシュ保持を確認しました。[結果](../../evidence-public/deployment-preflight.json)。

この試験は実WordPress・SSH・S3の接続検査ではありません。72時間観測の台帳・署名鍵・既存資産には触れません。新たな環境障害・製品不具合は今回の試験では検出されませんでした。

ホスト上の実測アダプターと `--host-report` 接続を[追加しました](host-inventory.md)。実測対象はDB・ファイル・実行PHPの一部です。SSH転送の配備や書込み元全体の確認は引き続き未達です。環境問題はworkspace系の指摘、設定問題はconfiguration、未完了処理はoperational、製品対応範囲外はunsupportedで区別します。
