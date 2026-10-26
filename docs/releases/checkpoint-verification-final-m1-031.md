# Initial snapshot / Checkpoint verification distribution candidate

Date: 2026-10-25. Unpublished; not a new GitHub release. Plugin header remains 0.3.1; identify this candidate by full filename and SHA-256.

- [ZIP](../../release-candidates/20261025-checkpoint-verification/ozeki-wordpress-resilience-0.3.1-checkpoint-verification.zip)
- [SHA-256](../../release-candidates/20261025-checkpoint-verification/ozeki-wordpress-resilience-0.3.1-checkpoint-verification.zip.sha256)
- [File manifest](../../release-candidates/20261025-checkpoint-verification/ozeki-wordpress-resilience-0.3.1-checkpoint-verification.manifest.json)
- SHA-256: `61d7a91219fd09e9a479f1d608bb7a20e5d169a6ce84d291bcf5417b9fe4ee45`
- Size: 7,424,974 bytes; 3,824 files. ZIP CRC and 54 packaged relative links checked.

## Change and evidence boundaries

The only changed product code file relative to published v0.3.1-pre.1 is `src/SiteSnapshot.php`. It reads every saved resource by fixed version and checks the hash before manifest publication. Other changes are documentation, including portable links from packaged documents to repository records. Vendor dependencies and all other executable product files are unchanged.

[Implementation and actual S3 results](../../packages/markdown-m1/docs/site-checkpoint-verification.md) describe initial capture and Checkpoint success with 29 resources each. Actual S3 writes/reads succeeded. Failed retrieval/mismatch results were deliberately injected after real GETs; they are not evidence of an actual AWS outage. Actual WordPress administration processing and HTML rendering were checked, not browser interactions.

## ZIP installation/update acceptance

Existing dm Docker, WordPress core and DB service were reused with dedicated `owrcpverify_20261025_fresh_` and `owrcpverify_20261025_upgrade_` table namespaces and separate plugin/content directories. No shared-site plugin was replaced.

- Fresh installation and activation succeeded.
- Published v0.3.1-pre.1 was installed in the upgrade fixture before replacing its files with this candidate and bootstrapping WordPress again.
- Configuration, two nonempty synthetic pending entries, error/capture notices, individual/site recovery results, the recovery attempt, and snapshot result remained equal.
- Existing S3 formal history (one record) and its independent original were readable and unchanged; no S3 writes were performed by this installation test.
- Test content remained equal. All 3,824 installed files matched the final ZIP on both paths; shared-site before/after probe matched.
- Tests against product files extracted from the final ZIP passed: resource verification, administration failure recording, point-in-time reconstruction and recovery result rendering. These are fixture contracts, not an additional live S3 restore.

The install/update test uses PHP activation and ZIP extraction, not browser upload. The pending queues are synthetic preservation fixtures and were not resumed. Previously accepted browser/resume evidence is separate. No new full restoration or scheduled execution was performed.

The existing `DISABLE_WP_CRON already defined` warning appeared in the shared-site probe. This is a pre-existing test-environment configuration warning, not a product regression; all checks completed. Mail was blocked in the test, and automatic scheduling was disabled. No existing S3 assets, members or content were changed. Published ZIP SHA-256 remains `913bac85cb704f24edaaa76d793222d5b25676eef0ad87543b102c7d1933762f`.

Local evidence: `release-readiness/checkpoint-final-20261025/` contains build/result manifests, ZIP-extracted contract results and dm installation output. Its deployment script is single-use and already executed. An intermediate candidate failing packaged-link checking was retained separately and was not deployed.

## 日本語

作業種別は配布物作成・導入更新の差分検証・文書整理です。状態は検証済み・制限ありで、未公開です。新規導入、公開済みPre-releaseからの更新、設定・正式履歴・非空キュー・各結果の保持という完了条件を満たしました。

英日READMEで今回の未公開候補と公開済み版を区別し、実S3での成功確認と試験用の失敗注入を分けています。導入更新は既存dmサービスの隔離領域で行い、ブラウザ操作やキュー再開を再試験したものではありません。公開済みZIP・既存S3資産・既存コンテンツは変更していません。復旧資源を照合してから確定する製品要件を、新しい配布物へ反映した確認です。
