# 0.3.1 comment history — final review

This candidate extends the independent WordPress + S3 product, not the preserved
research execution path. No new runtime dependency or authentication helper is added.
It is a review candidate, not a formal release.

## Behavior

Core comment creation, editing, moderation, trash/untrash and deletion use complete
JSON originals and the shared formal S3 history. Whole-site recovery restores the
body, core attributes, article/reply relationships and approved counts. Individual
text/attribute recovery is explicitly separate and rejects comments.

WordPress persistence, S3 original storage and formal history confirmation must
all succeed. The adapter freezes the successful callback payload and reuses it
on retry; it no longer fetches the comment later by ID. Core insert/status hooks
already receive a persisted result object: this is not raw-input interception,
S3-first comment mutation, or a distributed atomic commit. Unconfirmed operations
are omitted if the source disappears. Existing article S3-first behavior is retained.

Final review additionally found that pending comment history did not prevent S3
configuration changes. The candidate now rejects configuration changes while
article or comment history is pending, retaining both the destination and payload.

## Reviewed artifact

`release-candidates/20261024-comments/ozeki-wordpress-resilience-0.3.1-comments-reviewed.zip`

SHA-256: `24b2ee1d5c9c38cd93dc94361849755451bd5741346024313f686df3ebc40e87`

3,803 files; 7,347,035 bytes. All package source files match; the AWS SDK is unchanged.
No test tools or authentication helpers are packaged. This supersedes the earlier
comments-final ZIP (`2c0606241526efae108ad3f57fd0445c05e39864e2a861091e03f77ac2c16fcd`)
for this PR because of the pending-configuration guard. Earlier evidence is retained.

## Evidence and scope

- Existing live trial comments exercised add/edit/approve/reply/trash/untrash/delete;
  complete-site recovery used the fixed S3 baseline and formal tail, without the source
  database. Orders 34–36 additionally confirmed edit/hold/approve frozen payloads,
  source state and recovered state agree. Operations used standard WordPress PHP
  APIs; browser verification viewed the recovered comments, not form submission.
- Isolated WordPress tests cover frozen data against later callback mutation,
  original/history failure and same-payload resume. Failure injection uses memory
  transport, not a claimed AWS outage.
- Reviewed ZIP syntax and comment/Checkpoint/cleanup memory contracts pass, including
  real configuration-handler rejection with article/comment pending records.
- Candidate installation/update acceptance is recorded in `validation.json`.
  Dedicated tables/folders in the existing dm container are used; running site tables,
  S3 assets and settings are not changed. History remains 36 confirmed operations.
- English/Japanese package READMEs agree on recovery boundary and exclusions.

## Product limits versus test issues

Product limits: arbitrary comment metadata/types, external comment services, direct
SQL changes and notification replay are excluded. Same-comment concurrency/load and
whole-site process-kill rollback are unaccepted. Comments include private email/IP;
WordPress deletion does not delete retained S3 versions. A valid site baseline and
parent article are required. Scheduling, live cleanup and formal release are deferred.

Test infrastructure corrections: comparisons originally included allocated postmeta
IDs and two regenerable Markdown caches; checks now preserve original source/attributes
and exclude only those derived fields. A separate count assertion omitted existing
trial replies. Installation checks now allow only four known WordPress first-boot
maintenance Cron additions while preserving every existing event. None of these are
claimed as product fixes. The duplicate DISABLE_WP_CRON warning is a probe issue.

One initial live restore exited without diagnostics. Inspection confirmed no target
change; a diagnostic retry and subsequent restores passed. Its cause is still unknown,
not classified as a fixed product or environment defect. The earlier in-app browser
blank-canvas issue remains separate from the plugin (Chrome comparison worked).

## 日本語要約

コメントの同一確定データ保存・全体復旧と、未確定履歴がある間の保存先設定変更拒否を
含む候補です。WordPress・S3原本・正式履歴が揃った操作だけを復旧対象とします。
個別文書復旧はコメントを含みません。英日READMEに対応範囲・制限を記載しています。
試験側の比較条件修正と製品修正を分け、初回復旧の原因不明終了も未解明として残します。
既存コンテンツは変更せず、定期実行・正式公開・マージは今回行いません。
