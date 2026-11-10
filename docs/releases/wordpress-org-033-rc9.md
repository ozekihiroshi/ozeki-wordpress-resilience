# WordPress.org 0.3.3 rc.9 — November 10 review response

**Submitted November 11, 2026 (JST): update accepted and review-email reply sent. Awaiting the reviewer response; publication is NOT approved.** The reviewer requested changes to rc.8 on November 10. All submitted ZIPs/tags remain preserved.

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

## Submission and reply / 更新受付と返信

2026年11月11日（日本時間）、既存申請へrc.9をアップロードし、画面の「New version of Ozeki Resilience uploaded for review.」を確認しました。07:53の自動受付メールでもrc.9の補足説明とファイル受領を確認しています。元の11月10日審査メールへ返信し、Gmailの送信完了を確認しました。現在は審査担当者の回答待ちであり、公開承認済みではありません。

The upload page lists November 10, 2026 (site date); the receipt email is November 11 at 07:53 JST. The site still displayed “Being Reviewed — waiting on action from you” immediately after upload. The waiting-for-reviewer description records our completed upload/reply, not an observed approval or a claim that the portal label changed.

Before submission, related request paths were reviewed again: shared administrator capability/nonce checks, partial editor submissions, malformed recovery references/numbers and GFS input, and archival originals versus escaped display. No additional submission blocker was identified in that bounded review. This is not a new end-to-end test of every integration or content format.

GitHub Actions PHP 8.1 and 8.3 passed: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/actions/runs/42917044052

When recording submission acceptance, only current documentation and release notes were updated. The rc.9 source tag and ZIP remain immutable; the ZIP retains the pre-submission status wording present when built. Current status is recorded here and in the main-branch READMEs.

## Sent reply to plugins@wordpress.org

Thank you for the additional review. I have uploaded 0.3.3 rc.9 to the existing ozeki-resilience application and confirmed its acceptance.

The reported nonce/input issues and related request paths have been reviewed and corrected. Plugin Check 2.1.0 reports 0 errors and 99 documented warnings; isolated clean installation, updates, real-S3 save/recovery, and PHP 8.1/8.3 CI checks passed.

One clarification: Markdown originals are authenticated, strictly validated archival text, retained without stripping their contents; they are not executed or directly emitted as HTML. Recovery restores supported information assets, not archived theme/plugin code. Administrators install trusted software separately.

Source, exact ZIP and validation: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.9
ZIP SHA-256: be152094f4c67affba938fc19e202d1ee61dba9179a5c4c313c12c7715ed5d69

Regards,
Hiroshi Ozeki
## Post-submission integration corrections — 2026-11-11 (not in rc.9)

These source changes were reviewed on `codex/wordpress-org-rc9-input-review` and merged into main for rc.10. The merge itself was not a submission or approval; rc.10 was subsequently submitted as recorded below. The submitted ZIP and tag above are unchanged.

- ACF: preserve mismatched field values in originals/history, but withhold the value and field-key reference from application, with an explicit not-applied reason. Other valid fields and articles continue to recover. No archive schema or stored original is rewritten.
- WP-Members: treat `db_version` as a dotted version identifier, retaining supported legacy numeric representations without conversion. Accept the plugin's integer page IDs as well as textual page/URL references. Arrays and invalid types remain rejected.
- Added regression cases for ACF value types, raw-metadata bypass prevention, version representations and page references. ACF, application rules and membership replay checks passed on PHP 8.3.36.
- Actual recovery on a separate WordPress database prefix restored the original real-S3 history through sequence 22: 8 content posts, 2 contact forms, 1 inquiry receipt, 1 table and the subscriber account. Member password hash was preserved; roles remained subscriber; session tokens were absent. The ACF array in a text field was withheld with its reason. All 22 formal-history records and their original-content SHA-256 hashes matched before and after recovery.
- Earlier ACF-only recovery separately verified a valid Japanese text field alongside the withheld invalid field. The combined run uses the older unchanged history, which does not contain that added test field.
- Environment: WordPress 7.1.3, PHP 8.3.36, CF7 6.2.3, Flamingo 2.6.4, TablePress 3.4.1, WP-Members 3.5.8.1, ACF free 6.8.10. External mail and scheduled jobs were disabled in the isolated fixtures. Existing sites and research working changes were not modified.
- TablePress: malformed row data with valid editor authorization can fail inside TablePress 3.4.1 before saving. No DB/history change was observed. Keep the upstream reproduction for reporting and verify an upstream fix separately; do not patch bundled third-party code or treat this failure as a completed save. No upstream report has been sent.

日本語要約: ACFの不適合値は原本に残したまま理由付きで未適用にし、他の復旧を継続します。WP-Membersの版情報とページIDの型を実際の保存内容に合わせました。元の正式履歴22件から会員・問い合わせ・表・記事を隔離環境へ復旧し、原本・履歴のハッシュ不変も確認しました。提出済みrc.9にはこの修正を加えていません。この確認時点では新しいZIPの作成・申請更新は未実施でした。その後のrc.10の作成・提出結果は以下に記録しています。

## rc.10 follow-up candidate — submitted

The installation/update check additionally found that restoring only recognized WP-Members settings left out operational defaults required on the next request. Recovery now obtains defaults from the trusted installed WP-Members version and overlays only recognized archived settings. Unknown archive settings remain unapplied. The same original history was restored again, followed by a separate WordPress bootstrap and management-screen render; these passed. This supersedes the earlier process-completion-only check.

- Candidate: **0.3.3 rc.10**, [release and ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.10), **submitted to WordPress.org on November 11, 2026 (JST)**. The update was accepted and the original review-email reply was sent; awaiting the reviewer response, not approved.
- ZIP: 8,283,977 bytes, 3,813 files; SHA-256 `a762c181772ded58ac403ad520a731278c4c73ed91181d3326bd1cab6420acbf`.
- [Package audit](../../evidence-public/wordpress-org-033-rc10/package-audit.json): all product source hashes match; vendor unchanged; 8 maintained bundled guides, 78 valid relative links, no development artifacts.
- Exact-ZIP fresh installation/activation and rc.9 → rc.10 update passed in isolated WordPress. Configuration, pending-state/result hashes, content count and activation remained identical across the update. Queues were empty; this does not establish an update with queued work.
- Exact-ZIP recovery through the existing history sequence 22 passed with members, inquiries, table and articles, then a new process successfully bootstrapped and rendered the admin screen. S3 original/history hashes remained unchanged. These were real WordPress CLI/API checks, not a new browser timeout test.
- Plugin Check 2.1.0: **0 errors, 99 warnings**, same categories as rc.9. [Results](../../evidence-public/wordpress-org-033-rc10/plugin-check.json).
- ACF, application-rule and member replay regression checks passed against code installed from the exact ZIP.
- Existing submitted ZIPs/tags, original/history formats and research working changes are preserved. The rc.10 upload and original review-email reply are complete; see the receipt below.

日本語: 版情報・ページIDの修正に加え、復旧後の起動に必要なWP-Members標準設定を信頼済み導入版から補う修正も含めました。最終ZIPで新規導入・更新・会員連携を含む復旧と次のリクエストまで確認済みです。rc.10は更新受付・元の審査メールへの返信が完了し、審査担当者の回答待ちです。公開承認済みではありません。

## rc.10 submission receipt — November 11, 2026 (JST)

- The existing ozeki-resilience application accepted the rc.10 ZIP. The page displayed **“New version of Ozeki Resilience uploaded for review.”** and listed the rc.10 comment and SHA-256 above. WordPress.org displays the upload date as November 10, 2026 (UTC).
- A reply was sent to the original November 10 review email at plugins@wordpress.org, under **“Re: [WordPress Plugin Directory] Review in Progress: Ozeki Resilience”**. Gmail displayed **“メッセージを送信しました”**.
- The reply identifies rc.10, confirms the retained nonce/input-validation fixes and follow-up ACF/WP-Members recovery checks, and links the matching source and validation.
- **Awaiting the reviewer response. Publication is not approved.** The application displays **“Being Reviewed — We've got your email. This plugin is currently waiting on action from our plugins team.”**
- Submitted ZIPs and tags, including rc.9 and rc.10, remain unchanged. This record update changes documentation only; it does not rebuild the submitted ZIP.

日本語: rc.10の更新受付と元の審査メールへの返信送信を確認しました。現在は審査担当者の回答待ちで、公開承認済みではありません。提出済みZIP・タグは変更していません。
