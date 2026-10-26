# Save failure → resume → confirmed history acceptance

Date: 2026-10-25. Documentation-only follow-up to merged PR #31. No product correction or new ZIP was needed.

## Observed sequence

The existing isolated source WordPress and existing S3 trial prefix were reused. A new trial article (#37) was created through the normal WordPress `wp_insert_post` API and product hooks from CLI. The article was not created by clicking through the browser editor. Existing content was not edited.

| Stage | Confirmed S3 history | Local pending records | Administrative feedback |
|---|---:|---:|---|
| Before | 56 | 0 | No pending operation |
| Formal-history PUT rejected | 56 | 2 | Article history and article details pending; reason and Resume history instruction visible |
| Resume history clicked once in browser | 58 | 0 | Latest sequence 58; pending notices/errors cleared |

The body operation `b335570c-587a-4466-ba31-d7d026fdd3d1` became sequence 57; native article-details operation `67eb7750-9b26-49a1-a85b-7e4dd5977c85` became sequence 58. These were the identities displayed while pending, not replacement operations. The final S3 history read contained exactly these two new records.

## Failure model and limits

A request-local AWS SDK HTTP-handler wrapper rejected only PUT requests to the formal-history path before transmission, with `TEST ONLY: formal-history PUT interrupted before transmission`. Other requests, including original storage, used the normal handler and existing standard authentication. The filter disappeared at the end of the CLI request; browser resume used the normal product route. No persistent fault-injection component, IAM change or new infrastructure was added.

This was **controlled test transmission interruption, not an actual AWS outage**. It establishes the original-saved / history-pending recovery path, not original-storage failure, timeout/lost-response handling, every adapter, concurrency or arbitrary AWS incident behavior. Destination reconstruction was not repeated; this acceptance ends at confirmed history and recovered save-status display.

## Preservation and issue classification

- Every pre-existing source post and postmeta row matched its before value. The aggregate posts hash changed because of the new trial article only.
- Administrator, other members and their metadata, approval policy and settings matched before/after probes. Mail blocking and Cron disabling were maintained; CLI test mail-call count was zero. No mail, periodic run or formal release was performed.
- **Product:** the existing route succeeded; no product fix required.
- **Test infrastructure:** the deliberate request-local rejection is the failure trigger, not a production dependency or a real S3 incident.
- **Environment:** no environmental fault blocked this sequence. This does not resolve previously documented browser or resource limits.

The validated package remains `release-candidates/20261025-save-status/ozeki-wordpress-resilience-0.3.1-save-status-final.zip`, SHA-256 `43429964fe9ad68b5cc0979ebf3f9d95e760ff03b6c12b20fff1090975ff630b`. This follow-up updates repository documentation only; the frozen ZIP and its embedded documentation remain unchanged.

Local evidence: `release-readiness/save-resume-20261025/` contains before/start/pending/confirmed/after JSON, the guarded trial script and pending/recovered screenshots. Private probes and test harnesses are not shipped. See the [operator procedure](../../packages/markdown-m1/docs/save-resume.md).

## 日本語要約

原本を実S3へ保存した後、試験要求内だけで正式履歴送信を遮断し、未確定2件と失敗理由の表示を確認しました。管理画面のResume historyを一度操作し、同じ操作IDが履歴57・58に確定、未確定0件、失敗表示解消となりました。既存会員・記事・設定は保持されています。

実AWS障害の再現ではなく、原本保存後の履歴送信失敗に限定した検証です。製品修正は不要でした。今回の文書追加で検証済みZIPを書き換えたり、復旧先・定期実行を再試験したりはしていません。
