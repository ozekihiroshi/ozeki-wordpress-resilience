# Core comment history and site recovery

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

## Contract

With protection enabled, successful core comment operations on published or
already protected `post`, `page` and `ozmd_document` assets append complete JSON
originals plus metadata, then use the existing immutable, version-pinned S3
formal history. No content delta or site-wide inventory is generated per comment.
The prefix has one writing WordPress. The existing SDK credential provider and
S3 permissions are reused; no worker, role or infrastructure is added.

An operation is established for recovery only when WordPress persistence, S3
original storage and S3 formal-history confirmation have all succeeded. The
original is a frozen value copy of the successful operation payload, not a later
collection of the displayed comment. Resume uses that same frozen payload.

`edit_comment` provides the exact array passed to the core DB update, with its
generated comment ID attached by this adapter. Insert uses the `wp_insert_comment`
result object; status changes use the object passed to `transition_comment_status`
following `wp_set_comment_status`. Deletion uses the deleted object. The adapter
does not call `get_comment(id)` to obtain an original. It copies core fields at
the earliest hook priority before storage. Edit-triggered status callbacks do
not create a duplicate record.

Core insert/status code itself reads its persisted result before handing it to
these hooks. Thus this is **not** a pre-write interception or a claim of atomic
dual writes from raw submitted text. The premise remains normally operating
WordPress/core callbacks; sanitization and moderation are part of the confirmed
operation. Hostile core hooks or DB modifications before that snapshot are not
proven absent. This is distinct from the S3-first article body path. Failed S3 writes
do not roll back the comment or enter formal history. A local pending queue
allows Resume history on the surviving source; it is not a recovery dependency.
History confirmation retries the same record/key. Pending comment history blocks
protected article saves and initial capture until resumed, preserving the shared
confirmation sequence. If the server disappears first, ignore unconfirmed
operations and recover the previous confirmed state, including its old comment
status. Prepared objects alone are never adopted.

Restore complete site reads the existing site baseline and S3 history only.
Core comment fields, body, approval state, article identity, reply parent and
approved comment count are replayed. Deletion is a tombstone; children inherit
the deleted comment's parent as in WordPress. Recovery does not send comment
notification mail. Destination users retain their existing identity mapping.
The individual text/attribute recovery path rejects comment selection.

## Limits

- Arbitrary plugin comment metadata and custom comment types/states, direct SQL
  edits, external comment services and email delivery are not covered.
- Core JSON includes author email and IP like a WordPress comment record; use
  the existing private S3 scope and retention policy. Deleting a WordPress comment
  does not erase its older retained S3 versions.
- Capture is synchronous. Large bulk operations and simultaneous edits to the
  same comment have not been load/concurrency validated. No atomic commit across
  the WordPress mutation and S3 is claimed. Process death before the pending
  queue is recorded can lose that final operation.
- The 5 MiB original limit applies. Comment history is supplementary to a valid
  site baseline; it cannot reconstruct a missing parent article by itself.
- Scheduled execution and formal release remain deferred. Installation/update package validation is recorded alongside the candidate ZIP.

## Acceptance — 2026-10-24

Existing source wp.ceri.link, read-only recovery dm/wp-backup.ceri.link and the
existing isolated M1 prefix were reused. Only new test comments on trial post149
were changed; no article body, original comment, IAM, scheduling or baseline
was edited. The source used normal WordPress core APIs, not browser form
submission, to exercise the same successful hooks.

| Formal order | Operation | Recovery evidence |
|---|---|---|
| 27 | New pending comment3 | Restored; preserved pre-next-restore content confirms pending body/state |
| 28–30 | Edit, approve, reply4 | Body, status, article, reply parent and count match |
| 31 | Trash parent3 | Trash status and count match |
| 32–33 | Untrash then permanently delete parent3 | Parent absent, reply4 retained/reparented, count1 |

Every actual restore used the existing through2 S3 baseline plus its formal
tail, no source DB. Chrome confirmed the final reply in the destination's normal
Comments screen. Isolated WordPress with a memory S3 transport additionally
passed hold/spam/unspam and original/history-write failures plus resume (12
formal operations). Those injected failures are not claimed as real AWS outages.
Offline JSON replay and independent asset-snapshot tests also pass.

The first real restore process exited1 without diagnostics; its result was not
counted as success. Target remained unchanged on inspection. A diagnostic wrapper
and deliberate restore retry succeeded, as did subsequent restores; the first
exit's cause remains undetermined. It is separate from the product assertions.

The first preservation check compared raw postmeta row IDs and rendered Markdown
caches and therefore failed after site restoration. Inspection found only
regenerable `_ozmd_rendered_html` / `_ozmd_render_hash` removals and meta row ID
allocation changes. The corrected check compares original pre-test source and
attributes, excludes only those two caches and row IDs, and passes; it did not
reset the baseline. Posts, Markdown source, other metadata, taxonomy, settings,
Cron and preexisting comments remained unchanged.

## 日本語要約

2026-10-24訂正：WordPress保存・S3原本保存・正式履歴の確定の三つが揃って
復旧可能な操作として成立します。原本は成功操作の引数から直ちにコピーし、
再開時にも同じ値を使用します。Resilience自身がIDからDBを読み直して原本を
作る経路は廃止しました。編集はDB更新に使った配列、新規・状態変更は
WordPress本体が読み出して渡す保存結果、削除は削除対象のオブジェクトです。
標準処理での同一性を検証しますが、「生の投稿入力を直接二重書込み」や
本体内部の保存結果読取り前にも改変がないことを証明するものではありません。

コメントの追加・編集・承認待ち／承認／スパム／ゴミ箱・完全削除を、完全JSONと
S3正式履歴へ記録します。返信の親子関係・コメント数もサイト全体復旧で再現します。
実S3では追加・編集・承認・返信・ゴミ箱・完全削除、隔離試験ではスパムと保存失敗／
再開を確認しました。ブラウザでは復旧結果の閲覧を確認し、操作発生は標準PHP APIです。

本文とは異なり、コメントはWordPressで成功した直後の保存です。S3失敗時には
未確定を表示し「Resume history」で再開します。元サーバ喪失前に正式履歴へ
確定しなかった変更は採用せず、前の確定状態へ戻ります。個別文書復旧ではなく
サイト全体復旧を使用します。第三者プラグイン独自のコメント情報は保証対象外です。
定期実行・正式公開は未実施です。
