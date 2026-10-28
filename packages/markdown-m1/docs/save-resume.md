# Resume unconfirmed save history

English | 日本語 below

## Standard editor diagnostics (editor-save-final candidate)

The current source uses a structured `owr_save_failed` error so the block editor shows the save failure reason, rather than only “Updating failed.” A standard Save can submit both a REST article request and a legacy meta-box request. The latter skips an article original only when its complete body and recorded attributes match confirmed S3 history. Native details also omit identical confirmed state (including referenced media bytes); changed state is still recorded. An unavailable equality lookup never discards a completed native operation: it remains queued for confirmation. This is not general cross-request idempotency or multi-writer support.

Editor preferences are separate user-profile operations. WordPress persists them through `/wp/v2/users/me`; Flamingo hooks `profile_update` and refreshes contact dates. Do not interpret those contact-date changes as a Resilience article-save mutation. Do not disable member approval or third-party hooks to hide them. The measured article-only follow-up did not modify existing contacts. Historical request-level attribution remains unavailable for the earlier preference change.

日本語：現行ソースでは標準エディターへ具体的な失敗理由を返します。標準保存はREST本文要求と追加設定欄の別要求を送る場合があり、後者の本文がS3確定版と一致するときだけ重複保存を省きます。付随情報も画像の内容を含む確定状態が同じなら省き、変更や未確認の操作は捨てません。読取り失敗時は保留データを保持します。汎用の重複排除や複数書込み元の保証ではありません。

エディター設定の保存はユーザープロフィール更新経路を通り、Flamingoの標準フックが連絡先日時を更新します。これは本文保存とは区別します。会員承認や連携フックを無効化して隠しません。今回の本文だけの追試では既存連絡先は変化していません。前回の設定変更要求そのもののログは残っておらず、個別の因果関係は断定していません。この修正はeditor-save-final候補に収録しています。

Use **Tools → Resilience → Save protection status** on the surviving source WordPress. This is a save-side operation, not destination recovery or replication.

1. Read the latest confirmed S3 sequence/time/asset, local pending count and recorded failure reason. A failed history read means **unknown**, not an empty history. An old error without pending work is not a reason to recreate an operation.
2. Resolve the reported storage/access problem using the existing configuration. Do not delete the pending queue or issue a replacement edit to bypass the failure. Keep the affected article unchanged while resolving it: article resume checks that its applied state still matches the pending operation.
3. Choose **Resume history** once. It uses the existing article record and shared adapter queue. If the response is uncertain, inspect the confirmed history and pending state before another action; do not assume either success or failure from a timeout alone.
4. Check that the expected operations appear in confirmed S3 history, pending work is cleared and the save-status display has recovered. One user operation may produce multiple records: article body and article details are separate. A higher sequence alone does not identify which operation succeeded.
5. If resume fails or the article no longer matches, retain the pending data and record the reason for investigation. Do not certify mismatched data as successful. A later complete-site recovery uses the selected baseline and confirmed history only.

WordPress application or S3 original storage alone does not make an operation recoverable. If the source is lost before formal-history confirmation, omit an unconfirmed new article or keep the previous confirmed version of an update. A clear local queue does not guarantee coverage of unsupported operations. This display is not a durable audit log.

## Measured boundary

The [2026-10-25 acceptance](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/save-resume-acceptance.md) interrupted only the formal-history PUT, after original storage, inside one test request. Browser resume confirmed the same pending operations: history 56 → 58, pending 2 → 0, and errors cleared. This was **not an actual AWS outage**. Original PUT failure, lost responses, all adapter types, concurrent edits and destination recovery were not retested in this acceptance. No fault-injection helper is part of the product.

## 日本語：未確定履歴の再開

元サーバが残っている場合に、保存側WordPressの **ツール → Resilience → Save protection status** を使用します。復旧先への復旧実行やレプリケーションとは別の操作です。

1. 最後に確定したS3履歴の順序・時刻・対象、ローカル未確定件数、記録された失敗理由を確認します。履歴読取り失敗は「履歴なし」ではなく「未確認」です。未確定がなく古いエラーだけが残る場合、操作を作り直さないでください。
2. 表示された保存先・アクセス等の問題を既存設定で解消します。保留キューを削除したり、失敗を回避するための別編集を作成したりしないでください。本文の再開は反映済み状態との一致を検査するため、解消中は対象記事を変更しません。
3. **Resume history**を一度操作します。既存の本文履歴と共通連携キューを使います。応答が不明なら、追加操作の前に正式履歴と未確定状態を確認します。タイムアウトだけで成功・失敗を断定しません。
4. 対象操作がS3正式履歴に入り、未確定が解消し、保存状態表示が回復したことを確認します。一つの利用者操作から本文と付随情報など複数の履歴が生じる場合があります。履歴番号の増加だけで対象操作の成功を判断しません。
5. 再開失敗や本文不一致が残る場合は、保留データと理由を保持して調査します。不一致のまま成功扱いにはしません。その後のサイト全体復旧は、選択した基準と確定履歴だけを使用します。

WordPress反映やS3原本保存だけでは復旧対象に確定しません。正式履歴確定前に元サーバを失った場合、未確定の新規記事は存在しないものとして扱い、未確定の更新は前の確定版まで復旧します。未確定0件でも未対応操作の保護は保証しません。この表示は永続的な監査ログではありません。

今回の検証は原本保存後、試験要求内で正式履歴PUTだけを遮断したものです。**実AWS障害ではありません。** ブラウザで同じ操作を再開し、履歴56→58、未確定2→0、エラー表示解消を確認しました。原本PUT失敗、応答喪失、全連携、同時編集、復旧先の再実行は今回再検証していません。遮断処理は製品の依存関係ではありません。

## Capture failures before queue registration (save-verification-final candidate)

See [save confirmation and capture failures](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/save-confirmation.md). A capture diagnostic is not a resumable operation. Inspect existing history and queued payloads before choosing Resume history or re-saving the affected data. 本文と付随情報の確定を区別し、キュー登録前の診断を未確定データそのものと扱わないでください。
