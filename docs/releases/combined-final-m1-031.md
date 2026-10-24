# Combined final ZIP — 0.3.1, 2026-10-24

## Candidate

`ozeki-wordpress-resilience-0.3.1-combined-final.zip`

SHA-256: `afbdf0844940569a494e7cd965734d75f6f0f04c810950024d610934787468f2`

7,371,893 bytes; 3,810 files. Previous TablePress final ZIP retained unchanged. Dependency/vendor bytes match that candidate. Every packaged product file matches the source used to build it. The only changed packaged files are README.md, RAADME-jp.md, src/SiteSnapshot.php and new docs/combined.md. Product remains 0.3.1; identify this candidate by filename and hash. No formal release or deployment to existing site plugin directories.

## Actual acceptance

Existing dm Docker/core/DB service, separate `/tmp/owr-combined-final-20261024/{fresh,upgrade}` content directories and `owrcfinal_20261024_{fresh,upgrade}_` database prefixes. No new server, bucket, role or authentication helper. AWS SDK default EC2 role credentials; existing S3 trial history read only.

- Fresh installation of final ZIP: PASS.
- Upgrade from frozen PR25 TablePress 0.3.1 ZIP: PASS.
- Both: configuration, content/asset identity, previous recovery result, comments, form/receipt fields/channels, membership credentials/settings, TablePress registry/cells/settings, frozen pending/error records and existing Cron entries retained. UI labels checked. No Resilience schedule enabled.
- S3 formal history remains 29 entries; SHA-256 of serialized history before/after: `5461dbc673603a739ba116eb8c0bee8357b5786079a236583322974e3f1be200`.
- Both installations restored the existing complete Checkpoint through 21 plus tail through 29 via product SiteSnapshot::restore. Checkpoint manifest SHA-256 `ccddff2471020e9bd19882e869371db3c568cb851b8c2dc3e840967c0f838bd7`, fixed VersionId `vFwIAiDQLXk9SeQ.dTD5MQaMsURSfGV_`.
- Exact Post/Page bodies after destination URL relocation, publish status, links, replacement image hash, comment content/moderation/relation, CF7 and Flamingo metadata, WP-Members authentication/profile/guest restriction, TablePress data/options/visibility/ID and combined shortcode rendering: PASS.
- CF7 deny-all upload guard restored and validated. Destination administrator preserved. All 3,810 installed ZIP file hashes match before and after recovery.
- Recovery and verification mail attempts: zero. Mail transport blocked throughout trial. No source DB/local queue used as recovery input. Private expected fixture used only for assertions, never published.
- Existing dm site's content/configuration/Cron/history probe output identical before/after. No source-site changes or S3 writes in this packaging test.

## Product versus test infrastructure

Product correction: snapshot previously rejected CF7's normal deny-all `uploads/wpcf7_uploads/.htaccess`. Exact known path and content (LF/CRLF) now accepted, with arbitrary control files, appended allow directives and PHP/PHAR still rejected. Guard is preserved, never disabled.

Trial infrastructure: first installation stopped before installation because the proposed `owrczip_20261024_` database prefix already belonged to a prior test. Read-only mysqli inspection identified this; that DB was not overwritten. A previously unused `owrcfinal_20261024_` prefix was checked before installation. A diagnostic WordPress-bootstrap probe was rejected by automatic approval review and was not executed; direct read-only SQL was used instead.

Some standalone regression scripts expected source-tree relative paths. Their local trial copies were adjusted to load code from the installed ZIP, then only the uncompleted tests were rerun. Product code unchanged. Existing duplicate DISABLE_WP_CRON warning in live probe remains an environment configuration issue. No new memory failure.

Earlier combined test fixed an inherited fictional content URL; earlier TablePress browser test corrected proxy/JavaScript setup. Neither is a product guard fix.

## Regression and limits

Against final-ZIP code: upload-guard, Checkpoint, comments, forms, membership, TablePress, capture queue and cleanup contracts PASS. These tests explicitly use in-memory doubles; the two recovery integrations use real S3. No new cloud CI run in this task.

The original combined change sequence was reused, not regenerated. Browser tests for all adapters were not repeated. Separate TablePress browser acceptance covered add/update/delete, recovered search/sort/pagination. No claim of arbitrary plugins, premium modules, same-asset concurrent writes, external imports or universal WordPress equivalence. Only confirmed formal history is recoverable; source changes without confirmed history are excluded. Optional plugins remain separately installed. Mail, scheduled execution, formal publication and S3 cleanup remain deferred.

## 日本語要約

修正版最終ZIPで新規導入・旧TablePress版からの更新・設定と履歴の保持・同一Checkpointと後続履歴からの同居復旧を確認しました。CF7保護ファイルの拒否は製品修正、試験DB接頭辞の重複と契約試験の相対パスは試験基盤の問題として区別しました。既存コンテンツ・会員・IAM・既存S3資産は変更していません。メール送信・定期実行・正式公開は実施していません。