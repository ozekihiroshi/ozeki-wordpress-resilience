# 導入前検査から初回取得への条件（試作仕様）

対象は単一 WordPress・InnoDB・ローカルファイル・外部依存なしの専用試験です。本番導入の許可ではありません。

`tools/first-capture-readiness.py` は既存の導入前検査を再評価し、SSH棚卸し報告、転送状態、担当者確認記録を読むだけです。取得・署名・復元・設定変更・通信は行いません。

## 判定

|状態|扱い|担当者の次の操作|
|---|---|---|
|取得失敗・転送失敗|blocked。過去の成功で代替しない|原因と接続先を確認し、再取得・再転送する|
|報告・検査・転送・確認記録が5分以上前|blocked。ちょうど300秒でも拒否|最新情報を取り直して確認する|
|時刻が5秒を超えて未来／タイムゾーンなし|blocked|時刻同期・形式を修正する|
|報告と転送状態が別世代|blocked|一致した組が受信されるまで待ち、再検査する|
|未確認項目あり|blocked|下表の根拠を確認記録へ記載する。推測で確認済みにしない|
|非対応構成・容量不足・未終了処理・結果不明PUT|blocked。担当者確認で解除不可|構成や処理状況を是正し再検査する|
|すべて満たす|eligible_for_dedicated_capture_review|専用試験の取得手順へ進むか判断する|

全結果で `production_ready=false`, `capture_started=false`, `execution_authorized=false`。終了コード0は確認条件の成立だけを表し、2は保留です。保存した判定JSONを後日の実行許可として使ってはいけません。

## 担当者が確認する事項

|確認キー|必要な確認・根拠|
|---|---|
|writers|管理画面・REST・cron・CLI・SSH・直接DB・外部処理を含む更新経路と、停止担当・停止方法|
|queue|キューが存在しない根拠。存在する場合は初期対象外として構成を見直す|
|dependencies|外部DB・オブジェクトストレージ・共有ファイル等の見落としがないこと|
|runtime_image_binding|復元に使う実行環境と設定の対応、固定参照の根拠|
|multisite_config|単一サイト構成と対象ルート・DBの対応|
|storage|保存先、35日保持、固定Version取得、保存権限と復旧権限の分離を確認した試験記録|
|trust|独立した署名担当・公開鍵の照合元・別媒体コピーと復旧方法|
|operational_ledgers|未終了処理・結果不明保存・未配送記録を調査し、消さずに解決した記録|
|file_snapshot_consistency|DBとファイルの取得範囲、停止中の更新防止、除外による欠落がない根拠|
|stop_and_release_plan|停止時間上限、処理完了待ち、失敗時の解除担当・解除確認方法|

すべて `confirmed: true` と根拠の参照 `evidence_ref` が必要です。実データ・秘密・パスワードを根拠欄へ書かず、管理された記録のIDを記載してください。確認者は設定済みownerまたはalternateです。

## 入力と運用

```sh
python3 -B tools/first-capture-readiness.py \
  --profile /private/profile.json --inventory /private/inventory.json \
  --workspace /private/capture-work \
  --report /private/preflight-report.json --health /private/preflight-health.json \
  --review /private/first-capture-review.json
```

確認記録の厳密なフィールドは `format`（owr-first-capture-review-v1）、`site_id`、`config_sha256`、`report_sha256`、`health_sha256`、`inventory_sha256`、`workspace`（絶対パス）、`reviewed_at`、`reviewed_by`、`scope`（dedicated_trial_only）、`confirmations` です。
SHA256は既存 `first-site-capture.digest` の正規化JSON方式で算出します。確認は報告・転送より後でなければなりません。設定・棚卸し・報告・転送状態・作業場所のいずれかが変わったら確認をやり直します。定期更新中に報告が変わった場合も安全側で拒否します。

この記録は署名ではなく、確認者の文字列は認証ではありません。入力は信頼する外部ホストの所有者限定領域で管理し、SSHホスト鍵と固定コマンドの既存制限を維持してください。WordPressや保存元から確認記録を書き換えられる配置にしないでください。ツールは根拠参照先の内容や人の判断を自動検証しません。

## 初回取得入口への接続

読取り専用ゲートを使う初回取得入口 `first-capture-entry.capture_from_files` を追加しました。設定・棚卸し・報告・転送状態・確認記録のファイルパス、workspace、既存backendを渡します。保存済みの判定JSONは受け付けません。

サイト単位の排他ロック取得後、未解決の前回処理がないことを確認して入力を読み直します。条件成立後に取得試行を作り、既存backendの実環境検査と空き容量検査を行い、更新停止直前にもう一度入力を読み直して時刻・設定ハッシュ・根拠の対応を再評価します。ロックは取得・解除・結果保存まで保持します。

最初の検査で拒否した場合はロックファイル以外の試行資産を作らず、backendを呼びません。直前検査で拒否した場合は `capture_started=false` の失敗結果を保存し、fence/streamを呼びません。取得後の停止解除が確認できない場合は既存のactive記録を保持し、次回の取得を拒否します。

この入口は生成データの専用環境で接続済みです。低水準のcapture APIは既存試験との互換性のため残しており、全既存の日次処理を変更したわけではありません。初回導入の呼出元は必ずこの入口を使用してください。OS権限を持つ攻撃者への認証境界ではありません。判定後の任意のファイル変更を原子的に防ぐ仕組みではなく、入力は外部の信頼する所有者限定領域に置く前提です。実取得中の更新防止・整合性・停止解除は既存アダプターが引き続き確認します。

保存完了、署名承認待ち、承認済み、復元検証済みは後段の別状態です。今回の判定はこれらを進めません。マルウェア不存在、本番復旧可能性、実際の停止成功は未保証です。

## 検証と課題区分

専用のネットワークなし・コード読取り専用Dockerで生成データによる14試験が成功。正常、300秒境界、失敗時のキャッシュ拒否、未来時刻、報告世代不一致、確認欠落、入力束縛、未終了保存、非対応構成、CLIの入力不変・取得先無変更を検証しました。実SSH・S3・署名・復元・通知はこの試験では行っていません。

環境：今回の試験で新規障害なし。72時間観測の既存欠測は別管理。
試験基盤：既存のブラウザ起動問題は原因未確定のまま。今回ブラウザ試験は対象外であり、解決を意味しません。
プラグイン／外部処理：ゲート実装済み。新しい初回取得入口への強制接続は実装済み。既存の日次実行への移行と本番適用は未達。共通部品とBackup for S3は変更していません。


## 初回取得入口の実行例（Python API）

```python
# tools/first-capture-entry.py を importlib で読み込んだ entry を使用する。
work, result = entry.capture_from_files(
    profile=profile_path, inventory=inventory_path,
    report=report_path, health=health_path, review=review_path,
    workspace=private_workspace, backend=dedicated_backend,
)
```

初期拒否は `entry.api.Rejected`、試行開始後の失敗は保存されたresultで報告します。`eligible_for_consistency_acceptance` と `release_confirmed` を必ず確認してください。`capture_started` は停止開始を試みたことを示し、取得完了を意味しません。

検証コマンド：`python3 -B tools/run-first-capture-entry-lab.py --execute-lab --output /new/private/path/result.json`。既存の専用WordPress/MariaDB起動・解除・廃棄処理を再利用します。棚卸しと担当者確認は生成した試験入力です。実SSHの棚卸し、実S3への送信、独立署名はこの試験の合格範囲に含みません。

初回取得接続の検証結果：入口単体7件、既存取得17件・判定14件が成功。実WordPress/MariaDBの4項目（初期拒否、実環境検査後の条件変更拒否、DB/ファイル取得・解除、解除後の利用可能性）成功。DB92,829バイト・ファイル29,718,629バイト、試験資源削除済み。初回試行は出力親フォルダー未作成により入口呼出前に停止した試験基盤の不具合で、原因を記録し修正後に再試験した。新たな環境障害や取得処理の不具合は今回確認していない。既存ブラウザ問題の原因未確定は維持する。
