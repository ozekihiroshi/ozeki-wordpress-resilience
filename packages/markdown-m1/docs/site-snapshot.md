# Complete site baseline and reconstruction

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

This document includes historical candidate design and verification records. Follow the current [user guide](user-guide.md). Historical code-restoration results do not describe the current recovery feature.

## Baseline and Checkpoint operations

This describes the current implementation; this documentation update does not replace published ZIPs or expand their verification scope.

- **Create complete initial snapshot:** pause editing, resolve pending history and acknowledge that the current source is trusted. This reads the supported live DB content and files. Repeating it creates a new Baseline, not a normal Checkpoint or permission to delete earlier points.
- **Create complete Checkpoint:** select an existing complete point. Its S3 assets and subsequent confirmed S3 history supply the new point. Scheduled complete-site creation uses the same path. Missing inputs or history gaps stop creation; they do not trigger live recapture.
- **Restore complete site:** select a Baseline or Checkpoint and an inclusive formal-history end. Choosing its `through` restores that point alone. A later end requires every necessary subsequent record and referenced resource. PHP callers omitting the end use the history tail observed for that invocation.

### Common storage and independence

Both use `owr-site-snapshot-1` under `site-snapshots/<identity>/`. The manifest records `origin` (`administrator_initial` or `confirmed_s3`), `through` and resource references containing Key, VersionId and SHA-256. Current separated resources include `assets/metadata.json`, `assets/data/`, captured Markdown, uploads and `software.zip`; the asset layout is `owr-separated-assets-1`.

The common saver creates a fresh complete set in that point's own `resources/`, retrieves and checks its fixed versions, then writes `manifest.json`. Loading rejects resource references outside that point's resource prefix. Creating a point depends on its selected ancestor and subsequent history; recovering the completed point does not depend on that ancestor. The Baseline itself is directly usable as the first recovery point.

Input assets must remain available until creation completes. Independence is not deletion authorization: other retained points or history ranges may still need those assets. A compatible destination and supported recovery rules are required; independent storage does not imply unconditional restoration or harmless data.

### Separate legacy Markdown path

The older asset-level path uses `owr-md-snapshot-2` under `snapshots/<sequence>/<identity>/`, with its own manifest/assets and initial-capture/Checkpoint controls. It is distinct from `site-snapshots/`. Individual text recovery does not restore complete-site media, software and relationships. Use **Site-wide recovery — primary workflow** for the operations above.

## Recovery through a selected formal history number (working tree)

In Tools → Resilience, choose a complete Checkpoint and **Formal history end**, then confirm destination replacement. The end is an inclusive confirmed sequence, at or after the Checkpoint boundary; choosing the same number restores the Checkpoint alone. The selector shows confirmed timestamps and operation labels where recorded. One user edit can produce multiple formal records, so a record boundary is not necessarily a complete editing session.

Only records through the selected number and their fixed-version originals are applied. Missing history, a missing end, invalid Checkpoint/end combinations or missing/corrupt required resources stop recovery before content replacement; later records are excluded. The submitted end remains fixed even if newer history arrives. Results retain the Checkpoint boundary, requested end, actual applied end and detailed JSON. Existing three-argument PHP callers still recover through the history tail observed by that invocation.

Use a prepared, dedicated recovery WordPress. Reusing an existing test container and DB service with separate content/table namespaces is sufficient; destination-only scratch data preservation is not a product requirement. Theme/menu/configuration changes without supported formal history still require a new trusted baseline. No schedule, deletion or publication mechanism is added. This change is not included in the frozen `site-retention-final` ZIP.

The goal is the same site's content, appearance, navigation and supported behavior on a new WordPress, not merely a readable Markdown document. `SiteSnapshot` supplements the Markdown original/history path.

An administrator-trusted initial capture stores native posts (including pages, revisions, templates, navigation and global styles), metadata, taxonomies, comments, presentation options, raw Markdown, upload files, the active theme/parent and explicitly selected runtime plugin code. Content records are portable JSON, Markdown remains raw `.md`, media remains individual files, and software is a ZIP with per-file hashes. This is not an SQL/database-image restore. Source administrator credentials, sessions, WordPress/AWS configuration, cron queues and SMTP credentials are not imported. WP-Members core subscriber password hashes and configured fields are included when its adapter is active; see [membership scope](members.md).

`site-snapshots/<identity>/manifest.json` is written last and pins every resource by VersionId and SHA-256. A Checkpoint copies the complete baseline into its own resource prefix and applies later formal Markdown, Page and Post history, including new articles, supported referenced images and trash/untrash operations. It does not require the initial snapshot's resources during recovery. Missing history or damaged resources blocks reconstruction. Later theme, menu, template, global taxonomy administration and arbitrary plugin changes do not have these S3-first adapters: capture a newly trusted baseline for those changes. Unused media is outside incremental coverage. Native permanent deletion, featured-image selection/replacement/removal and category/tag assignment changes are captured after successful operations; see [native detail scope](native-details.md). No live-source data is silently adopted during Checkpoint creation. The supplementary asset timer is not a complete-site scheduling guarantee; periodic execution remains deferred.

Recovery includes only operations confirmed in S3 formal history after the trusted baseline. If WordPress applied an operation but history remains pending when the source is lost, omit that operation: omit an unconfirmed new article, or retain the previous confirmed version for an update. Prepared originals and local pending records are not recovery authority. Rescuing the final unconfirmed operation is not required. A surviving source can retry history confirmation after verifying its applied state.

Use **Site-wide recovery — primary workflow → Restore complete site** for this path. **Confirmed formal history / Individual recovery** restores selected text and attributes only, updating matching asset identities or creating missing ones; it does not restore media files, themes, menus or complete site relationships and leaves unrelated target content intact. Earlier asset-snapshot controls are supplementary and are not whole-site snapshots. Destination preparation is a normal administrator task; continuous replication is not required. Restored publication state is preserved; network exposure and DNS are administrator responsibilities.

Tools → Resilience provides complete initial capture, Checkpoint and destination replacement controls. The current UI selects Markdown Documents and the active theme/parent; active supported CF7/Flamingo, WP-Members and TablePress dependencies are also included by their adapters. Arbitrary plugin settings still require explicit coverage; admin-only Backup for S3 and Plugin Check are excluded and recorded. Mail delivery and external portal authentication remain external services, not fabricated successes.

Recovery requires a separate destination URL, write protection disabled, InnoDB content tables, ZipArchive, writable resource directories and the recorded WordPress release line (same or newer maintenance patch). S3 is read-only at the destination. All resources are downloaded and verified before content replacement. The destination's existing content, presentation options and changed files are backed up in a private temporary directory outside the web root. Native IDs are retained within the replaced content set so block/menu/template references stay intact; source authors are represented by non-privileged display identities. Supported WP-Members subscribers are separately restored with their saved password hashes and fields; unrelated account collisions are rejected. Destination administrative users remain. If restored WP-Members settings enable moderation, the designated destination administrator must already be activated; preserved credentials alone do not ensure login. Check activation before recovery and verify fresh standard-screen authentication afterward. See the [administrator access checklist](members.md#administrator-access-during-setup-and-recovery). Do not disable moderation or approve unrelated members.

Local URL references are rebased recursively, including serialized metadata. Raw Markdown bytes remain unchanged; rendered links are rebased. Existing identical software files are hash-verified and reused. Failed writes roll back touched files and transactional content; process-kill recovery/automatic rollback is not yet an accepted guarantee. A new request loads the recorded theme and plugin code. Do not overwrite active code during concurrent use; perform recovery on a designated destination.

2026-10-24 real acceptance: wp.ceri.link → existing wp-backup.ceri.link using default EC2 role authentication and S3 only for recovery input. 73 post records, 9 raw Markdown files including revision originals, 23 media files and 558 theme/Markdown program files matched. Both public pages, menu navigation, local PDF and three original images were checked. Source WordPress 7.1.2; destination maintenance patch 7.1.3. Source 39-record baseline remained unchanged. The new Resilience code was then deployed on source and its admin controls inspected; source content and scheduling configuration remained unchanged. This is a manual whole-site acceptance, not a periodic execution acceptance or universal plugin compatibility claim.

Subsequent adapter and combined acceptance is recorded in [combined scope](combined.md). The initial measurements above are historical evidence, not the complete current adapter list.

## Reading the recovery result

The last site-wide result shows success, failure or an unfinished attempt, the exact snapshot key and S3 Version ID, the Checkpoint history boundary, subsequent applied history range and record count, and restored post-record / written-file counts. Post records include all post types, not just public articles; unchanged files may be reused. Failure or an unfinished attempt does not imply zero changes or completed rollback. Detailed JSON retains the latest attempt and previous successful result. The display is local administrative feedback, not a replacement for S3 formal history. If the selected Checkpoint cannot be found in the current listing, its boundary is shown as unavailable rather than inferred.

## Confirm source history before recovery

Use the [save-history resume procedure](save-resume.md) when the surviving source reports pending operations. Confirm the intended operations in S3 before relying on them in a later site recovery. Source loss before confirmation does not promote prepared originals into recovery history. 履歴未確定の場合は同手順で再開し、対象操作のS3正式履歴確定を確認します。未確定操作を復旧対象へ推測で追加しません。

## Optional inventory for a reused test destination

The intended product destination is a newly prepared, dedicated WordPress, not a running unrelated site. The following inventory describes the historical reused-lab procedure; it is not a product prerequisite or a requirement to preserve destination-only drafts. Prefer a simple separate content/table namespace when reuse makes the starting state costly to understand. Preserve unrelated test data through environment preparation, not by changing reconstruction semantics.

1. Pin the intended Checkpoint Version ID and confirmed-history boundary. Assemble expected content from S3 without restoring it. If either input cannot be read, report unknown and do not treat it as an empty source.
2. Enumerate **all** destination post records, including draft, auto-draft, private, trash, revisions and other post types. Do not use a published-post-only query.
3. After URL relocation, compare matching native IDs and list changed content/attributes. Separately list source-only IDs (additions) and destination-only IDs (removals). An ID match does not prove the two records have the same origin: inspect content/type differences, especially on a previously unrelated destination.
4. Review destination-only records before replacement. Preserve needed content separately or choose an appropriate destination. An empty auto-draft is still reported; the tool must not silently decide it is disposable. Do not automatically reinsert arbitrary records after recovery: IDs and related metadata may conflict.
5. Recheck if the selected history or destination changes. The comparison does not lock writers. Keep editing paused during the final check and replacement.
6. Verify the recovered target against the selected S3 data and check the agreed preservation scope. A failed preservation check remains recorded even if a corrective action later succeeds.

The repository's `tools/testing/site-recovery-post-diff.php` is a pure test helper; callers supply assembled expected records with destination URLs and all destination records. It lists source-only, destination-only and changed rows, and marks destination-only rows for review. It performs no restore or automatic approval. The corresponding test covers published records, drafts, auto-drafts, additions, changed bodies, an empty source and duplicate IDs. It is not bundled into the validated ZIP. The temporary lab runner uses internal replay through reflection; it is test infrastructure, not a supported public API or product dependency. This is a post-record comparison, not a full member/metadata/file preservation guarantee.

### 履歴68の結果と事前確認手順

既存Checkpoint33＋後続正式履歴34～68から、復旧先の試験記事37を再構築しました。本文SHA-256はS3原本と一致し、タイトル・スラッグ・公開状態も一致しました。S3履歴、会員、コメント等の前後照合も確認しました。メール送信・定期実行・正式公開は行っていません。

当初の試験前確認は復旧元の行だけを走査していたため、復旧先にのみ存在した空の自動下書き30を見落としました。サイト全体の置換によるその除外は製品の既定動作であり、差分検出漏れは試験基盤の不足です。退避した完全な元行を別途戻し、最終的な既存投稿の照合は一致しました。最初の失敗結果も保存しています。製品が復旧先独自の下書きを自動保持するように変更したわけではありません。

この双方向比較は、再利用する試験環境に残ったデータを把握するための補助手順です。製品の想定復旧先は新しく準備した専用WordPressであり、復旧先だけの下書きの保全は完成条件ではありません。試験環境の把握が複雑なら、既存コンテナ内でDB接頭辞・ファイル領域を分ける等の簡単な準備で解決します。新しい製品保全機能や必須検査にはしません。過去の差分検出漏れと修正記録は、試験基盤の経緯として保持します。
