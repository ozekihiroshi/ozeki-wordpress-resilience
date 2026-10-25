# 0.3.1 Pre-release package and actual S3 confirmation

Work: documentation/package correction and narrowly scoped existing-function verification. State: verified with limits; prepared for GitHub Pre-release v0.3.1-pre.1. Completion: repaired bilingual package links, unchanged executable bytes, actual original PUT/read-back/history PUT confirmed, identified immutable distribution.

## Package

[Installable ZIP](../../release-candidates/20261025-prerelease/ozeki-wordpress-resilience-0.3.1-prerelease-prepared.zip)

SHA-256: `913bac85cb704f24edaaa76d793222d5b25676eef0ad87543b102c7d1933762f`

7,432,338 bytes / 3,823 files. Plugin version remains 0.3.1; use tag v0.3.1-pre.1, exact filename and checksum. GitHub source archives are not the installable product.

Only README.md, RAADME-jp.md, docs/start-here.md and docs/start-here-ja.md differ from the prior validated save-verification-final ZIP (SHA-256 `6105125270e459fdaeb392337c159cb35f6c705abe73293ec2ef7220becbc308`). All other 3,819 entries, including product PHP, assets and vendor libraries, are byte-identical. Entry names/count, CRC integrity, source/manifest identity and documentation link targets were checked. The previous ZIP is retained unchanged. Stale package identities and the incorrect download directory are corrected. Repository references in these bundled documents use the release tag.

## Additional real-S3 write verification

Reused community wp-rescue, the existing isolated owrseps3_20261025_source_ WordPress namespace, standard SDK EC2-role credentials and an unused subprefix under the already authorized M1 test range. No IAM, infrastructure or authentication helper was added. New test page and image only; original isolated post rows and existing current S3 inventory outside the trial prefix were unchanged. Trial config was restored. No email, cron, deletion or shared-site plugin deployment.

The prepared ZIP was extracted separately; its product classes processed a normal WordPress API page publication containing a local PNG. A request-local observation handler forwarded commands to the real standard-auth SDK and recorded successful command names/keys/Version IDs; it did not substitute responses, credentials or writes.

Observed successful order:

1. Actual S3 PUT of image, complete HTML and metadata (three new fixed versions).
2. Actual GET of those exact three Version IDs and product hash/reassembly checks.
3. Actual PUT of formal history sequence 1, returning an S3 Version ID.
4. Actual read of that history and direct original re-fetch: HTML and image match; no pending article operation.

Mock writes: zero. This closes the earlier actual-history-write evidence gap for the representative protected article+image operation. The write trial used an intermediate ZIP; final ZIP changes after it are documentation only, and all executable entries remain identical.

## Evidence boundaries and promises

- The earlier source/metadata/split-part/media failure-injection contracts remain evidence that failed verification prevents history PUT. This new test is a real successful write, not a real AWS outage test.
- Normal WordPress PHP API and product article hooks were exercised, not browser editing or every adapter. The local PNG was a test attachment; this did not repeat the media-upload UI trial.
- Prior fresh install/update tests preserve settings, nonempty synthetic queues and recovery results. No new full-site restore, browser upgrade, scheduled execution, real cleanup or large-media performance test is claimed for this documentation-only package.
- For supported confirmed operations, originals are retrieved by fixed version and checked before confirmation. Body/details can confirm separately. Current status display reads history, not a live audit of every original. Old history is not retrospectively certified; initial snapshot/Checkpoint creation is unchanged by this correction.
- Recovery remains conditional on supported types/versions, a trusted baseline, one source writer, suitable IAM/versioning and retention of required S3 versions. No malware-free claim, indefinite survival after external deletion, universal plugin support, cross-system atomicity or recovery of unconfirmed operations.
- Capture-error diagnostics are historical and may be unavailable on DB failure/process termination. No auto-retry/rollback machinery was added.

## 日本語

英日README・導入案内の4ファイルだけを修正し、残る3,819収録ファイルは検証済み版とバイト単位で一致しました。新しいSHA-256は上記を使用します。0.3.1の旧候補と混同せず、タグ・ファイル名・ハッシュで識別してください。

既存communityの隔離WordPressで試験ページと画像を作り、実S3への原本3件PUT、同じ固定版からの全件GET照合、正式履歴1件の実PUT、履歴と原本の再読取りまで確認しました。今回は模擬書込み0件です。標準AWS認証を用い、既存S3資産・既存投稿は前後一致し、設定は復帰、メール送信0件でした。

成功経路の未確認部分を限定して確認したもので、全連携・ブラウザ操作・AWS障害・サイト全体復旧の再試験ではありません。異常系とZIP導入更新は従来の検証を引き継ぎます。製品コードは追加変更していません。GitHubの試験版配布であり、WordPress.org公開申請や安定版ではありません。
