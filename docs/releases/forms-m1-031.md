# 0.3.1 Contact Form 7 / Flamingo — review candidate

Completed CF7 definition saves and newly received Flamingo inquiries now become
complete JSON originals and confirmed S3 history, replayed through complete-site
recovery. This extends the WordPress + S3 product, not the research worker path.
It is a PR candidate, not a formal release.

## Contract and scope

CF7 creation/update and its Flamingo receipt integration freeze the completed
plugin-save result. This is post-success capture, not article-style S3-first
admission or raw-input interception. WordPress persistence, S3 original storage
and formal confirmation jointly establish recoverability. A failed S3 operation
retains the same payload for Resume history. Source loss before confirmation
omits that operation. Recovery does not call submission/email APIs.

Form post fields, metadata, mail templates and inbound-channel relationships are
replayed without using the source DB. Individual text recovery rejects form
records. CF7 6.2.3 and Flamingo 2.6.4 were tested on PHP 8.3.36; the tested CF7
requires PHP 8.3+. Both optional plugins are installed separately, not bundled
in the product ZIP. Exact recorded versions are required at the destination.
Keep form runtimes consistent with the baseline and subsequent history; plugin
version transitions across a baseline are not an accepted migration scenario.
A new trusted baseline includes active form runtimes, but this new capture path
was not separately repeated in the live acceptance reported here.

Not covered: attachments' binary contents, address-book entries, later inquiry
editing/moderation/deletion, form deletion history, arbitrary third-party fields,
SMTP/OAuth secrets and notification replay. Do-not-store exclusions remain in
effect. Stored settings and inquiries can contain personal data. Existing 5 MiB
operation limits and one writer per S3 prefix apply. The paired form plugins must
be available when protection is enabled. Concurrent same-asset writes and abrupt
whole-site process-kill rollback remain unaccepted.

## Artifact

[Final 0.3.1 ZIP](../../release-candidates/20261024-forms/ozeki-wordpress-resilience-0.3.1-forms-final.zip)

SHA-256: `34cdefd6ff3ea4880bc1643342655caef6d2157bbb8e6a7f9f600aa94f7e0068`

7,353,171 bytes / 3,805 files. Product source equality checked; AWS SDK/vendor
unchanged. No test helpers, credentials or private test data are included.
The English/Japanese package READMEs and forms contract are inside this ZIP.

## Validation

- Actual trial form create/update and standard CF7 HTTP submission used the existing
  AWS environment. `skip_mail: on` prevented delivery; a `mail_sent` response is
  not claimed as evidence of actual delivery.
- Transport failure injection kept history at 40; frozen retry confirmed 41 and
  repeat retry did not duplicate. This is not a real AWS outage test.
- Existing S3 baseline plus history through 41 reconstructed form/receipt fields
  and channel relationships on the recovery WordPress. Restore mail calls: 0.
  Prior content/configuration comparisons passed after the author fix below.
- ZIP-extracted PHP lint, forms/comments/Checkpoint/cleanup contracts pass. The
  latter failure cases use an in-memory transport and are distinguished from AWS.
- Final ZIP fresh installation and update from the PR #21 comments-reviewed ZIP
  passed in separate folders/tables in the existing dm container. Settings,
  content, stable identities, comments, forms, receipts, metadata, channels,
  pending queues/errors, dependency activation and restore results were preserved.
- Standard EC2-role reads found 41 identical formal-history entries before/after;
  these packaging tests made zero S3 writes/deletes. Actual admin-page rendering
  passed. The running recovery site's before/after probe was byte-identical.
- Sanitized aggregate evidence: [validation.json](../../release-candidates/20261024-forms/validation.json).
  Frozen-queue installation fixtures are not replayable production operations.

## Distinguish corrections

**Product:** unmapped post authors previously fell back to the recovery operator,
which could change attribution according to the invocation identity. They now
use ID 0, consistent with unmapped comment users; restored original attributes
match the preserved baseline. Forms reuse the existing durable comment queue.

**Environment:** dm's 192 MiB/no-swap container hit OOM conditions during earlier
restore attempts (cgroup oom_kill=3). The same container was adjusted to 320 MiB,
640 MiB memory+swap; subsequent restores completed and the counter stayed at 3.
This is a measured lab configuration, not a universal product minimum or a plugin
resource-setting feature. Carry those settings separately on container recreation.
Do not attribute older unexplained exits from other tests to this diagnosis.

**Test infrastructure:** activate-then-submit in one PHP request lacked normal CF7
module initialization; tests use the next normal request. A memory fixture lacked
its history schema and was corrected. Cron preservation distinguishes Flamingo's
own maintenance registration and four normal WordPress first-boot events while
preserving all pre-existing events. An existing probe's duplicate DISABLE_WP_CRON
warning is separate from product behavior. These are not product fixes.

This PR does not modify live content, IAM or server configuration. Periodic
Checkpoint acceptance, cleanup execution and formal publication remain deferred.

## 日本語要約

フォーム作成・更新と新規受信の完全JSON保存、同一データ再開、正式履歴からのサイト
全体復旧を追加します。本文のS3先行保存とは異なり、フォーム保存完了時点の結果を
固定します。復旧はメールを再送しません。添付本体、アドレス帳、受信後の編集・削除、
フォーム削除は対象外です。記録した版の両プラグインを別途用意してください。

検証済みZIPの新規導入・旧ZIPからの更新では、設定・フォーム・受信記録・コメント・
未確定キュー・復旧結果を保持し、S3正式履歴41件も不変です。dmのメモリ不足、試験側の
初期化・比較条件修正、製品の投稿者割当修正を区別しています。既存コンテンツを変更
せず、定期実行と正式公開は後回しにします。
