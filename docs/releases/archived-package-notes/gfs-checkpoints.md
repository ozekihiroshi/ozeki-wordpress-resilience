# Historical GFS verification / 過去のGFS検証記録

Not current setup instructions. [Current guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/gfs-checkpoints.md).

# GFS Checkpoints (unreleased development)

Weekly, monthly and yearly rules are independently enabled in Tools → Resilience. Each has a start time and retention count (weeks, calendar months, calendar years). Weekly selects a weekday; monthly selects a day or month end; yearly selects month/day. The displayed WordPress timezone applies. Nonexistent dates clamp to month end; the next month/year keeps the configured day. Old interval configuration continues until settings are explicitly saved; saving the GFS form replaces it. Settings changes affect new points, not existing recorded expiry dates.

Coincident rule timestamps create one complete Checkpoint with all matching labels. Different times remain separate. Every new occurrence copies complete resources even when content/history is unchanged. The manifest records actual confirmation time, planned time, timezone and each label's expiry. Same-slot repetition checks the confirmed S3 manifest under the existing writer lock and does not create another point. Manual creation does not inherit a previous point's GFS labels. This is a complete supported-content reconstruction set, not a SQL/server image or a promise to restore unsupported integrations.

Keep a Checkpoint while ANY GFS label is active. The separate detailed-history window retains its boundary baseline, recent points and required subsequent history/resources. Historical GFS archives do not require every intervening history record. An unchanged old article/image remains in every applicable new full point: resource age is never a reason to discard currently needed information.

Complete-site automatic deletion runs only after a successful scheduled creation. Manual deletion uses the preview and the same policy. Both preserve the latest point, required history/resources, active labels and unknown resources. Recalculate the exact-version plan before deletion; reject stale plans or incomplete inventory. Object Lock/Legal Hold never bypassed; a locked member holds its entire retired Checkpoint. Delete failure stops with completed and uncertain entries reported. Interrupted deletion can leave unreferenced data for separate review; no broad orphan sweep is added. The current manual control deletes only policy-eligible expired resources, not arbitrary still-retained points or whole-store resets.

Optional S3 protection (`retention_days`, 0 = no requested product lock) is independent of GFS retention and detailed-history days. Existing/bucket-default locks still apply. Real version-list/read-lock/delete permissions are prerequisites for real cleanup; this implementation does not grant them. Existing IAM/S3 assets are untouched. Ordinary renewal is not the lifecycle mechanism; the earlier renewal backend remains available for compatibility, but its button is removed from the normal screen.

WP-Cron provides execution opportunities, not exact wall-clock guarantees. The next future slot is registered after a run. A delayed run records actual confirmation time and the original planned slot; missed past points are not invented. A failed run reports failure, skips cleanup and schedules the next future occurrence; no automatic same-slot retry/rollback added. An existing server cron runner may provide regular triggers. Settings are per site; starting times can be staggered.

## Differential verification, 2026-10-25

- Local PHP memory S3: three-way collision, different times, month/leap boundaries, validation; recorded labels; weekly/monthly expiry cannot retire an active yearly point; all-label expiry; archived points do not pin intermediate history; unchanged copies; last/boundary preservation; deletion locks/stale plan/denial.
- Admin action with WordPress API fixtures: saves all three rules, registers next slot, rejects invalid input without replacing configuration.
- Existing dm isolated WordPress: actual settings renderer, WP single event registration, deliberately due slot dispatched through WP hook, one point/three labels, repeated-slot suppression, independent next occurrence, automatic/manual cleanup through memory S3. Original options/cron restored; content/member hashes unchanged; no mail.
- Existing checkpoint verification, failure reporting, point-in-time and retention tests pass. Not a browser test, elapsed-week/month test, actual AWS GFS write/delete test, ZIP installation or release. No public ZIP modified.

[日本語](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/02ec4e8/packages/markdown-m1/docs/gfs-checkpoints-ja.md)

## Configured-time operation and verified boundary

1. In Tools → Resilience, check the displayed WordPress timezone and select the required weekly/monthly/yearly dates, times and retention counts. Stagger sites on a shared server. Save and check the next reservation.
2. Ensure WordPress has an execution opportunity. WP-Cron does not itself guarantee exact-time execution; use the site's existing approved trigger arrangements. A reservation alone is not proof of successful capture.
3. After execution, check the success/failure record, confirmed point and next reservation. A successful point requires fixed-version verification of the complete saved set before manifest confirmation. On failure, investigate the recorded cause; do not treat a scheduled or partially written point as confirmed.
4. For isolated tests sharing core files, account for unrelated Cron events, automatic core/plugin/theme updates and mail before triggering the standard entry. Scope temporary guards to the check and remove them afterwards. This is test-environment preparation, not an added product dependency.

On 2026-10-25 one real-time weekly slot passed via the standard wp-cron.php entry invoked from the existing server: 20:44 JST scheduled, 20:44:02 dispatched, 20:44:04 confirmed. Three unchanged resources were copied to independent keys and verified before the manifest; the next November 1 reservation was registered. This does not verify HTTP page-triggered loopback, later weekly/monthly/yearly occurrences, browser GFS setup or actual deletion. The test environment's unrelated core-update processing and later guarded UI check are recorded separately in [the timed-execution report](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/gfs-timed-acceptance.md). The ZIP installation/update evidence below is a different test; no ZIP was rebuilt for this documentation update.

## Additional real-S3 differential verification, 2026-10-25

Existing community isolated WordPress and the standard EC2-role SDK provider wrote only a fresh dedicated `gfs-verify-20261025-c62a17/` prefix. A small complete test set (Markdown, image, metadata) was used. Three coincident rules produced one Checkpoint; repeating the same slot returned the same manifest VersionId without any additional PUT. Exact-version readback confirmed all three labels and calendar expiries calculated from actual confirmation time. The coincident date was a deliberately selected test slot (Sunday January 1), not an assertion that a historical snapshot was taken.

A separate newly written immutable fixture with expired weekly/monthly dates and an active yearly date was retained specifically for `GFS retention`, including all its resources, while a newer point existed. These explicit fixture dates did not result from waiting months or modifying the genuine product-created point. No original asset was overwritten.

`ListBucketVersions` was denied by the existing role. The product used its read-only current-fixed-version fallback; hidden versions remain unassessed and zero candidates are authorized. GFS preservation was verified by its explicit retention reason and resource membership, not merely by an empty candidate list. This is not actual deletion eligibility or execution acceptance. No Delete/retention mutation/IAM calls, elapsed-time scheduling, browser or ZIP tests were performed. Sixteen fresh objects remain; existing parent inventory and WordPress content hashes were unchanged, temporary options restored, mail count zero, published ZIP unchanged. Evidence: `release-readiness/gfs-real-s3-20261025` in the development workspace.

## ZIP installation/update / ZIP導入・更新

New distribution ZIP verification reused the existing dm WordPress core and DB service with isolated tables/content. Fresh activation and replacement of published v0.3.1-pre.1 preserved GFS/S3 settings, the registered (not executed) slot, two synthetic pending records, diagnostics, recovery results and test content. Existing formal history and its original were read from real S3 using standard authentication. Installed files matched the ZIP byte-for-byte. This was PHP-driven extraction/activation/reload, not browser upload, queue resumption, new S3 writes, real deletion or elapsed-time scheduling. A duplicate DISABLE_WP_CRON warning came from the test bootstrap/shared configuration; assertions passed and it is not evidence of a product defect.

## Unset Object Lock correction / ロック設定なしの修正（2026-10-26）

The new unpublished `ozeki-wordpress-resilience-0.3.1-gfs-lock-read.zip` adds one narrow correction: only HTTP 404 with AWS code `NoSuchObjectLockConfiguration` is treated as absent retention/Legal Hold configuration, and only after HEAD of the same Key/VersionId succeeds. AccessDenied, transport failures, missing versions and unrelated 404s remain blocked. Both complete-site and legacy asset-level preview use the common reader. No lock bypass or deletion permission is added.

新しい未公開候補は、AWSコードNoSuchObjectLockConfigurationかつHTTP404だけを、同じKey/VersionIdのHEAD成功後に設定なしと扱います。権限拒否・通信失敗・版の不在・その他404は保留のままです。サイト全体と既存資産単位のプレビューで共通処理を使用し、ロック回避・削除権限は追加しません。

The earlier version-list permission gap was resolved by the administrator for the dedicated GFS trial prefix only. Existing real S3 assets were read without mutation: 16 versions, 3 retained points/12 resources, 4 obsolete candidates, no blocked rows, identical before/after inventory. This is a preview with a test cutoff of the current time, not an applied retention-setting change or deletion authorization. IAM's explicit deletion deny remains. The existing admin renderer produced the preview HTML in isolation; no live browser administration test or deployment is claimed. Denial/network/missing-version cases were injected into memory S3 tests, not caused on AWS.

以前の一覧権限不足は管理者が専用試験prefixに限り解消しました。既存実S3資産の読取りでは16版、保持3点・12資源、候補4件、保留0件、前後一覧一致。現在時刻を試験用基準にしたプレビューであり、保持設定変更や削除許可ではありません。IAMの明示的削除拒否は維持しています。既存管理画面の表示処理を隔離してHTML出力した確認で、稼働サイトへの配備・ブラウザ操作は含みません。権限拒否・通信障害・版の不在等はメモリS3への失敗注入であり、実AWS障害ではありません。

Installation/update verification is separate from this real-S3 preview. The distribution must preserve settings, formal-history references, synthetic pending records and diagnostic/recovery results; synthetic queues must not be resumed. See the candidate's release validation record for the exact ZIP hash and completed checks. Published ZIPs remain unchanged.

導入更新の検証は実S3プレビューと別です。設定・正式履歴の参照・合成未確定操作・診断／復旧結果を保持することを確認し、合成キューは再開しません。正確なZIPハッシュと完了した検証は配布候補の検証記録を参照してください。公開済みZIPは変更しません。

## Cleanup operation and post-deletion recovery (2026-10-26)

1. Select the complete-site retention preview for the intended bucket/prefix. Verify a complete version inventory, the retained recovery points and subsequent history, candidates and blocked reasons. The legacy Markdown asset-only cleanup path is different.
2. Confirm the scope and candidate Key/VersionId pairs before executing. A preview alone is not authorization. Recalculation must still match the reviewed plan; investigate failures rather than broadening permissions or bypassing Object Lock/Legal Hold.
3. After execution, inspect the deletion result and remaining fixed versions. Verify recovery from the retained Checkpoint and the chosen subsequent formal-history boundary into a prepared recovery environment. Do not infer restore success from successful deletion alone.

A disposable-prefix test on existing community/dm infrastructure saved 33 versions, reviewed 16 candidates (old Baseline and history 1 with its originals), deleted exactly those versions, and read back all 17 retained versions with unchanged SHA-256. The independent Checkpoint through 1 plus history 2 restored the test page body/title/publish state, image bytes and relocated links on dm without the old Baseline or source DB. Current-time cutoff was deliberate; this did not wait for natural expiry. Objects had no retention/Legal Hold setting. Existing prefixes retained their deletion deny.

**Verified:** real S3 operations through existing product methods. **Not verified here:** browser/admin cleanup, scheduled automatic deletion, locked-object deletion, full elapsed retention periods or interrupted deletion. Earlier preview, timed capture and ZIP installation/update records remain separate. No product code or ZIP was changed. The initial PutObject denial was an effective-role permission issue, resolved by the administrator before the successful run; it required no product fix. See [the bilingual acceptance record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/deletion-recovery-acceptance.md).

Later standard-admin and scheduled automatic cleanup passed in the disposable prefix: 17 versions deleted through the browser and 14 by scheduled cleanup, with active weekly points retained and dm recovery successful. See the [scoped follow-up](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/cleanup-browser-scheduled-acceptance.md). The earlier record above remains limited to its original test.
