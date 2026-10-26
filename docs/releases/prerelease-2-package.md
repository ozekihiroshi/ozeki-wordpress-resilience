# Pre-release 2 package preparation / 次回試験版の配布準備

Work: packaging and evidence organization. State: verified with limitations, unpublished. Completion: current bilingual documentation bundled, unchanged tested executable entries, package/link checks and SHA-256 recorded, reviewable PR merged. Contribution: distribute the verified original-preservation and retention/recovery behaviour with accurate promises.

作業：配布準備・エビデンス整理。状態：検証済み・制限あり、未公開。完了条件：英日文書収録、実行コード同一性、収録内容・リンク・SHA-256確認とPRマージ。原本保全・保持・削除後復旧の検証済み範囲を正しく配布するための作業です。

## Distribution / 配布物

Proposed tag / 予定タグ: `v0.3.1-pre.2`. No tag or release is created. Plugin display version remains 0.3.1.

[Installable ZIP](../../release-candidates/20261026-prerelease-2/ozeki-wordpress-resilience-0.3.1-pre.2.zip) · [SHA-256](../../release-candidates/20261026-prerelease-2/ozeki-wordpress-resilience-0.3.1-pre.2.zip.sha256) · [Checks](../../release-candidates/20261026-prerelease-2/VALIDATION.json) · [Entry hashes](../../release-candidates/20261026-prerelease-2/manifest.json)

SHA-256: `109f0db79f1e5b0886b11d6ebcb2df0f4728912baa1217f977de91760b0b3d0a`

7,455,881 bytes / 3,831 files. Eight documentation entries updated and two bilingual release-note files added; 3,821 entries unchanged. All executable files, composer files and vendor dependencies are byte-identical to [the tested gfs-lock-read candidate](unset-lock-final-m1-031.md), whose checksum is `8b14e94666e733cdc5018dbb4bdb4e7877ca9d91e3360f837d20877cece0a168`.

文書8件更新・英日リリース説明2件追加のみ。製品PHP・依存定義・vendorは検証済み候補と全件同一。旧候補と公開済みpre.1は変更していません。

## Verification / 確認

ZIP CRC integrity, unchanged non-document entries, no removed entries, current package-document equality and relative-link destinations passed. Repository links point to existing documents; the new release notes pin the PR52 acceptance record to its merged commit. No runtime, S3, IAM or content operations were performed. This is package verification, not additional functional testing.

ZIPの破損検査、文書以外の全件同一性、既存収録ファイルの欠落なし、最新文書との一致、相対リンクの参照先を確認。リポジトリ参照も実在文書を指し、新しい説明内のPR52検証記録はマージコミットに固定しています。製品実行・S3・IAM・コンテンツの操作は行っていません。

Fresh installation and update evidence is reused from the identical executable candidate, not asserted as a fresh install of these exact new ZIP bytes. Real S3, injected failure, standard browser operation and scheduled server-invoked wp-cron.php evidence remain separate. [PR52 acceptance](cleanup-browser-scheduled-acceptance.md) confirms the later cleanup/recovery routes; it does not change the scope of older records.

同一コード候補の新規導入・更新の証拠を再利用し、この新ZIPを実環境へ再導入したという意味ではありません。実S3・失敗注入・ブラウザ・サーバからの標準Cron入口の証拠を区別します。

## Prepared release description / 公開時の説明案

[English](../../packages/markdown-m1/docs/prerelease-2.md) · [日本語](../../packages/markdown-m1/docs/prerelease-2-ja.md)

The notes distinguish delivered functions, required S3/runtime conditions and unverified limits: no malware-free or unconditional recovery promise; HTTP loopback, long-term recurrence, real locked/interrupted deletion remain unverified. Manual deletion is limited to policy-eligible expired resources. This is ready for a separately authorized GitHub Pre-release publication, not a stable release or WordPress.org submission.

実現機能・必要条件・未検証範囲を分離しています。完全無害化・無条件復旧は保証せず、HTTP起動・長期反復・実S3の保護中／途中停止削除は未検証。手動削除は保持規則に従う期限切れ候補に限定します。別途公開指示を受けられる配布準備であり、安定版・WordPress.org申請ではありません。
