# Editor save corrections — final 0.3.1 ZIP acceptance

Date: 2026-10-25. Candidate: [ozeki-wordpress-resilience-0.3.1-editor-save-final.zip](../../release-candidates/20261025-editor-save/ozeki-wordpress-resilience-0.3.1-editor-save-final.zip).

SHA-256: `901950f74d02d40bb4c21f92cecb6f7a80d30192f211a84191857f4e2bd3e5d2`.
Size: 7,385,571 bytes; 3,813 files. Vendor bytes are unchanged from the validated save-status-final ZIP. Product sources and packaged documentation match the build inputs; no test injector is bundled.

## Product changes

- A structured `owr_save_failed` error lets the standard block editor show the failure reason.
- Standard Save can submit a REST body request and a second legacy meta-box request. Only a secondary body matching confirmed S3 content and captured attributes is omitted.
- Identical confirmed native detail state, including referenced media bytes, is omitted. Changed state remains recorded. Equality-read failure falls through to the durable pending queue, never silent loss.
- This is not generic request idempotency, universal adapter deduplication or multi-writer support.

Earlier browser acceptance used existing trial article37: original-PUT interruption retained the old body and history67, displayed the concrete reason, and retained the editor input. Removing that test-only interruption and clicking Save once produced one changed-body record68, S3 body equality, no pending history and no error notice. Existing post/meta/user/member/settings hashes matched. This was controlled transmission interruption, not a real AWS outage. The exact ZIP acceptance below does not repeat that browser simulation.

## Fresh installation and update

The existing dm Docker/core/DB were reused with unused isolated `owreszip_20261025_fresh_` and `owreszip_20261025_upgrade_` namespaces and content directories. No infrastructure or credential helper was added. Fresh install used this ZIP; update overwrote the validated save-status-final 0.3.1 installation with this ZIP. This was extraction/activation and file-overwrite acceptance, not browser Plugin_Upgrader acceptance.

Both installations passed preservation checks for configuration, article content/identity, comments, CF7 definitions, Flamingo receipts, WP-Members credentials/fields/settings, TablePress IDs/cells/settings, four synthetic frozen pending operations and their error, and prior recovery-result/attempt data. The complete admin page rendered existing save-status and recovery-result displays without resuming the synthetic queue or restoring site content.

S3 was read-only through the standard AWS SDK EC2 role. All 68 formal-history records matched before and after, SHA-256 `625997c285d433808a1099677945641434ca27397be4ff9b04b6b8816e45f81c`.

All 3,813 installed files matched the ZIP bytes in both installations. Extracted-product tests passed for article equality/error reasons, native queue failure/resume including unknown equality reads, save-status boundaries and recovery-result displays; PHP lint passed. Existing running-site before/after probes matched; mail counters were zero, WP-Cron execution disabled. Existing scheduler definitions were preserved; core first-boot maintenance registrations were not counted as executions.

## Separate classifications and remaining work

**Product:** duplicate secondary saves and generic editor error messages are corrected within the scope above.

**Flamingo standard behavior:** `profile_update` calls its contact-add routine, which updates contact dates. WordPress editor preferences use the user-update endpoint. This explains a possible route for the earlier contact-date change; that individual historical request was not traced. No Flamingo hook or membership-approval policy was altered. Article-only follow-up preserved existing contact records.

**Environment:** the existing live probe emits a duplicate `DISABLE_WP_CRON` definition warning. The setting remains disabled and before/after probe output is identical; this is separate from product corrections. No new test-harness defect occurred during this ZIP acceptance.

No existing member/content edits, S3 writes/deletes, email, periodic execution, live deployment or formal release were performed. New trial records were limited to the isolated installation fixtures. Remote CI for this uncommitted candidate has not run. Earlier frozen ZIPs remain unchanged.

## 日本語要約

標準編集画面での具体的な失敗理由表示と、S3確定状態が同じ場合の追加設定要求・付随情報の重複抑止を収録しました。新規導入と前回の検証済みZIPからの更新は合格し、設定・履歴・試験記事・コメント・フォーム・会員・表・保留操作・復旧結果が保持されました。S3正式履歴68件は読取り照合のみで不変、全3,813ファイルがZIPと一致しています。

Flamingoのプロフィール更新に伴う日時更新は標準動作として区別し、製品側で無効化していません。前回の個別要求の因果関係は断定していません。既存環境のCron重複定義警告も製品修正とは別です。メール送信・定期実行・正式公開は行っていません。

Local evidence: `release-readiness/editor-save-final-20261025/` contains build manifest, installation/preservation results, extracted-product contracts, byte checks and before/after live probes. Browser evidence is separately recorded in `release-readiness/editor-diagnostics-20261025/`.
