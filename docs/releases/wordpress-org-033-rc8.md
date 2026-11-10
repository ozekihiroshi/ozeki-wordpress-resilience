# WordPress.org 0.3.3 rc.8 — purpose and recovery principles

> 2026年11月10日に追加審査が届きました。現在は指摘修正済みの[rc.9候補](wordpress-org-033-rc9.md)を準備しています（未提出・公開未承認）。The reviewer requested changes to rc.8; rc.9 is the unsubmitted response candidate. The submission/reply chronology below is retained.

**Submitted to the existing WordPress.org application on November 2, 2026 (JST); upload accepted and reply in the original review-email thread sent. We are awaiting the reviewer’s response; publication is not approved.** Earlier submissions, including rc.6, and all existing ZIPs/tags are preserved.

## 更新受付・返信記録 / Submission and reply

- 2026年11月2日（日本時間）、既存申請（ozeki-resilience）へのrc.8アップロード受付を確認。WordPress.orgは「New version of Ozeki Resilience uploaded for review.」と表示し、同日04:21に更新受付メールも届きました。
- 同日12:04、元の追加審査メールへrc.8への更新を返信し、Gmailの送信完了表示と送信済みメールを確認しました。宛先はWordPress Plugins Team（plugins@wordpress.org）です。
- 公開承認済みではありません。審査担当者の回答待ちです。rc.6の過去の提出記録は保全しています。
- The rc.8 upload was accepted; its automated receipt arrived at 04:21 JST on November 2. At 12:04 JST we replied to the original additional-review email, confirming the update, information-assets-only recovery principles and bounded validation results. Gmail confirmed sending. This is not approval or a reviewer response.
- The submitted ZIP and tag remain immutable. Their bundled status text records preparation time; current status is maintained here and in the main-branch distribution-status page. Main now differs from the tag in standalone test fixtures and submission-status documents only.

## 説明の整合確認 / Consistency review

Reviewed the Japanese/English README, bundled readme.txt and setup/recovery guides against the rc.8 submission explanation and existing validation record. The scope remains supported information assets, separately prepared trusted software, recognized settings and optional integrations (ACF free only). No new runtime behavior or expanded guarantee was added. Plugin Check remains 0 errors / 107 recorded warnings; real-S3 functional checks apply to the identical rc.7 runtime. Corrected stale rc.8-not-submitted / rc.6-current-status text; older records are identified as historical. ZIP SHA-256 and existing tags remain unchanged.

## Explanation changes / 説明の修正

WordPress.org用の **readme.txt**、日英README、日英導入・復旧ガイドに今回の説明を反映しました。

- 必要性：元のサイトを信頼できなくなっても、情報を取り戻して活動を再開する備え。
- 原則：情報を独立した原本として保全し、実行ソフトウェアは信頼できる配布元から別途準備する。旧テーマ・プラグインのコードを配置・実行せず、設定は認識された項目だけ適用する。
- 目的：容量や復元時間の最小化より、原本と復旧ポイントによる冗長性、予備、余裕を重視する。
- 連携：標準の記事・固定ページは追加プラグイン不要。連携固有の情報には対応版を別途用意する。

The WordPress readme now explains why the plugin exists before describing its mechanics. The same principles are stated in the Japanese/English README and guides. Redundant explanations were consolidated, and the source link now points to the current main branch. These changes do not add runtime behavior or stronger recovery guarantees.

## Artifact and verification

- [Installable ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.8/ozeki-resilience-0.3.3.zip)
- [Matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.8)
- Candidate **0.3.3 rc.8**; plugin header/stable tag **0.3.3**.
- **8,283,015 bytes / 3,813 files**.
- SHA-256: `1f826c27aebb28e81b726ac71f0c58a4d5f8400afe09a4d33a3c68b80c79118b`
- [Package audit](../../evidence-public/wordpress-org-033-rc8/package-audit.json): all **3,796 runtime files match rc.7**. Only five files differ: readme.txt, README.md, RAADME-jp.md and the two user guides. Product files match corresponding source; all 78 bundled relative links resolve; eight maintained guides; no development scripts/tests/tools.
- [Installation verification](../../evidence-public/wordpress-org-033-rc8/validation.json): installed the exact ZIP over rc.7 with the standard WordPress upgrader via WP-CLI in the existing unconfigured, isolated community package-check site. Activation remained enabled, all 3,813 installed files matched, and the administration screen rendered. WordPress 7.1.3 / PHP 8.3.36.
- [Plugin Check 2.1.0](../../evidence-public/wordpress-org-033-rc8/plugin-check.json): **0 errors / 107 warnings**, unchanged in count from rc.7. Warnings remain documented; this is not approval or a warning-free claim.
- Functional validation remains the [rc.7 evidence](wordpress-org-033-rc7.md) and [real-S3/browser checks](recovery-usability-20261101.md). Those tests were not repeated for this documentation-only package; identical runtime files were verified instead.

rc.6 SHA-256 remains `e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3`; rc.7 remains `b8e2d8d8961463da42f223990461f29ff7a3546212f459983ec1ebec0d307b58`.

## CI fixture correction after packaging

The main-branch Actions run exposed a missing `determine_locale()` stub in standalone recovery-result tests, introduced when the UI began rendering next-action text. WordPress supplies this function in the installed plugin environment. The test fixtures now supply the locale, and assert English/Japanese interruption guidance without weakening the existing result checks. The full independent M1 package contract step passed locally on PHP 8.3 after correction. [Latest main-branch CI results](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/actions/workflows/contracts.yml?query=branch%3Amain) include the PHP 8.1/8.3 jobs and remaining repository checks.

This correction changes tests only, not packaged runtime or documents. The rc.8 tag/ZIP remain unchanged; the corrected standalone tests are on main. Historical failed runs remain visible. Plugin Check and ZIP validation above are separate from Actions results.

## Purpose and validation summary accompanying the submission

Ozeki Resilience provides a recovery path when the original WordPress environment can no longer be trusted. Alongside existing backups, it preserves supported information as independent originals so publishing and service can resume on a fresh WordPress.

This purpose leads to three principles: preserve independent information assets; install executable software separately from trusted distributors; apply recognized content/settings rules instead of blindly importing the old environment. Recovery does not deploy or execute archived theme/plugin code. Standard Posts and Pages need no additional plugin; integration-specific content requires the compatible plugin separately. Originals and recovery points deliberately provide reserves, rather than minimizing storage or restoration time.

0.3.3 rc.8 incorporates these explanations into readme.txt and the bundled guides. Its runtime is identical to rc.7, which adds recovery-destination write/delete guards, recorded software requirements and Japanese/English failure and interruption guidance. The exact rc.8 ZIP passed installation/file-integrity checks and Plugin Check 2.1.0 (0 errors, 107 recorded warnings). Existing real-S3 and browser recovery evidence is linked above. Stored data formats are unchanged.

ZIP SHA-256: 1f826c27aebb28e81b726ac71f0c58a4d5f8400afe09a4d33a3c68b80c79118b.
