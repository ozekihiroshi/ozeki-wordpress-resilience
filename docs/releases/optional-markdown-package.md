# Conditional Markdown dependency — distribution ZIP

2026-10-26. Unpublished candidate; published pre.2 remains unchanged.

## Type, state and completion

Work: packaging, guide maintenance and differential verification of existing functions. State: verified with the boundaries below. Completion: new installation and replacement of pre.2 preserve configured state and readable formal history; packaged source matches the reviewed conditional-dependency change; English/Japanese prerequisites agree. All completed.

Candidate: `ozeki-wordpress-resilience-0.3.1-optional-markdown.zip`

SHA-256: `f6ab14e882cd2b1a768b6efd7fed90cc2f4c0ad3a190af515949dc9ebb8314f2`

7,487,147 bytes; 3,840 files. PHP plugin version remains 0.3.1; identify the candidate by its filename and SHA-256. No release/tag was created.

## What is included

Only Plugin.php and SiteSnapshot.php executable entries differ from published pre.2. Their bytes match the previously tested working source. Vendor files are unchanged. Updated English/Japanese guides, README, installation notes, prior complete IAM examples and conditional-dependency verification are included. IAM examples were not applied. Archive integrity, all packaged source equality and 131 local documentation links passed. Changed PHP files pass syntax checks.

Native-only Baselines do not require Markdown Documents. Active Markdown is bundled; remaining Markdown documents/originals with an inactive plugin stop capture before saving. Markdown recovery still requires the compatible recorded runtime to be available (tested 0.1.1). The guides distinguish this candidate from published pre.2's unconditional admin prerequisite. Existing older trial records remain historical evidence.

## Installation/update evidence

The existing dm WordPress container, PHP and DB service were reused with separate `/tmp/owr-optional-markdown-final-20261026/{fresh,upgrade}` files and `owromdzip_20261026_*` tables. Neither fixture installed Markdown Documents. Cron execution, auto-updates and mail were disabled; protection and cleanup were off. Scheduled-state preservation was checked without dispatching events.

- Fresh: extracted the candidate, performed WordPress installation and plugin activation, prepared fixture state, and verified it in a subsequent process.
- Upgrade: installed published pre.2, prepared fixture state, replaced plugin files with the candidate, and verified preserved state.
- Both preserved S3 configuration, GFS settings/reservation, two nonempty synthetic pending entries, failure diagnostics, individual/site recovery results, Baseline result and test content.
- Both read the same existing dedicated S3 history (one record) with identical hash and retrieved its original with a matching SHA-256. No S3 writes/deletes were issued.
- Every installed file matched the final ZIP in both fixtures; no Markdown runtime was loaded. Mail calls: 0.

This is ZIP extraction/activation/replacement verification, not another browser Upload Plugin test. Synthetic pending entries were preserved, never resumed. It does not newly verify a history write, Baseline capture or recovery from the installed ZIP. The prior [standard-admin real-S3 evidence](optional-markdown-baseline.md#follow-up-standard-administration-and-real-s3-2026-10-26) separately covers both Baseline/restore branches with the same executable source. It did not test automatic loading of an unavailable Markdown runtime, empty-disk software deployment or new math rendering guarantees.

## Environment and remaining work

No product correction was needed during packaging. The packaging allowlist initially omitted the already-approved AWS example directory and was corrected; the checks did not identify an executable change outside the two expected files. Local documentation links were made self-contained, then the final archive was rechecked. These were packaging/test preparation adjustments, not product runtime failures.

Existing S3 assets, live content, IAM and published archives were unchanged. Published pre.2 SHA-256 remains `109f0db79f1e5b0886b11d6ebcb2df0f4728912baa1217f977de91760b0b3d0a`. Long-term schedules, interrupted deletion and exact-IAM-template deployment remain in the existing remaining-confirmations document; this packaging task adds no acceptance claims for them.

Local records: release-readiness/optional-markdown-final-20261026/build-result.json, install-result.txt, final-install-result.txt. Setup scripts are single-use; synthetic pending fixtures must not be resumed.

## 日本語

作業種類は配布物整備・文書更新・既存機能の差分検証、状態は検証済み・制限ありです。新規導入とpre.2からのファイル置換更新で、設定・履歴・非空の模擬未確定キュー・失敗理由・復旧結果・試験本文の保持を確認し、完了条件を達成しました。両環境ともMDを導入せず、実S3は既存専用履歴と原本の読取りだけです。

標準ブラウザでのZIPアップロードや未確定履歴の再開を今回再試験したものではありません。前回の標準管理画面・実S3によるBaseline作成／復旧と、今回のZIP展開・有効化・更新保持の証拠を区別します。公開済み版と未公開候補の必須条件を英日ガイドに併記しました。プラグイン表示版だけでなくファイル名・SHA-256で識別してください。

製品完成への寄与は、通常投稿サイトの不要な導入条件を外した修正を、説明と整合した配布物として提供できることです。既存S3資産・コンテンツ・IAM・公開済みZIPは変更せず、公開していません。

## Final PR review — 2026-10-26

No blocking findings in the bounded review. Candidate SHA-256 and installed-source identity were reconfirmed without rebuilding the ZIP. Only Plugin.php and SiteSnapshot.php executable entries differ from pre.2; vendor is unchanged. 131 in-ZIP and 43 reviewed repository-relative links resolve. Complete IAM examples parse as JSON; AWS application is not claimed. Existing offline tablepress-capture, site-checkpoint-verification, application-rules and site-point-time contracts pass. They do not replace or expand the separately recorded real-S3/browser and ZIP-installation evidence. No cloud acceptance was repeated for this review.

最終レビューでは、この変更範囲にマージを妨げる問題を認めませんでした。ZIP再生成なしでハッシュ・コード一致・リンク・既存の関連オフライン契約テストを確認しました。実S3／ブラウザとZIP導入更新の検証範囲、MDランタイムの事前準備、模擬キューの保持のみという制限は維持しています。
