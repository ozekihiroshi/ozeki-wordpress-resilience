# Contact Form 7 / Flamingo recovery

This adapter protects completed Contact Form 7 definition saves and Flamingo
inbound messages created through Contact Form 7's submission integration. Tested
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

- Form creation/update and initial CF7-to-Flamingo receipt capture are covered.
  Later Flamingo edits, spam/trash/deletion, address-book entries and form deletion
  are not incrementally captured in this first adapter.
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
今回はフォーム作成・更新と受信時の保存に限定し、添付ファイル本体、アドレス帳、
受信後の編集・削除・スパム移動、フォーム削除の継続記録は対象外です。
定期実行と正式公開は行いません。
