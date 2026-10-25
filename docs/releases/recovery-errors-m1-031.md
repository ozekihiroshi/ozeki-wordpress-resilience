# Recovery failure detection — focused correction, 2026-10-25

## Work contract

Type: defect correction and existing-function verification. Initial state: recovery accepted with limits; unchecked database/result writes. Completion: normal and unchanged writes succeed; tested failures stop, do not return a new success, and expose a cause. Contribution: truthful recovery outcome, not automatic continuation, restart or site-wide rollback.

## Product changes

- Check START TRANSACTION and COMMIT return values; throw with the database error on failure.
- Verify persisted recovery options directly from the database after update_option, including site settings, active plugins, WP-Members settings, origin and recovery results. Unchanged values are accepted; read/write errors or mismatches fail. Verify the origin metadata update as well.
- Return the current successful result only after it is persisted, rather than rereading a potentially older result.
- Verify attempt-state writes. A caught complete-site recovery failure stops with an escaped HTTP 500 error response. Try to record the failure; if that also fails, show both errors in the current response and warn that stored results may be older. No redirect that could silently show an older success.
- Existing exception cleanup remains unchanged. No automatic retry/resume or new rollback mechanism.

## Focused environment and acceptance

Reused dm's existing WordPress/core and database containers. A new isolated table namespace `owrerr_20261025_` and `/tmp/owr-recovery-errors-20261025` held synthetic fixtures only. The test bootstrap uses product classes directly; shared site code and the validated ZIP were not updated. S3 is an in-memory test double: no real S3 requests, writes or deletes. WP-Cron disabled; email intercepted, checked zero calls during tested recovery/actions.

Passed on actual WordPress/DB:

- Changed and unchanged text, empty/false, zero and nested-array options.
- Injected START failure: exception with cause, no continued COMMIT, no new successful result.
- Injected COMMIT failure: exception with cause, no new successful result.
- Injected blogdescription update and final recovery-result write failure: stopped with named option/database cause, no new success returned; previous success record unchanged.
- Normal synthetic complete-site recovery: success returned and expected option persisted.
- Actual admin handler with invalid end: terminates in failure response and stores failed state.
- Attempt-state and failure-record writes both blocked: terminates with current failure response and explicit warning about older stored results. A test wp_die handler captured the response; this was not browser acceptance.
- Origin metadata changed/unchanged writes and injected write failure: failure detected with post/key context.
- Existing shared-site probe identical before/after the main suite. Metadata follow-up touched only a new fixture in the isolated namespace.

Failure injection replaces selected SQL with a deliberately invalid query through a test-only WordPress query filter. This verifies false/error handling, not real network loss or an indeterminate COMMIT. Existing point-time/result/membership tests pass; new offline recovery-errors contract covers unchanged values, option read/write failure and transaction failures and is added to PHP8.1/8.3 CI (not yet run remotely for this change).

## Corrections and limits

The first test found a defect in the new verification helper: wpdb::get_var returns null for an empty cell. Changed to get_row to distinguish an existing empty value from a missing row, and reran the affected suite successfully. Original failed log retained. This was a product correction discovered by the test, not an environment failure.

Existing duplicate DISABLE_WP_CRON warning comes from the shared probe configuration, unrelated to the product correction. It was not changed.

If the database cannot store the failure, this response supplies the cause but cannot guarantee a durable failure record or updated later admin-page state. A failure after COMMIT can mean content was applied but completion/result recording failed; failure does not prove zero changes or rollback. Process termination, OOM, database connection loss with unknown commit outcome, arbitrary plugin hooks and all possible WordPress API failures are not accepted by these focused tests. No automatic restart/rollback guarantee. Existing file error messages and external plugin internal behavior are not broadened by this change.

No existing member/content edits, email delivery, scheduled execution, S3 deletion, IAM changes, shared-site deployment, ZIP rebuild, PR or formal release.

## 日本語

作業種類は不具合修正＋既存機能の検証。DB開始・確定、設定・メタ情報、復旧結果・試行状態の保存失敗を検出し、失敗応答で停止する範囲を確認しました。結果記録も失敗した場合は、その場の応答に両方の原因と過去の記録が残る可能性を表示します。

既存dmの専用DB領域・合成データを使用。実WordPress/DBへの意図的なSQLエラー注入であり、実AWS障害・ブラウザ試験・強制停止試験ではありません。自動再開・巻戻し機能を追加していません。COMMIT後の結果保存失敗は内容反映済みの可能性があり、失敗表示は未変更・巻戻し完了を意味しません。

状態は「今回の失敗条件について検証済み・制限あり」。検証済みZIPと稼働サイトは未変更です。Evidence: release-readiness/recovery-errors-20261025/ (result.txt preserves initial failure; result-2.txt is corrected acceptance; metadata follow-up recorded separately).
