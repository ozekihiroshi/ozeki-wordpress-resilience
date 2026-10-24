# Contact Form 7 / Flamingo recovery

This adapter protects completed Contact Form 7 definition saves/deletion and Flamingo
inbound messages, including subsequent changes and deletion. Tested
versions: Contact Form 7 6.2.3 and Flamingo 2.6.4; these are optional dependencies
for this feature, not requirements for ordinary article/comment protection.

## Storage and recovery contract

At `wpcf7_after_save` and `wpcf7_after_flamingo`, copy the completed asset's post,
metadata and inbound-channel relationship into a complete `source.json`. A receipt
record includes its associated form definition, including the newly assigned channel.
This is a snapshot of the completed plugin save, not a pre-write input interception
or a proof against hostile plugins. No later DB lookup is used when resuming.

Reuse the existing successful-operation queue, S3 version/hash-pinned originals and
confirmation-ordered formal history. WordPress persistence, S3 original storage and
formal confirmation must all succeed to make a recoverable operation. A storage
failure leaves a frozen pending record; Resume history retries that same record.
No mail is sent by capture, resume or recovery. Pending records also block storage
configuration changes and protected article saving. The queue's historical option
name is `owr_m1_comment_pending`, now shared with forms; it is not a recovery source.
Loss of the source before confirmation omits that operation, as with comments.

Use **Restore complete site**, not individual text restore. S3 supplies the trusted
baseline and subsequent form/receipt records, including content, mail templates,
field values, stored submission status and channel relationships. Imported records
use direct content replacement; Contact Form 7 submission and email APIs are not
called. A new request loads the installed plugins. Install both recorded plugin
versions at the destination before recovery; missing/mismatched versions stop before
replacement. New trusted initial snapshots include active CF7/Flamingo code. Existing
older baselines can still use the post-baseline form history with installed dependencies.
The environment and SMTP/API credentials are not copied.

## Boundaries

- Form creation/update/deletion and Flamingo receipt edits, spam/ham, trash/restore
  and permanent deletion are covered. Address-book entries remain excluded.
- Uploaded attachment file bodies, external integrations and arbitrary third-party
  fields are not covered. Names recorded by Flamingo do not imply file recovery.
- Respect CF7/Flamingo do-not-store exclusions: data not retained by their integration
  is not rescued separately by Resilience. Do not store live secrets in form fields.
- Form settings can contain recipients and messages; receipts contain personal data.
  They use the same private S3 scope and retention controls as other originals.
- Storage confirmation and mail delivery are separate. CF7 may return `mail_sent`
  with `skip_mail: on`; that is not evidence of actual delivery. Recovery does not
  resend historical inquiries. No SMTP/OAuth configuration is reconstructed.
- Same-asset concurrency, process death before the pending record and arbitrary
  external hooks are not a distributed transaction guarantee.
- Existing text limits (5 MiB per operation), one writing WordPress per prefix and
  whole-site replacement constraints remain. Scheduling and formal release are deferred.

## 日本語

フォーム定義の通常保存と、CF7からFlamingoへ保存された受信記録を完全JSONとして
独立保存します。フォームとの関連・受信本文・連絡先・状態を正式履歴から復旧します。
本文のS3先行保存とは異なり、プラグイン保存完了時のスナップショットです。
未確定なら同じ保存内容で再開し、元サーバ喪失時は前の確定状態を使用します。

サイト全体復旧を使用し、復旧先には記録された版のCF7とFlamingoを導入してください。
メール送信APIは復旧で呼びません。受信履歴の保存成功とメール配送成功は別です。
フォーム作成・更新・削除と、受信後の編集・スパム／解除・ゴミ箱／復帰・完全削除を
記録します。添付ファイル本体とアドレス帳は対象外です。
定期実行と正式公開は行いません。

## Received-message lifecycle

Flamingo 2.6.4 writes its post before its metadata and supplies no dedicated
completed-update hook. Successful WordPress post/metadata callbacks therefore
mark only `flamingo_inbound` IDs for capture at the normal WordPress `shutdown`
hook. Capture freezes the final persisted post, metadata and channel state once
per ID per request. Multiple writes in one request coalesce; intermediate states
are not individual recovery versions. CF7's completed receipt hook clears its ID
from this deferred set, avoiding an extra initial-receipt record.

Permanent deletion uses `deleted_post` after core deletion succeeds. A complete
identity tombstone is stored in the same original/history format; replay removes
the post, metadata and its relationships, updates channel counts, and does not
resurrect it. CF7 form deletion leaves retained inquiries intact, just as the
source operation does. It does not edit pages containing the removed shortcode.
S3 history still retains older versions under the existing retention policy.

Failed storage keeps the frozen change/tombstone in the existing pending queue.
Retry does not look up the now-deleted post. Source loss before confirmation uses
the previous confirmed state. Process death before request-end capture, direct SQL,
concurrent requests modifying the same asset, external hooks writing after capture,
and external Akismet/email delivery effects are not covered. Replay imports records
without invoking mail or Akismet submission APIs. Ordinary plugin actions are not
prohibited by this scope.

受信後変更は標準フックで対象IDを追跡し、通常リクエスト終了時に完成した状態を1回保存
します。同じリクエスト内の中間状態はまとめます。完全削除は成功後の削除記録を保存し、
本文・メタ情報・関係を復旧先から除去します。フォーム削除で受信記録や記事本文を勝手に
削除しません。リクエスト終了前にプロセスを失った操作は未確定として扱います。

## Lifecycle acceptance — 2026-10-24

Existing trial inquiry and form only: edit, spam, ham, trash, restore from trash,
receipt deletion and form deletion produced real S3 history 42–48. Each stage
was reconstructed on the existing recovery WordPress from the same prior S3
baseline plus history; post fields, exact metadata and channel relationships
matched, and deletion removed post/meta/relations. Standard plugin PHP APIs and
normal request shutdown were used, not browser-click acceptance. Existing content
and configuration were preserved; mail calls were zero. The final trial form and
inquiry are intentionally deleted on both sites.

Isolated actual WordPress with memory transport additionally verified original
failure, tombstone-history failure, frozen retry and duplicate suppression.
These are injected failures, not actual AWS outages. Offline tests verify form
deletion does not cascade into inquiries. dm's OOM counter remained unchanged;
test comparison serialization and shell argument fixes were separate from product
changes. Periodic execution and formal release remain deferred.
