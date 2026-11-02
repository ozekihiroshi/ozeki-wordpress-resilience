# WordPress.org 0.3.3 rc.6 — publication documentation


> 過去の記録 / Historical record. 現在はrc.8の更新受付・返信済みで、審査担当者の回答待ちです（公開未承認）。[Current rc.8 submission status](wordpress-org-033-rc8.md).

**Submitted and reply sent on October 28, 2026. Awaiting the reviewer’s response; WordPress.org publication is not approved.** rc.6 updates the existing application after the rc.3 review. All submitted ZIPs and tags remain unchanged.

## 更新受付・返信記録 / Submission and reply

- 2026年10月28日、既存申請（ozeki-resilience）へrc.6をアップロードし、「New version of Ozeki Resilience uploaded for review.」の受付表示を確認しました。提出ファイル欄にはrc.6の補足説明と下記SHA-256が表示されました。
- 同日の追加審査メール（21:04 JST）へ返信し、Gmailの「メッセージを送信しました」を確認しました。実行コードは別途準備する復旧方針、識別子の移行、配布物の整理、配置先の修正、確認結果を説明しています。
- 受付は公開承認ではありません。現在は審査担当者の回答待ちです。
- The upload was accepted and the reply was sent in the original additional-review email thread to plugins@wordpress.org. The WordPress.org screen still showed “Being Reviewed”; successful upload and email sending do not establish approval.
- This status-only documentation update was recorded on November 1, 2026. The ZIP and tag retain the documentation as it stood at submission; use this record for subsequent status.


## 文書の整理 / Documentation scope

公開用ZIPの操作・利用条件文書を19本から8本へ整理しました。導入・復旧（日英）、AWS準備（日英）、利用条件（日英）、更新（日英併記）、保存再開（日英併記）を残します。製品README、WordPress readme、ライセンス、AWSポリシー例も保持します。

準備画面の詳細、ACF対応表、世代管理、FAQ、運用変更の案内、実装規則はGitHubから必要時に参照します。過去の試験経緯・研究資料・審査記録はZIPに含めません。資料はGitの履歴とリポジトリに残し、[文書案内](../../packages/markdown-m1/docs/README.md)から現行ガイドと区別します。

The ZIP contains eight maintained operational/terms documents rather than nineteen. Detailed optional references remain online. Historical diagnostics and test narratives were removed from the save-resumption and installation instructions, and Japanese action labels match the current UI. Guide links to documents omitted from the ZIP now point to GitHub. Runtime behavior and stored data formats are unchanged.

## Artifact and verification

- [Installable ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.6/ozeki-resilience-0.3.3.zip)
- [Matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.6)
- Header version: 0.3.3; candidate: rc.6; 8,277,278 bytes / 3,812 files.
- SHA-256: `e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3`
- [Package audit](../../evidence-public/wordpress-org-033-rc6/package-audit.json): 3,795 runtime files byte-identical to rc.5; 78 bundled relative links resolve; eight bundled guides; no Python/BAT/tools/test artifacts. Product files match source.
- [Isolated installation](../../evidence-public/wordpress-org-033-rc6/validation.json): WordPress 7.1.3; ZIP installation/activation succeeded; all 3,812 installed files match the ZIP.
- [Plugin Check 2.1.0](../../evidence-public/wordpress-org-033-rc6/plugin-check.json): **0 errors / 107 warnings**, same counts as rc.5. Warnings remain recorded for review; no new runtime changes.
- Installation/update/recovery/startup-failure behavior retains the [rc.5 validation](wordpress-org-033-rc5.md); those full functional tests were not repeated for this documentation-only repackaging.
- Submitted rc.3 SHA-256 remains `066c4ae4f47f943a8b7cb4fa31efd6e256ad47772bdb1f4bd99c22a39804973e`.

## Pre-submission upload-note draft (historical)

0.3.3 rc.6 addresses the additional rc.3 review: archived software installation is removed, active WordPress identifiers use ozeki_resilience with migration, custom upload locations are supported, and development artifacts are excluded. Failed settings migration preserves viewing and administrator sign-in while pausing saves with retry guidance. The bundled documentation now contains only maintained user instructions. Plugin Check: 0 errors / 107 recorded warnings. SHA-256: e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3.

## Pre-submission reply draft (historical)

Thank you for the additional review. The revised package removes archived theme/plugin code installation. Recovery imports information assets into WordPress with trusted software installed separately by the administrator.

Active WordPress identifiers now use the ozeki_resilience prefix. Old names are retained only for compatibility migration and archived data, not active registrations. Directory-location findings are addressed, and development and historical test documents are excluded from the ZIP. Installation, update, recovery and startup-failure handling were verified; the final documentation repack was also installed and checked with Plugin Check.

Package and verification: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc6.md

Regards,
Hiroshi Ozeki

## Reply sent / 送信した返信

Thank you for the additional review. I have uploaded 0.3.3 rc.6 and addressed the reported issues.

Recovery no longer installs archived theme/plugin code. Administrators prepare a separate WordPress environment with compatible themes and plugins from trusted distributors; Resilience restores independent information assets and recognized relationships/settings.

Active WordPress identifiers now use the ozeki_resilience prefix. Legacy names remain only for compatibility migration and archived data, not active registrations. Development files and historical test notes are excluded from the ZIP, and restoration uses the configured uploads location.

Installation, update, recovery and startup-failure handling were checked. Plugin Check 2.1.0 reports 0 errors and 107 documented warnings.

Package and validation:
https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.6

ZIP SHA-256: e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3

Regards,
Hiroshi Ozeki
