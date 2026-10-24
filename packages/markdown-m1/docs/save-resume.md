# Resume unconfirmed save history

English | 日本語 below

Use **Tools → Resilience → Save protection status** on the surviving source WordPress. This is a save-side operation, not destination recovery or replication.

1. Read the latest confirmed S3 sequence/time/asset, local pending count and recorded failure reason. A failed history read means **unknown**, not an empty history. An old error without pending work is not a reason to recreate an operation.
2. Resolve the reported storage/access problem using the existing configuration. Do not delete the pending queue or issue a replacement edit to bypass the failure. Keep the affected article unchanged while resolving it: article resume checks that its applied state still matches the pending operation.
3. Choose **Resume history** once. It uses the existing article record and shared adapter queue. If the response is uncertain, inspect the confirmed history and pending state before another action; do not assume either success or failure from a timeout alone.
4. Check that the expected operations appear in confirmed S3 history, pending work is cleared and the save-status display has recovered. One user operation may produce multiple records: article body and article details are separate. A higher sequence alone does not identify which operation succeeded.
5. If resume fails or the article no longer matches, retain the pending data and record the reason for investigation. Do not certify mismatched data as successful. A later complete-site recovery uses the selected baseline and confirmed history only.

WordPress application or S3 original storage alone does not make an operation recoverable. If the source is lost before formal-history confirmation, omit an unconfirmed new article or keep the previous confirmed version of an update. A clear local queue does not guarantee coverage of unsupported operations. This display is not a durable audit log.

## Measured boundary

The [2026-10-25 acceptance](../../../docs/releases/save-resume-acceptance.md) interrupted only the formal-history PUT, after original storage, inside one test request. Browser resume confirmed the same pending operations: history 56 → 58, pending 2 → 0, and errors cleared. This was **not an actual AWS outage**. Original PUT failure, lost responses, all adapter types, concurrent edits and destination recovery were not retested in this acceptance. No fault-injection helper is part of the product.

## 日本語：未確定履歴の再開

元サーバが残っている場合に、保存側WordPressの **ツール → Resilience → Save protection status** を使用します。復旧先への復旧実行やレプリケーションとは別の操作です。

1. 最後に確定したS3履歴の順序・時刻・対象、ローカル未確定件数、記録された失敗理由を確認します。履歴読取り失敗は「履歴なし」ではなく「未確認」です。未確定がなく古いエラーだけが残る場合、操作を作り直さないでください。
2. 表示された保存先・アクセス等の問題を既存設定で解消します。保留キューを削除したり、失敗を回避するための別編集を作成したりしないでください。本文の再開は反映済み状態との一致を検査するため、解消中は対象記事を変更しません。
3. **Resume history**を一度操作します。既存の本文履歴と共通連携キューを使います。応答が不明なら、追加操作の前に正式履歴と未確定状態を確認します。タイムアウトだけで成功・失敗を断定しません。
4. 対象操作がS3正式履歴に入り、未確定が解消し、保存状態表示が回復したことを確認します。一つの利用者操作から本文と付随情報など複数の履歴が生じる場合があります。履歴番号の増加だけで対象操作の成功を判断しません。
5. 再開失敗や本文不一致が残る場合は、保留データと理由を保持して調査します。不一致のまま成功扱いにはしません。その後のサイト全体復旧は、選択した基準と確定履歴だけを使用します。

WordPress反映やS3原本保存だけでは復旧対象に確定しません。正式履歴確定前に元サーバを失った場合、未確定の新規記事は存在しないものとして扱い、未確定の更新は前の確定版まで復旧します。未確定0件でも未対応操作の保護は保証しません。この表示は永続的な監査ログではありません。

今回の検証は原本保存後、試験要求内で正式履歴PUTだけを遮断したものです。**実AWS障害ではありません。** ブラウザで同じ操作を再開し、履歴56→58、未確定2→0、エラー表示解消を確認しました。原本PUT失敗、応答喪失、全連携、同時編集、復旧先の再実行は今回再検証していません。遮断処理は製品の依存関係ではありません。
