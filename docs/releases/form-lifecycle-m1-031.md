# 0.3.1 Flamingo lifecycle and CF7 deletion — review candidate

This extends PR #22 with received-message editing, spam/ham, trash/restore,
permanent inquiry deletion and Contact Form 7 form deletion. It uses the existing
complete JSON, frozen pending queue and confirmed S3 history; no new runtime,
authentication helper or infrastructure is introduced. This is not a formal release.

## Save and recovery boundary

Flamingo writes its post before metadata and has no completed-update hook.
Core post/metadata callbacks track inbound-message IDs; normal WordPress shutdown
captures the completed request state once per ID. Multiple writes in one request
coalesce rather than becoming distinct intermediate recovery versions. The initial
CF7 receipt callback clears its pending ID to avoid duplicate capture.

Successful core deletion produces a tombstone. Whole-site replay removes the
post, metadata and relationships, and recalculates channel counts. Form deletion
does not cascade into retained inquiries or rewrite pages containing its shortcode.
WordPress deletion is not physical deletion of retained S3 versions. Storage failure
retries the same frozen change/tombstone, never the later DB state. Only confirmed
S3 history is recoverable; loss before confirmation omits the final operation.

## Artifact and packaging

[Verified ZIP](../../release-candidates/20261024-form-lifecycle/ozeki-wordpress-resilience-0.3.1-forms-lifecycle-final.zip)

SHA-256: `1eba8cbabfcc18adceedb1d002b9f39da5e43fd220739689f67bd725c77d25ac`

7,355,612 bytes / 3,805 files. Source matches the ZIP; AWS SDK/vendor is unchanged.
The changes from PR #22's ZIP are FormHistory.php, Plugin.php, English/Japanese
READMEs and forms.md. No test helpers, credentials or inquiry contents are bundled.
Earlier candidates remain historical evidence; use this ZIP for lifecycle support.

## Validation

- Actual standard plugin PHP API operations and normal request shutdown used the
  existing trial inquiry/form, not existing business content or browser clicks.
- Edit, spam, ham, trash, untrash, inquiry delete and form delete produced S3
  sequences 42–48. Each was reconstructed on the existing recovery WordPress from
  the SAME prior S3 baseline plus confirmed history. Body/status/exact metadata/
  channels matched; deleted post/meta/relations remained absent. Source DB was
  not a recovery input. Mail calls were zero throughout.
- The trial form and inquiry are intentionally deleted on both sites. The page
  containing the trial shortcode was not edited and no longer has an available form.
- Isolated actual WordPress with memory transport covered original-write failure,
  deletion-history failure, frozen retry and duplicate shutdown/resume suppression.
  These are injected failures, not actual AWS outage tests.
- ZIP-extracted syntax and forms/comments/Checkpoint/cleanup tests passed, including
  tombstone idempotence, channel counts and no form-to-inquiry cascading deletion.
- Fresh installation and update from the PR #22 forms-final ZIP passed in separate
  folders/tables in the existing dm container. Settings, content, stable identity,
  comments, forms, inquiries, channels, restore results, dependency activation and
  frozen change/deletion pending records were preserved. Admin rendering passed.
- Standard-role S3 reads found identical 48-entry history before/after package
  tests; S3 writes/deletes were zero. Running-site probes were byte-identical.
  [Sanitized validation](../../release-candidates/20261024-form-lifecycle/validation.json).

## Limits and issue classification

The tested optional dependencies are CF7 6.2.3 and Flamingo 2.6.4 on PHP 8.3.36.
They are installed separately; CF7's PHP 8.3+ requirement is separate from base
Resilience's PHP 8.1+ requirement. Use the recorded versions and a compatible
site baseline. Runtime-version migration across a baseline is not accepted here.

Unsupported: process loss before request-end capture, simultaneous same-asset
writes, direct SQL, third-party hooks writing after capture, attachment binaries,
address-book entries and external mail/Akismet delivery or training effects.
Intermediate changes within one request are not preserved separately. Whole-site
abrupt process-kill rollback and periodic execution remain unaccepted. Recovery
does not call mail or Akismet APIs. Existing 5 MiB operation limits still apply.

**Product change:** connects lifecycle changes and deletion to history/replay.
It retains PR #22's unmapped-author correction; that is not a new fix in this PR.

**Test infrastructure:** a metadata comparison double-serialized raw values; the
comparison was corrected. A shell-loop argument was lost and the test request
stopped at its invalid-operation guard before any mutation; a script file fixed
argument delivery. Existing DISABLE_WP_CRON probe warnings and narrow first-boot
WordPress/Flamingo maintenance-event allowances are test details, not product bugs.

**Environment:** reuses dm's previously adjusted 320 MiB / 640 MiB memory+swap
container. Lifecycle tests left oom_kill at 3, unchanged; no new resource setting
was applied. Do not infer a universal memory minimum or diagnose older unexplained
failures from this evidence.

No live changes in this PR preparation. Existing content, IAM and periodic
configuration are unchanged. Merge and formal publication are not part of this task.

## 日本語要約

Flamingoの受信後編集・スパム判定／解除・ゴミ箱／復帰・完全削除とCF7フォーム削除を
正式履歴とサイト全体復旧へ接続します。通常リクエスト終了時の最終状態を保存し、
削除成功時には削除記録を保存します。未確定の操作は復旧候補にしません。

実S3履歴42〜48の各段階を復旧先で照合し、メール呼出し0、既存内容保持を確認済みです。
最終ZIPの新規導入・更新でも設定・履歴・未確定記録を保持しました。試験側の比較・引数
修正と製品対応を区別し、同時変更・終了前プロセス喪失・添付本体等の制限を明記します。
既存コンテンツを変更せず、定期実行と正式公開は後回しです。
