# Site-wide snapshot verification before confirmation

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

This change is in the development tree after PR #45. It is not included in the published v0.3.1-pre.1 ZIP.

Initial site snapshots and site-wide Checkpoints share `SiteSnapshot::save`. After writing their resources, that method now retrieves every resource using the returned VersionId and checks its SHA-256 through the existing `Store::get`. Only after all checks succeed does it write the manifest. It reuses the same Store and S3 client, without changing the storage format.

The check includes separated content and metadata, media, and any bundled software. A read failure or mismatch throws with the resource path and cause; no new manifest is written. The existing administration action records the error and does not replace the previous snapshot result with a new success. Already-written partial resources remain; no deletion, automatic retry or rollback is added. A later administrator-requested retry uses the existing immutable-write behavior and checks the resources again.

This establishes byte equality at verification time, not malware freedom or permanent availability. Previously confirmed manifests are not retroactively reverified by this change. The manifest itself retains the existing write semantics; this change concerns its referenced resources.

## Differential verification, 2026-10-25

- `site-checkpoint-verification.php`: 16 injected failures across initial common save and Checkpoint creation; content, metadata, image and software bytes; unavailable reads and SHA mismatches. Each stops before manifest PUT. Successful explicit retries retrieve every exact referenced version before the manifest and remain readable, with confirmed tail content intact. Existing objects remain unchanged.
- `site-checkpoint-admin-failure.php`: the actual administration action with WordPress functions and S3 replaced by in-memory fixtures records the cause, preserves the prior snapshot result and writes no manifest on verification failure.
- Existing separated-asset, Checkpoint, point-in-time and recovery-result contracts pass; changed product PHP passes syntax checking.

The tests above are local PHP fixture tests using the existing test framework. The subsequent actual AWS verification below is separate. No existing S3 resources, site content or published ZIP were changed.

## Actual S3 differential verification, 2026-10-25

The existing community `wp-rescue` container and isolated WordPress database/content namespace were reused. Current source files were staged separately, without replacing the shared site's plugin. AWS SDK standard EC2-role authentication was used, with no IAM changes or new infrastructure. Only a previously unused `checkpoint-verify-20261025-7c914b/` child of the existing M1 trial prefix received new objects.

| Case | Result |
| --- | --- |
| Initial capture through the actual administration action | All 29 resources (2,545,080 bytes) were retrieved using their exact saved versions before the manifest PUT; the resulting manifest was read back. |
| Site-wide Checkpoint through the same administration action | Baseline loaded from S3; all 29 resources of the new Checkpoint were retrieved using their saved versions before its manifest PUT; the resulting manifest was read back. |
| Initial capture verification failure | After a successful real fixed-version GET, the trial handler injected a read error. No manifest PUT was attempted; the error was recorded and rendered in the actual admin page HTML. No new success result replaced the previous result. |
| Checkpoint verification failure | After a successful real fixed-version GET of a newly saved resource, the trial handler changed only the response bytes. SHA mismatch stopped confirmation, with the same error-record/display behavior and no manifest PUT. |

Successful PUT/GET requests were forwarded to real S3, not replaced by in-memory storage. The failure injection did not damage the stored objects and is **not an actual AWS outage or stored corruption test**. The admin action and page renderer ran in WordPress via PHP; this was **not a browser interaction test**. Checkpoint-only creation was sufficient for this changed confirmation gate; history replay and full restoration were not repeated.

The current-object inventory (ETag, size, modification time) for every pre-existing object in the M1 trial parent remained unchanged in each case. Existing isolated content/member tables were unchanged. Test-only configuration and result/error options were restored. Existing retained resources were neither overwritten nor deleted; failed-attempt resources remain in the dedicated trial scope. No automatic recovery or cleanup was introduced.

Evidence: local `release-readiness/checkpoint-real-s3-20261025/` contains the one-shot script and four event/result JSON records. Do not rerun the one-shot script against its already-used prefix. Published ZIP SHA-256 remains `913bac85cb704f24edaaa76d793222d5b25676eef0ad87543b102c7d1933762f`.

## 日本語要約

初期スナップショットとサイト全体Checkpointの共通保存処理で、保存した全資源を固定Version IDから再取得し、SHA-256が一致した場合だけマニフェストを書き込みます。取得失敗・不一致では停止し、管理処理は原因を記録して前回の結果を保持します。部分保存された資源の削除、自動再開、巻戻しは追加しません。

ローカル模擬試験に加え、既存communityの隔離WordPressと実S3で、初期スナップショット・Checkpoint各29資源の固定版照合後にだけマニフェストが確定することを確認しました。失敗条件は実GET後の試験用エラー／応答改変で注入し、実AWS障害とは区別しています。実際の管理処理と画面HTMLのエラー表示を確認しましたが、ブラウザ操作試験ではありません。既存資産・コンテンツ・公開済みZIPは変更していません。

公開済みv0.3.1-pre.1には未収録で、過去のマニフェストへの遡及的な照合や無害性の保証を意味しません。
