# Recovery display and ordinary-save corrections — 2026-11-24

Status: implementation and isolated verification complete; reviewed for main integration from `codex/recovery-content-usability`. This is a source update, not a release. Production and submitted rc.20 remain unchanged.

## 原因と共通の仕組みでの修正

特定のページIDや文書だけへの修正ではありません。次の3つの共通処理の境界を変更しました。

| 原因 | 共通処理での修正 | 再発を検出する確認 |
|---|---|---|
| 記事として戻す情報と、復旧先で実行するテンプレートを混同していた | 保存元のテンプレートを自動適用せず、復旧先の準備済み構成を維持。ID・テーマとの関連も確認する | レコードの存在だけでなく、WordPressが実際にテンプレートを選択し本文を表示することを確認 |
| 対応する文書参照と、その文書を読む権限・表示時の実行可否を分けていなかった | 埋込み先文書自身の閲覧条件を判定し、描画結果だけに安全処理を適用。原文を変更しない | 公開ページから会員文書を参照し、非会員・会員・管理者の違いと未知命令の非実行を確認 |
| 閲覧条件に影響しない自動保存も全添付再照合を起動していた | リビジョンと編集ロック情報を起動対象から除外し、初回保存と日常保存で保存先ごとの完了状態を共有 | 自動保存と通常保存の重なり、実際の閲覧条件変更、競合時の未完了保持、再復旧を確認 |

例外を捕まえるだけの対処ではありません。不要な再照合の起動原因を修正したうえで、残る競合では未完了と診断を残し、既存の再開操作につなぎます。ロック・履歴の順序・記事保存失敗の扱いは維持しています。

確認は、communityの初回保存と履歴77の固定コピーを使う隔離環境と、新規試験用S3領域で実施しました。ブラウザ編集の追記まで再復旧でき、共通する対応データ46件は一致しました。件数差の1件は管理画面が生成した未投稿の自動下書きでした。特定できた原因への対策であり、任意の外部プラグインやすべての同時編集負荷まで検証したという意味ではありません。

## Changes and boundaries

1. Archived `wp_template`, `wp_template_part` and `wp_navigation` are not activated as destination software configuration. The prepared destination's published records and their taxonomy relationships are retained with collision-free IDs. Previously recovered records are not promoted to trusted preparation. Unresolvable references are omitted and reported. A source-selected page template unavailable on the destination falls back to its prepared default.
2. `ozeki_markdown_document` accepts a positive document ID only. The target document's publication, password and WP-Members viewing conditions are checked before invoking the installed, recognized renderer. Rendered HTML is filtered; embedded commands are not recursively executed. The Markdown original remains unchanged. Invalid references have a short administrator-only explanation. Unknown membership extensions are not granted access by this path.
3. Revision autosaves and editor lock metadata no longer trigger media reconciliation. A verified, unchanged complete baseline seeds the same destination-scoped completion state used by daily saves. Genuine access changes still trigger capture. Shutdown contention retains pending work and a diagnostic rather than terminating with an uncaught exception. Locks, ordering and article-save failure handling remain in place.

No archive-format change. Existing originals/history are read without rewriting them. Earlier releases do not acquire these corrections. Previously textified embeds require recovery from their originals or an explicit administrator reference edit, not bulk decoding.

## Evidence and reproducibility

Use disposable WordPress installations at localhost ports 18931/18932, the same trusted theme/plugins, and separate test-only S3 write prefixes. Production source access is read-only. The fixed initial-save/history-77 input contains 638 objects. Mail, Cron and unrelated external HTTP are disabled. No software installer is invoked during recovery; installed software hashes remain unchanged.

Before applying the corrections, `tests/content-usability.php` failed against exact rc.20: prepared templates were lost and member/admin Markdown embeds were unavailable. During implementation, browser verification exposed duplicate theme taxonomy terms: records existed but WordPress selected a theme-file fallback. The correction reuses matching taxonomy terms, and the regression now also calls WordPress's actual template resolver.

| Check | Result |
|---|---|
| Prepared header, front-page template and navigation | Preserved and selected by WordPress; actual homepage content visible in Chrome |
| Public page embedding a member-only document | Guest cannot see document; member/admin can read heading and table |
| Embedded unknown shortcode, code example, invalid attributes, prior filter denial | Execution denied; prior denial preserved; original hash unchanged |
| Initial autosave overlapped with normal save | Both HTTP 200; autosave 0.75 s, normal save 6.02 s |
| Subsequent normal save | HTTP 200, 3.51 s; committed value present |
| Browser editor with protection on | Page updated notification; added paragraph and document reference saved |
| Rerecovery from new test baseline/history through 10 | Browser-added paragraph, document and member login usable; guest restriction retained |
| Content comparison | All 46 common supported records exactly equal after URL normalization; only excluded record was an editor-created `auto-draft` |
| File access and membership state | Equal across resave/rerecovery; no pending article/attachment/shared queue |
| PHP / transport | No PHP Warning/Fatal/Uncaught in captured server logs; 1,782 measured S3 operations, zero transport failures |

Timings include the isolated host and scoped SSH/S3 relay; they are not production performance promises. This verifies the stated core and supported-plugin paths, not arbitrary third-party renderers or every concurrent editing workload.

Offline checks passed: `media-autosave.php` (new revision/real-access-change/lock-retry/scope contract), prepared settings, application rules including Flamingo, media/file scope, attachment pending, editor save, capture failure, checkpoint verification, reference context and no-software-install. Existing `review-safe-content.php` passed on the disposable WordPress. The new offline test is included in the existing contracts workflow. GitHub Actions must also pass on the integrated main commit; local checks are not presented as an Actions result.

## Preserved resources

The fixed source's 638 hashes are unchanged. Submitted rc.20 ZIP SHA-256 remains `90849e809d215b9472fba3c36226a171fffb432922cf7aaf6eb14ea1a516e610`; tag object remains `8111b17c2b5e4c26bcc53890e2a90c04e3114cef`. The research worktree is preserved; main integration is limited to the reviewed source, guides, tests and this record. No production update, candidate ZIP build, submission or email was performed.

Evidence: [non-content result JSONs](content-usability-20261124/); local browser proof `content-usability-rerecovery-20261124.png`. Private fixture/logs remain on dm under `/tmp/owr-content-fix-20261124`; do not publish them. Disposable containers were removed after verification. New test S3 assets were retained; existing source assets were never written.
