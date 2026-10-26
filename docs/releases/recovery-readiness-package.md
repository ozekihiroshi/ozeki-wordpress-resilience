# Recovery readiness candidate — not published

Work type: existing-feature verification, documentation and packaging. State: candidate prepared; environment decision pending. Completion: review the scope and checks, resolve the IAM/active-lock acceptance boundary, then merge. No release publication.

作業の種類：既存機能の検証・文書と配布整理。状態：候補準備済み、環境条件の判断待ち。完了条件：範囲と確認結果をレビューし、IAM・実ロックの受入境界を決定したうえでマージ。リリース公開は行わない。

- [English results and limits](../../packages/markdown-m1/docs/recovery-readiness.md)
- [日本語の結果と制限](../../packages/markdown-m1/docs/recovery-readiness-ja.md)
- [Candidate ZIP](../../release-candidates/20261026-recovery-readiness/ozeki-wordpress-resilience-0.3.1-readiness.zip)
- [SHA-256](../../release-candidates/20261026-recovery-readiness/ozeki-wordpress-resilience-0.3.1-readiness.zip.sha256)
- [Archive verification](../../release-candidates/20261026-recovery-readiness/verification.json)

The archive updates documentation only relative to the verified optional-Markdown ZIP (`f6ab14e882cd2b1a768b6efd7fed90cc2f4c0ad3a190af515949dc9ebb8314f2`). Every executable/vendor entry is identical, no entries were removed, and archive integrity and local documentation links were checked. Fresh-install/update preservation evidence comes from [the unchanged executable candidate](optional-markdown-package.md); this is not another installation trial. Current FAQ and guides are included. Published pre.1/pre.2 are unchanged.

検証済み条件付き依存ZIPに対し文書のみ更新。実行コード・vendorは全件バイト一致、削除エントリなし。ZIP整合とローカル文書リンクを確認。新規導入・更新時の保持確認は同一実行コードの候補から引き継ぎ、新しい導入試験とは区別する。最新FAQ・ガイドを収録し、公開済みpre.1/pre.2は変更しない。

Actual S3 deletion followed by pre-transmission failure injection and isolated dm recovery succeeded. Exact IAM-example deployment and active-retention acceptance are not complete: role-policy inspection and the dedicated prefix's PutObjectRetention were denied. Those environment conditions must not be presented as a product fix or an acceptance pass.

実S3削除後の送信前障害注入と隔離dm復旧は成功。IAMサンプル単独での実適用と実保持ロックの受入は未完了。ロールポリシー参照と専用prefixのPutObjectRetentionが拒否されたためで、製品修正や受入合格とは扱わない。
