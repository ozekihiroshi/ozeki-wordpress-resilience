# Save confirmation and capture failures

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

Included in save-verification-final candidate after PR #42; absent from the older application-rules-final ZIP. No publication.

- **Formal history confirmed** means that the S3 history record was read. The status display does not re-fetch every referenced original. Saving uses checksums/fixed versions; retrieval checks hashes through the existing reader. These are distinct checks.
- Article body and article-detail pending counts are separate. Images, categories/tags and deletion state can have a separate operation from the body. A body confirmation is not confirmation of the whole editing session.
- The shared queue also contains comment/form/member/table operations. Existing queue payloads remain the only input for Resume history.
- A capture or queue-registration exception is recorded separately with time, operation context and reason. It is diagnostic information, not a payload, not formal history and not a retry request. The original exception is rethrown; there is no automatic continuation or new rollback.
- The latest recorded capture error remains visible after unrelated success. It does not prove that an operation is still pending. Zero queued records does not resolve it: investigate the affected operation and confirmed history. If there is no queued payload, correct the cause and save the affected information again. The notice cannot reconstruct information that was never captured.
- If diagnostic persistence fails, a generic server-log message is attempted and the original exception is preserved. Database outage or forced process termination can prevent durable notification. This is not an independent audit ledger or a new guarantee of uncaptured operations.

## Verification

Local contracts cover prequeue size rejection, original exception preservation, diagnostic write failure, unrelated-success retention, escaped display and separate body/detail counts. Existing comment/form/member/table/native-detail/native-queue contracts passed; PHP syntax and diff checks passed.

Existing dm isolated fresh-install namespace `owrruleszip_20261025_fresh_` was reused. A prequeue oversized payload and a nonexistent form lookup caused controlled failures before S3 access. Actual WordPress options retained diagnostics; the administration renderer showed reasons and confirmation boundaries. Before/after configuration, queues, results, posts/comments/users and the shared-site probe matched. AWS calls and mail attempts were zero; scheduling remained disabled.

This is not browser acceptance, real AWS failure, all-adapter failure-injection, forced termination, new package acceptance or a repeated restore trial. The existing duplicate DISABLE_WP_CRON warning is a probe bootstrap issue. No new product fault was found during this test.

## 日本語

作業種類は表示・失敗通知の修正と差分検証、状態は検証済み・制限ありです。完了条件は正式履歴と原本再取得の区別、本文・付随情報の未確定状態、キュー登録前の失敗理由を管理者が見分けられることです。

正式履歴の確定表示は、参照原本を現在すべて再取得したという表示ではありません。本文と付随情報は別の確定単位になり得ます。取得・キュー登録時の失敗は日時・処理区分・理由を最後の診断として保持し、本文そのものや再開用データは保存しません。別操作の成功で診断を消さず、キューが空でも解決済みとは扱いません。一方、過去の診断だけで現在未確定だとも断定しません。

既存キューがあれば通常の再開手順を使います。キューがない場合は原因と対象操作を確認し、修正後に対象データを再保存します。自動再開・新しい巻戻しは追加していません。DBに診断を書けない場合や強制停止では記録が残らない可能性があります。

既存dm隔離環境でキュー前のサイズ超過・フォーム取得失敗と実管理画面の表示処理を確認しました。S3呼出し0、メール0、既存コンテンツ・設定・未確定キュー・復旧結果は不変です。ブラウザ、実AWS障害、全連携の異常系、ZIP更新は今回未検証です。修正は旧検証済みZIPに含まれません。正式公開は行っていません。
