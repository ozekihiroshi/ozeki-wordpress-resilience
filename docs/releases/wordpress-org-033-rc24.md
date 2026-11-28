# Ozeki Resilience 0.3.3 rc.24 — 2026-11-28

New GitHub review candidate. NOT submitted to WordPress.org, NOT deployed to production, NOT approved. rc.23 remains submitted and deployed; awaiting reviewer response. Supplementary submission text and email reply are drafts only.

新しいGitHub候補です。WordPress.org未提出・本番未導入・公開未承認。提出済み・本番稼働中はrc.23で、審査担当者の回答待ちです。補足説明・返信文は未送信の案です。

## Artifact / 成果物

- Source: `2d608addf04355d988cf16adcf83e69399b5cd40`
- Tag: `wporg-0.3.3-rc.24`; internal version: `0.3.3`
- ZIP: `ozeki-resilience-0.3.3.zip`; 8,338,659 bytes; 3,823 files
- SHA-256: `e5c808e2c51ebcdf1e33f8bef3f7438fb1625747e94c8bc9b928cf877e9cc3dc`
- [Release and matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.24)

## Changes / 修正

Supported TablePress, Markdown and CF7 embed syntax remains usable. Markdown revisions retain source associated with the correct document, recovered documents refresh derived hash/cache after revision restore, and safe .md export filenames are restored. CF7 Flamingo mappings accept only declared existing form fields. ACF instructions are restored with HTML presentation safety limited to that field. No third-party software installation or initialization is added.

TablePress等の埋込み、Markdown過去版と元ファイル名、CF7の宣言済み項目のFlamingo連携、ACF説明文を修正。HTML安全処理は表示項目に限定します。原本・履歴の形式、依存ライブラリ、事前セットアップの原則は変更しません。

Normal rc.23 → rc.24 update preserves protection and needs no new initial save solely for the update. Prepare the updated reader on the recovery destination. A previously incomplete recovery that was re-saved requires an earlier original containing the missing information; updating cannot recreate it.

rc.23からの正常な更新だけを理由とした初回保存のやり直しは不要です。復旧先も更新します。欠けた状態で再保存済みの情報は、情報が残る元の復旧点から戻します。

## Exact ZIP validation / ZIP自体の確認

Disposable internal-only Docker on dm: WordPress 7.1.5, PHP 8.3, MariaDB 10.11. Synthetic data; external HTTP, WP Cron and automatic updates disabled; no S3 use in packaging checks.

- Fresh install/activation and rc.23 replacement update passed. All 3,823 installed files match the ZIP in both cases.
- Update retained the exact comparison hash of configuration including protection, initial-save readiness, pending records, active plugins and posts. No unexpected interruption marker.
- Plugin Check 2.2.0: exit 0, errors 0, warnings 134. Categories/counts unchanged from rc.23: direct queries 47, uncached 43, meta_value 23, meta_key 18, error_log 2, Japanese Markdown filename 1. These warnings are not claimed resolved; zero errors is not review approval.
- Five existing checks passed: basic-settings, navigation-state, reference-settings, core-update-contract, attachment-deletion-state.
- Dependency files unchanged; no files removed. Eight maintained user guides, 86 valid relative links; development/test scripts excluded.
- Test containers/volumes/network removed successfully. Initial invocation lacked Docker permission and created no containers; the same built ZIP passed the privileged retry.

新規導入・rc.23更新とも成功。設定・保護状態・未完了保存・記事を維持し、全配置ファイルをZIPと照合。Plugin Checkはエラー0・警告134（rc.23と同分類・同件数）。同梱文書リンクと開発資料除外も確認しました。

[Machine results](wordpress-org-033-rc24/result.json) / [Package audit](wordpress-org-033-rc24/package-audit.json) / [Plugin Check](wordpress-org-033-rc24/plugin-check.txt).

## Recovery evidence and limits / 復旧確認の根拠と範囲

The packaged runtime is the same reviewed runtime in the [real-S3 record](../review/recovery-fields-s3-20261128.md); subsequent source changes are documentation only. Two synthetic round trips covered use, resaving and second recovery, with all 316 written fixed versions read back identically. Markdown Documents was 0.1.2, not 0.1.3. This packaging check does not rerun the full community dataset, all browser operations, external email delivery or protected daily-history commits. Source-site Markdown 0.1.2 revision hash observations remain separately recorded; they are not represented as resolved by this release.

実S3往復の製品実装と今回ZIPの実装は同一です。その後の変更は文書のみ。既存の確認範囲を超えて、本番全件や全ブラウザ操作・実メール配送まで確認済みとはしていません。

Private staging and Markdown-original clarification questions from rc.23 remain with the reviewer; no WP_CONTENT_DIR fallback was added. [Additional information draft](wordpress-org-033-rc24/additional-information.txt) / [Reply draft](wordpress-org-033-rc24/review-reply.txt).

## Preservation / 保全

No production operation, original/history rewrite, WordPress.org upload or review email. Existing ZIPs/tags retained. Submitted rc.23 SHA-256 remains `062a8c423c4ecca40b0075dc65d4d783e27ed884024fc66c5933f341e7de5447`.
