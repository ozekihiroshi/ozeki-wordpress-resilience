# WordPress.org 0.3.3 rc.9 — November 10 review response

**Prepared November 11, 2026; NOT submitted to WordPress.org. No review-email reply has been sent for rc.9. Publication is not approved.** The reviewer requested changes to submitted rc.8 on November 10. Its ZIP/tag and earlier artifacts remain preserved.

## 今回の修正 / Changes

- Markdown本文が送られた保存では、nonceが欠落・不正なら保存前に拒否します。nonceだけ・本文が配列などの不完全な送信も拒否し、保存済み原本への切替で処理を続行しません。利用者の編集権限確認は別途維持します。
- 復旧ポイント、復旧終了番号、個別復旧番号、定期保持設定を入力受付時にサニタイズし、型・形式・範囲を確認します。不正な保持設定は既存設定を置き換えません。
- 通常の記事保存や本文を送らない操作、独立したMarkdown原本、保存形式、復旧範囲は維持します。WordPress・テーマ・プラグインは信頼できる配布元から別途準備する方針も変わりません。

The Markdown editor path is now detected from either submitted source or nonce, rather than requiring both before entering nonce validation. Missing/non-string/invalid nonces and missing/non-string source fail before lock acquisition or S3 work. The independent capability check remains. Non-editor saves use previously stored source and do not consume an unverified POST original.

Recovery references and end numbers are sanitized at the form boundary and then checked against the existing exact schema, numeric syntax and integer bounds. GFS leaves are sanitized recursively; malformed rows/nested values are rejected before persistence. Individual recovery selections now require an array of positive integer strings. The shared administrative action still requires both `manage_options` and `check_admin_referer()`.

All product POST/GET/REQUEST occurrences were reviewed, including configuration, cleanup confirmations, recovery selections, the core meta-box selector and startup routing. Two narrowly scoped PHPCS explanations document intentional behavior: Markdown originals are bounded UTF-8 text, not executable/rendered output; startup reads a sanitized action only to block unsafe requests, leaving login/logout validation to core. These are documented analysis exceptions, not added nonce bypasses. No global suppression was added.

## ZIP and corresponding source

- [Installable ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.9/ozeki-resilience-0.3.3.zip)
- [Corresponding source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.9/packages/markdown-m1)
- Header / stable version: **0.3.3**; candidate identifier: **rc.9**.
- **8,283,466 bytes; 3,813 files**.
- SHA-256: `be152094f4c67affba938fc19e202d1ee61dba9179a5c4c313c12c7715ed5d69`.
- [Package audit](../../evidence-public/wordpress-org-033-rc9/package-audit.json): product files match source, 78 bundled relative links resolve, eight maintained guides, no development scripts/tests. Vendor dependencies are unchanged from rc.8. ZIP differences are the two READMEs, readme.txt, Plugin.php, GfsPolicy.php and the explanatory comment in Startup.php.
- Submitted rc.8 SHA-256 remains `1f826c27aebb28e81b726ac71f0c58a4d5f8400afe09a4d33a3c68b80c79118b`.

## 確認結果 / Verification

- Fresh isolated WordPress 7.1.3 / PHP 8.3.36 with WP_DEBUG enabled: standard ZIP installation and activation; 3,813 installed files match; administration screen renders.
- Existing isolated community/dm sites: standard rc.8 → rc.9 update preserves configuration, pending-state hashes, previous result records and activation. Pending queues were empty; this does not claim an upgrade with queued work.
- Actual admin-action handlers in isolated WordPress: 24 malformed recovery input cases rejected without changing posts; malformed GFS retains the prior settings; missing/wrong admin nonce and unauthorized user rejected.
- Actual WordPress save hooks with real S3: Markdown creation/update preserves Japanese text and code examples; native article creation/update confirms successfully. Six incomplete/invalid editor submissions leave the document and confirmed history unchanged. Baseline and Checkpoint form operations succeed.
- Real-S3 recovery on dm: successful recovery through history number 8, with 266 post records reported. The two newly saved native/Markdown assets match the source digest `a094acd84a1c30d2e5456742e1006c2bcb96ea8d714ac1c24475f5e5dbf1a5ec`; no pending history remains. Existing files already matched, so this run reports zero file replacements.
- These checks invoke real WordPress APIs/hooks and admin-action handlers from PHP CLI; they do not constitute a new browser timeout/interaction test. Earlier browser evidence is retained separately.
- All existing independent M1 package contract commands plus the new editor-nonce contract pass on PHP 8.3. Test fixtures supply standard WordPress sanitization helpers where the product now uses them.
- Plugin Check **2.1.0: 0 errors / 99 warnings** on the exact candidate ZIP. No input-sanitization or nonce warnings remain. The remaining categories are direct database access (34), no caching (32), meta queries (30), diagnostic error logging (2), and Japanese root README (1). These remain documented warnings, not approval.

See [sanitized verification summary](../../evidence-public/wordpress-org-033-rc9/validation.json) and [Plugin Check results](../../evidence-public/wordpress-org-033-rc9/plugin-check.json). Production sites were not used; the existing dedicated S3 test prefix and isolated database tables were reused. No saved S3 assets were deleted or reformatted.

## Reply draft — NOT SENT

Thank you for the additional review. I have uploaded 0.3.3 rc.9 with the requested input and nonce corrections.

Submitting a Markdown original now requires a valid nonce; missing or malformed editor fields are rejected before saving. Recovery and schedule form values are sanitized and validated before use. Markdown originals remain validated archival text so their content is preserved; they are not executed or directly emitted as HTML.

The exact ZIP passed Plugin Check 2.1.0 (0 errors, 99 documented warnings), isolated installation/update checks, and real-S3 save/recovery checks. Source and validation: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.9

ZIP SHA-256: be152094f4c67affba938fc19e202d1ee61dba9179a5c4c313c12c7715ed5d69

Regards,
Hiroshi Ozeki

The draft above is for use only after the rc.9 upload is authorized and its acceptance confirmed.
