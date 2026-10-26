# Save confirmation and original verification — final candidate

Work: minimal correction, focused verification and packaging. State: complete with stated limits; no formal publication or GitHub release. Purpose: prevent confirmation before original read-back succeeds and expose capture/pending failures without adding a new recovery workflow.

## Candidate

[ozeki-wordpress-resilience-0.3.1-save-verification-final.zip](../../release-candidates/20261025-save-verification/ozeki-wordpress-resilience-0.3.1-save-verification-final.zip)

SHA-256: `6105125270e459fdaeb392337c159cb35f6c705abe73293ec2ef7220becbc308`. 7,432,000 bytes / 3,823 files. Version remains 0.3.1; identify by filename and hash. Older candidates and vendor dependencies unchanged.

## Completed behaviour

- Same-client, fixed-version read-back of operation source, metadata, split parts and referenced media before formal history PUT. Existing reconstruction/hash checks reused; duplicate media references verified once. No site-wide scan.
- Read/hash failure prevents history PUT, retains existing pending state, and uses the existing resume path. A later resume verifies frozen references again. No automatic resume or new rollback.
- Administration distinguishes formal-history reading from present-time resource retrieval, and body/detail/other pending operations.
- Capture/queue-registration errors have a separate historical diagnostic. It is not a resumable payload, and unrelated successful actions do not erase it. Database unavailability/process termination can prevent persistence; this limitation remains explicit.

## Evidence, without conflating test types

1. Fixture tests locally and in the existing dm PHP container injected corruption and read failures into source index, metadata, split data and media. History PUT count stayed zero; pending data and original objects remained intact. Clearing faults confirmed the same operation. Existing save/result/adapter contracts also passed.
2. Actual isolated WordPress shared-queue resume used existing real-S3 history 1 original references. Five real fixed-version reads exercised corruption, unavailable response and successful verification. Faults were injected after reading, and the successful history PUT was intercepted by a request-local test handler. Therefore actual S3 writes were zero: this proves queue integration with real reads, not a new real-S3 write or AWS outage test. Trial queue state was restored in finally; shared-site probes matched.
3. Fresh activation and application-rules-final → save-verification-final replacement used existing dm Docker/core/database with dedicated `owrsaveverify_20261025_fresh_` / `upgrade_` table namespaces. Configuration, existing read-only S3 history, two synthetic pending records, capture diagnostic, errors, individual/site results and fixture content were preserved. All 3,823 files matched. This is extraction/activation/replacement, not browser upload. Pending resume evidence is item 2, not these synthetic install fixtures.

Final documentation-only correction removed an obsolete “not yet packaged” heading from save-resume.md; tested code was identical. Both installations were rechecked against the corrected ZIP; remote/local SHA-256 matched.

## Issue classification and scope

The first real-queue trial used a false pre-option override, which WordPress interprets as no override. The existing synthetic article queue correctly blocked the attempt; finally restored state. The test override was corrected to an empty array, and fault-message assertions were tightened. This was a harness issue, not a product failure. Duplicate DISABLE_WP_CRON warnings belong to the existing probe bootstrap. The intentional diagnostic-write-failure contract emits a generic error-log line as designed.

No existing S3 objects, shared-site members/content, IAM or infrastructure were changed; no mail, scheduled operation, deletion or publication. Product changes are staged only in isolated test installations and the candidate, not deployed to shared sites. Initial snapshot/Checkpoint creation and old-history certification are unchanged. No large-media timing, every adapter's browser workflow, or production outage guarantee is claimed. The prior ~55 ms measurement applies only to a 613-byte/two-object operation, not general performance.

## 日本語

今回の問題への対応は完了です。原本・付随情報・分離データ・参照画像を、保存時のS3クライアントと固定版で再取得・照合し、成功した場合だけ正式履歴を確定します。失敗時は既存の未確定操作を保持し、原因を直して再開すると同じ操作を照合して確定します。表示とキュー登録前の失敗通知も候補へ収録しました。

代替S3異常系、実WordPress＋実S3読取り（履歴PUTは試験側で遮断）、最終ZIPの新規導入・更新の三つを区別して確認しました。実AWS障害や実S3への新しい履歴書込み、ブラウザ更新を今回検証したという意味ではありません。設定・履歴・未確定記録・診断・復旧結果は保持され、既存資産・コンテンツは不変です。

実装を増やさず、この候補を今回の完了点とします。初期スナップショットやCheckpoint作成、旧履歴の遡及認定は対象外です。DB停止や強制終了時の診断保持は保証しません。正式公開・GitHub Pre-release作成は行っていません。

## Final PR review note

The repository English/Japanese README ZIP links were corrected to the candidate directory. The frozen, tested ZIP is unchanged: its bundled READMEs still contain an incorrect download-directory link. Use the candidate link and SHA-256 in this record instead. This is a documentation navigation defect, not a save/recovery or test-environment defect. No PHP changes or additional live tests were made during final review.

最終レビューでリポジトリの英日READMEのZIPリンクを修正しました。検証済みZIPは変更していないため、同梱READMEのダウンロード先にはディレクトリの誤りが残ります。本記録のリンクとSHA-256を使用してください。保存・復旧処理や試験環境の問題ではなく、文書リンクの不備です。
