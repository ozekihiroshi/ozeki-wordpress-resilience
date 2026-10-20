# 日次保存・署名承認・隔離復元の状態確認

二資産の日次JSONに復元観測を集約します。保存時の `receipt.json` と `approval.json` を上書きせず、専用SQLiteの `restore_observations` へ観測を追記します。三資産の72時間観測とは別の機能です。

|確認対象|JSONの項目|意味|
|---|---|---|
|保存完了|`storage_complete=true`|固定版保存と読戻しの証拠あり|
|署名承認待ち|`approval_state=pending` / `phase=awaiting_approval`|保存済みだが未承認|
|承認済み|`approval_state=approved` / `phase=approved`|独立署名承認済み、復元成功観測は未登録|
|復元検証済み|`restore_state=verified` / `phase=restore_verified`|この承認文書に対応する隔離復元成功を登録済み|
|復元失敗|`restore_state=failed` / `phase=restore_failed`|承認は有効だが最新の復元観測は失敗|
|承認期限切れ|`approval_state=expired` / `phase=approval_expired`|過去に復元成功していても現在有効な承認ではない|
|証拠不整合|`phase=evidence_error`|記録の欠損・変更・組合せ不一致を検出|

`state` は既存の日次処理用状態としてapproved等を維持します。総合表示には `phase` を使います。`restore_verified` は過去の試験観測であり、期限切れ後にtrueでも復旧許可を意味しません。`restore_allowed` は引き続きfalseで、実際の復旧は独立信頼情報・署名・固定版の再検証が必須です。

## 復元結果を登録する

担当者が独立した復元試行の `result.json` を確認し、そのSHA-256を指定します。個別の結果は明示登録できます。[自動登録ワーカー](first-site-auto-recovery.md)を使う場合は、復元処理と結果登録が接続されます。

```bash
python3 tools/first-site-daily.py --state "/二資産の日次台帳" record-restore \
  --day "2026-10-20" \
  --directory "/隔離復元の試行ディレクトリ" \
  --report-sha256 "確認したresult.jsonのSHA256"

python3 tools/first-site-daily.py --state "/二資産の日次台帳" status
```

登録時には、その日次枠が承認済みであること、署名文書・公開鍵・設定・セットの一致、署名と期限を確認します。成功の登録ではさらにS3のVersion ID付き読取り受領、取得物のハッシュ、取得時の組合せ、ファイル一覧、画像ハッシュ、WordPress表示と隔離・後片付けの結果を照合します。S3への再アクセスや再復元はしません。

同一レポートの再登録は何も増やしません。別セット、不正なハッシュ、固定版不一致、後片付け未完了、承認待ちの枠への登録は拒否します。署名期限切れ後の新規登録も拒否し、既に登録した履歴は保持します。

成功・失敗の観測を追記し、完了時刻順で最新を表示します。失敗報告に完了時刻がない場合は登録時刻を使います。以前の成功は消さず、`previous_restore_verified` に残します。古い成功報告を後で登録しても新しい失敗を隠しません。statusはSQLiteを読取り専用で開き、状態更新・再照合・通信をしません。

## 試験と限界

既存二資産台帳を新しい専用フォルダへ複製し、実際に隔離復元した生成セットの証拠で集約を検証しました。元の台帳・承認記録・転送受領はハッシュ一致で保存確認済みです。追加S3呼出し、追加保存、既存72時間観測への変更はありません。

これは担当者が確認したローカル試験観測の集約です。実行結果そのものの独立署名や遠隔実行証明ではなく、改ざんされたホストや台帳全体を信頼可能にする機能ではありません。[ローカル自動登録ワーカー](first-site-auto-recovery.md)は実装済みです。管理画面表示、別ホストからの観測転送は未実装です。

[日次保存と承認](first-site-daily.md) / [隔離復元](first-site-daily-restore.md)
