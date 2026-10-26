# Recovery readiness candidate — not published

Work type: existing-feature verification, documentation and packaging. State: candidate verified; sample-only IAM acceptance completed. Completion: review the scope and checks, confirm recorded temporary-role withdrawal and sample-only results, then merge. No release publication.

作業の種類：既存機能の検証・文書と配布整理。状態：候補検証済み、サンプル単独IAM受入完了。完了条件：範囲と確認結果をレビューし、一時権限撤去とサンプル単独の検証結果を確認したうえでマージ。リリース公開は行わない。

- [English results and limits](../../packages/markdown-m1/docs/recovery-readiness.md)
- [日本語の結果と制限](../../packages/markdown-m1/docs/recovery-readiness-ja.md)
- [Candidate ZIP](../../release-candidates/20261026-recovery-readiness/ozeki-wordpress-resilience-0.3.1-readiness.zip)
- [SHA-256](../../release-candidates/20261026-recovery-readiness/ozeki-wordpress-resilience-0.3.1-readiness.zip.sha256)
- [Archive verification](../../release-candidates/20261026-recovery-readiness/verification.json)

The archive updates documentation only relative to the verified optional-Markdown ZIP (`f6ab14e882cd2b1a768b6efd7fed90cc2f4c0ad3a190af515949dc9ebb8314f2`). Every executable/vendor entry is identical, no entries were removed, and archive integrity and local documentation links were checked. Fresh-install/update preservation evidence comes from [the unchanged executable candidate](optional-markdown-package.md); this is not another installation trial. Current FAQ and guides are included. Published pre.1/pre.2 are unchanged.

検証済み条件付き依存ZIPに対し文書のみ更新。実行コード・vendorは全件バイト一致、削除エントリなし。ZIP整合とローカル文書リンクを確認。新規導入・更新時の保持確認は同一実行コードの候補から引き継ぎ、新しい導入試験とは区別する。最新FAQ・ガイドを収録し、公開済みpre.1/pre.2は変更しない。

Actual S3 deletion followed by pre-transmission failure injection and isolated dm recovery succeeded. A later temporary, prefix-scoped PutObjectRetention grant enabled exact retention readback and product candidate exclusion without deletion. All 32 versions and selected bytes remained unchanged. Legal Hold ON and natural expiry are not claimed. A separate sample-only source/recovery role trial then passed save/verify/commit, retention exclusion, 16 fixed-version deletions and dm recovery; both temporary roles were removed. See the bilingual evidence above. These are environment/acceptance boundaries, not product fixes.

実S3削除後の送信前障害注入と隔離dm復旧は成功。後のprefix限定一時PutObjectRetention許可により、期限読戻しと製品の候補除外も確認しました。この確認では実削除なし、全32版と対象原本は不変。Legal Hold ON・自然期限満了は未検証です。別のサンプル単独ロール試験で保存・照合・確定・保持除外・16固定版削除・dm復旧に成功し、一時ロール2件を撤去。上記英日記録に範囲を区別しています。製品修正ではなく環境・受入条件です。
