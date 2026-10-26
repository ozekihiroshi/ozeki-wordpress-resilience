# Recovery readiness candidate — not published

Work type: existing-feature verification, documentation and packaging. State: candidate prepared; environment decision pending. Completion: review the scope and checks, confirm temporary-policy withdrawal and resolve the exact IAM-template acceptance boundary, then merge. No release publication.

作業の種類：既存機能の検証・文書と配布整理。状態：候補準備済み、環境条件の判断待ち。完了条件：範囲と確認結果をレビューし、一時権限撤去と完全版IAMの受入境界を確認したうえでマージ。リリース公開は行わない。

- [English results and limits](../../packages/markdown-m1/docs/recovery-readiness.md)
- [日本語の結果と制限](../../packages/markdown-m1/docs/recovery-readiness-ja.md)
- [Candidate ZIP](../../release-candidates/20261026-recovery-readiness/ozeki-wordpress-resilience-0.3.1-readiness.zip)
- [SHA-256](../../release-candidates/20261026-recovery-readiness/ozeki-wordpress-resilience-0.3.1-readiness.zip.sha256)
- [Archive verification](../../release-candidates/20261026-recovery-readiness/verification.json)

The archive updates documentation only relative to the verified optional-Markdown ZIP (`f6ab14e882cd2b1a768b6efd7fed90cc2f4c0ad3a190af515949dc9ebb8314f2`). Every executable/vendor entry is identical, no entries were removed, and archive integrity and local documentation links were checked. Fresh-install/update preservation evidence comes from [the unchanged executable candidate](optional-markdown-package.md); this is not another installation trial. Current FAQ and guides are included. Published pre.1/pre.2 are unchanged.

検証済み条件付き依存ZIPに対し文書のみ更新。実行コード・vendorは全件バイト一致、削除エントリなし。ZIP整合とローカル文書リンクを確認。新規導入・更新時の保持確認は同一実行コードの候補から引き継ぎ、新しい導入試験とは区別する。最新FAQ・ガイドを収録し、公開済みpre.1/pre.2は変更しない。

Actual S3 deletion followed by pre-transmission failure injection and isolated dm recovery succeeded. A later temporary, prefix-scoped PutObjectRetention grant enabled exact retention readback and product candidate exclusion without deletion. All 32 versions and selected bytes remained unchanged. Legal Hold ON and natural expiry are not claimed. Complete IAM-example deployment and temporary-policy withdrawal remain unconfirmed; see the bilingual evidence above. These are environment/acceptance boundaries, not product fixes.

実S3削除後の送信前障害注入と隔離dm復旧は成功。後のprefix限定一時PutObjectRetention許可により、期限読戻しと製品の候補除外も確認しました。この確認では実削除なし、全32版と対象原本は不変。Legal Hold ON・自然期限満了は未検証です。完全版IAM実適用と一時権限撤去は未確認で、上記英日記録に区別しています。製品修正ではなく環境・受入条件です。