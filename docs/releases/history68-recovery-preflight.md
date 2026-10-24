# History 68 recovery and bidirectional preflight

2026-10-25. Existing isolated dm destination only; no new infrastructure or authentication helper.

Existing complete Checkpoint through33 (`b896a01ba5ac36056289736fe1a69ab9a79ef21c28fcd465cd8cd5624b478fe1`, Version ID `N.1_fy371NBQSxQhsOnZZgPoqhgp5MTW`) plus formal history34–68 reconstructed trial article37. S3 original and restored body SHA-256 both `a5a99f83ce274806f763e2d942196547190153b0d6044870673dbd744db4184e`; title, slug and publish matched. Result: 23 post records, zero file writes because existing matching files were reused. This used the existing product method, not another browser recovery acceptance.

The original preservation check failed: destination-only empty auto-draft30 was removed by complete replacement. The preflight had inspected source rows only. Its exact backed-up row was restored separately and final existing-post field hashes matched. Initial failure evidence remains preserved. User rows, logical user metadata, post metadata excluding edit locks, comments and membership settings matched; history stayed68. The separate live-site probe was unchanged.

Updated test preflight enumerates both sides, all types/statuses, and reports additions, changes and destination-only removals. Read-only rerun found exactly auto-draft30 on the destination only, 23 unchanged matching rows, zero changed/source-only rows, and requires review. Synthetic tests also cover ordinary drafts and published destination-only posts, empty source, changed fields and duplicate IDs. The test is included in CI; remote CI has not yet run for this follow-up.

Product complete replacement is unchanged. This helper is not an automatic UI gate, public replay API, full metadata/file audit or concurrent-edit protection. Existing lab runner calls internal replay via reflection; this is test infrastructure only. The existing duplicate DISABLE_WP_CRON warning remains an environment issue. Flamingo behavior was not changed.

No recovery was repeated during the preflight improvement. No member/content edits, S3 writes, email, periodic execution, deployment or formal release occurred in that follow-up. Product PHP and validated ZIP SHA-256 `901950f74d02d40bb4c21f92cecb6f7a80d30192f211a84191857f4e2bd3e5d2` are unchanged; edited documentation and test helper are not repackaged into that ZIP.

Local evidence: `release-readiness/history68-recovery-20261025/RESULT.md`, original `verification.json`, corrective `preservation-final.json`, `preflight-v2.json` and identical `diff-v2-live-before.json` / `diff-v2-live-after.json`.

日本語：復旧本文の一致は合格しましたが、最初の既存保持検査で空の自動下書きの除外を検出しています。元行の復帰後に最終一致を確認した事実と、試験基盤の片方向比較の不足を記録します。今回の双方向確認改善では再復旧やコンテンツ変更は行わず、自動下書き30を読取りだけで検出しました。製品の置換動作や検証済みZIPは変更していません。
