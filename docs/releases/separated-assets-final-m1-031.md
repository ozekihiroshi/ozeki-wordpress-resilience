# 0.3.1 separated-assets-final package acceptance

2026-10-25. Work: packaging, existing-feature installation/update verification, documentation. State: verified with limits; not released. Purpose: ship the shared separated-original format and its real-S3 findings in an identifiable candidate. Completion: fresh activation and replacement of the previous ZIP preserve configuration, history and local operational state; installed files match the candidate. Contribution: independently usable recovery originals in a deployable product.

## Artifact

- [Candidate ZIP](../../release-candidates/20261025-separated-assets/ozeki-wordpress-resilience-0.3.1-separated-assets-final.zip)
- SHA-256: `eabb776970a057253d6ae58650f1e732f8ee4308b153bc450435ec8724c168eb`
- 7,414,658 bytes; 3,818 files. Product header remains 0.3.1; identify the candidate by filename and digest.
- Dependency/vendor bytes identical to the previous recovery-errors-final ZIP. Earlier ZIP preserved with SHA-256 `8aa35ca377346125c1b5019a014ada528d54157063a64f7ec80555c54fc5d3a9`.
- Includes shared AssetFormat, new-original reader, complete-snapshot separation, source-digest comparison, absent-option persistence correction and English/Japanese documentation. Unknown captured fields are retained. No new certification/activation policy, data migration, deletion, retry or rollback facility.

## Package-specific checks

Existing dm Docker and DB service reused with isolated `owrsepzip_20261025_fresh_` / `owrsepzip_20261025_upgrade_` tables and `/tmp/owr-separated-final-20261025` content. Fresh installation activates Markdown Documents and the candidate. Upgrade starts from the previous recovery-errors-final ZIP, seeds test-only operational state, and replaces plugin files with the final ZIP.

Both passed:

- Active plugin, configuration, generated page and identity of the test state retained.
- Nonempty article pending record and one shared-queue record, their full payloads and recorded error messages retained. These are synthetic preservation fixtures; they are never resumed or written to S3.
- Individual/site recovery results and latest failed-attempt record retained exactly.
- Existing dedicated S3 formal history (one confirmed operation) unchanged by hash; the installed new reader retrieves and validates its separated-format original with standard SDK EC2-role authentication. S3 is read-only in this test.
- Every installed file matched all 3,818 entries of the candidate ZIP in both namespaces.
- No trial Checkpoint schedule, no verification mail, no S3 writes; existing shared-site probe identical before/after.

ZIP-extracted code also passed separated-assets, Checkpoint, comments and recovery-errors contracts and PHP syntax checks. These tests cover standalone known content, unknown-information retention, legacy reads, independent snapshots, history replay, corruption/partial-write rejection and option persistence. They use in-memory S3/synthetic errors and are not additional AWS failure tests.

## Evidence boundaries and limits

[Earlier real-S3 acceptance](separated-assets-m1.md) verified source-community capture/normal save/Checkpoint and target-dm reconstruction using 24 fixed versions only within that Checkpoint. It used the same product source now byte-matched in the candidate. This packaging run adds installation, replacement and read-only new-format compatibility checks; it does not repeat complete-site restoration, browser uploading, all plugin rendering, or pending-history resume. Existing browser/update evidence remains separately scoped.

New records require this reader; the prior recovery-errors-final ZIP cannot restore newly separated records. The new reader still reads old originals/snapshots without rewriting S3. Independent data is directly readable, but identities, relationships, settings and publication state still need metadata for reconstruction. Preservation of unknown information does not certify its execution or activation.

No product fault was encountered. The existing live-probe duplicate DISABLE_WP_CRON warning is an environment bootstrap issue. No production plugin deployment, existing member/content changes, scheduled execution, S3 deletion or formal release.

Local evidence: `release-readiness/separated-assets-final-20261025/` build-result.json, ZIP manifest, zip-contract-results.json, install-result.txt, zip-test.php and send.sh. Single-use install script must not be blindly repeated. No new AWS resources or authentication helper.

## 日本語

作業種類はZIP作成・導入更新検証・文書整理、状態は検証済み・制限ありです。最終候補の新規有効化と旧recovery-errors-final ZIPからの置換が成功し、設定・正式履歴・非空の未確定操作2件・エラー・復旧結果・試験記事の保持を確認しました。導入ファイル3,818件がZIPと一致し、標準EC2ロール認証で実S3の新形式原本を読み取れました。

今回の更新は隔離環境でのファイル置換です。ブラウザからのアップロード、未確定操作の再開、全連携の表示、サイト全体の復旧を再実行したものではありません。実S3での原本単独取得と元環境なし復旧は前段の証拠として区別します。既存サイト・S3資産は変更せず、定期実行・メール送信・正式公開は行っていません。

原本と付随情報の分離は本候補に収録されています。未知情報も保持します。新形式の保存後は旧候補へ戻してもその新形式を復旧できません。新候補から旧形式の読取りは可能で、自動移行は行いません。既存のCron定数重複警告は試験環境側であり、今回新しい製品不具合は見つかっていません。
