# Recovery usability corrections — 2026-11-01

Status: tested working candidate on `codex/recovery-usability`; not a new submitted release. The submitted rc.6 ZIP and tags are unchanged.

## Changes / 修正

- A recovery destination hides capture, Checkpoint, retention and cleanup controls. The admin handler rejects those operations; the storage layer blocks object writes, retention changes and version deletion before calling S3. Saving recovery settings disables schedules, automatic cleanup and requested retention.
- Each recovery point exposes its recorded WordPress/plugin versions, installed versions and next actions in Japanese and English. Theme names/versions are reference information. Older points without recorded plugin versions explicitly say so. This inventory is not a full resource validation or a software installer.
- Common recovery preparation failures have Japanese messages and practical next actions. The last attempted point and history boundary remain selected when returning to the page.
- Guides agree on separate recovery URLs, recorded versions, attachment limits and retry guidance. Japanese guidance now links to the current recovery FAQ. The old evidence index labels its package records as historical.

復旧先の操作を整理し、必要な版、不足条件、失敗後の次の操作を表示します。保存形式・既存のS3資産は変更していません。

## Reused environment / 既存環境の再利用

The existing October 26 onboarding configuration was reused, not replaced:

| | Source / 保存元 | Destination / 復旧先 |
|---|---|---|
| SSH alias | `community` | `dm` |
| Container | `wp-rescue` | `owr-m1-wordpress` |
| WordPress entry | `/var/www/html/owr-guide-run` | same |
| Dedicated table prefix | `owrguide_20261026_source_` | `owrguide_20261026_target_` |
| Dedicated content | `/tmp/owr-guide-20261026/source/content` | `/tmp/owr-guide-20261026/target/content` |
| WordPress / PHP | 7.1.3 / 8.3.36 | 7.1.3 / 8.3.36 |
| Markdown Documents | 0.1.1 | 0.1.1 |

The existing test bucket, region, prefix, owner and standard EC2-role authentication were retained. No IAM edits, host PHP changes or production table/content replacements were performed. Mail is suppressed and WP-Cron remains disabled in the fixture. Automatic core updates remain disabled. Host resources are shared: use small, sequential tests.

`dm` uses the already-installed rootless Docker, not `/usr/bin/docker`. Its existing start/status commands are:

```sh
ssh dm 'bash /home/ubuntu/workspace/owr-m1-lab/lab-control.sh start'
ssh dm 'bash /home/ubuntu/workspace/owr-m1-lab/lab-control.sh status'
```

Keep the SSH test session open during work. The existing setup has no linger or boot autostart. The Docker client is `/home/ubuntu/workspace/owr-m1-lab/bin/docker -H unix:///run/user/1000/docker.sock`. Do not substitute the host's PHP 8.1/MySQL for this isolated WordPress/PHP 8.3 environment. Content under container `/tmp` survives stop/start but must be backed up before container recreation.

Before updating the fixtures, all 12 dedicated tables and their content directories were archived with private permissions. Existing test software was 0.3.1. Both sites were updated to the exact submitted rc.6 ZIP first; storage settings, source protection, counts and real-S3 point listing were checked before applying corrections.

## Verification / 確認結果

1. **rc.6 baseline:** actual browser login and recovery on dm from the existing October 26 Baseline through history 2 succeeded before corrections.
2. **Corrected source:** Japanese browser storage check succeeded; a new Baseline through 2 was captured into the existing test prefix at `2026-11-01T10:05:35Z`. Earlier points were retained.
3. **Corrected destination:** recorded WordPress 7.1.3 and Markdown Documents 0.1.1 were visible before recovery. Recovery of the new Baseline succeeded.
4. **Ordinary edit:** the existing test post title was changed in the standard editor and saved. Formal history 3 was confirmed; pending counts were zero.
5. **Checkpoint plus tail:** browser recovery through history 3 succeeded. Dedicated post/page IDs 1 and 2 matched title, body, type and publication state after the expected source-to-destination URL replacement.
6. **Missing dependency:** Markdown Documents was temporarily disabled only on dm. The preparation table requested activation; recovery stopped with a Japanese cause and next action. Activation was restored. Retrying the same point through 3 succeeded at `2026-11-01T10:09:43Z`.
7. **Focused regression:** `packages/markdown-m1/tests/recovery-usability.php` passed inside the dm fixture. Four write/retention/delete entry points were blocked with zero SDK calls; recovery UI write controls were absent; recovery remained available; Japanese/English preparation and a mismatched WordPress version were checked. Mutation rejection uses a fake SDK, while page listing uses real S3.
8. PHP 8.3 syntax checks passed for all five changed/new runtime files. PHP 8.1 syntax checks additionally passed for `Plugin.php` and `RecoveryPreparation.php`. `git diff --check` passed.

Two initial harness failures (missing admin template functions; a test variable colliding with WordPress's global locale) were corrected and rerun. They are not product success results. The final fixture is left with its required plugin active and a successful recovery record.

Local evidence: `D:/workspace/wp-rescue/release-readiness/usability-20261101/` contains before/after environment inventories, the focused result, comparison, and Japanese success/missing-dependency screenshots. Private account files and database/content backups are not committed.

## Still separate / 今回の完了とは区別する項目

This run verifies the existing configured environment, not a first-time AWS deployment or a new user's independent completion. It does not establish the `source-no-delete` sample policy alone, capacity beyond the bounded tests below, elapsed long-term scheduling or a full integration/version matrix. These remain explicit follow-up checks before promoting a new release. The current candidate Plugin Check is recorded below separately from the submitted result.

Submitted rc.6 SHA-256 remains `e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3`.

## Additional operations checks / 規模・途中中断・定期運用

Executed on the same community/dm fixtures on November 1. Synthetic posts were inserted into the dedicated source tables; this tests Baseline capacity, not 256 ordinary editor saves. One inert TXT attachment was enlarged between stages. Real S3 reads/writes used the existing configuration. No object/version deletion or IAM edits were performed.

| Added posts / attachment | Capture | Restore | Capture / restore PHP peak |
|---|---:|---:|---:|
| 32 / 1 MiB | 5.628 s | 2.569 s | 62.5 / 60.5 MiB |
| 128 / 8 MiB | 17.073 s | 7.682 s | 78.5 / 76.5 MiB |
| 256 / 24 MiB | 33.767 s | 16.547 s | 117.4 / 118.7 MiB |

All three stages matched the ordered test-post title/body/status digest and attachment SHA-256 between source and destination. The largest point contained 529 resources. Existing original posts, histories and earlier S3 points were retained. Capture used the source's 256 MiB PHP limit; restore used the destination's existing 128 MiB limit. These are CLI core-operation timings, excluding WordPress bootstrap, not browser/proxy timeout tests. The last stage has little headroom at 128 MiB and does not establish an unlimited or production capacity claim.

**Forced interruption:** only the dedicated PHP process received SIGKILL. On dm, the trigger was the first post INSERT after the transactional DELETE statements. The 32-post database rolled back unchanged, while the attachment had already become the new 8 MiB file. A retry of the same point restored all 128 posts and matched both digests. An interrupted destination must remain private until a successful retry and content check. The UI previously lacked a next action for a running/unconfirmed attempt; it now explains checking that the previous process has stopped and retrying the same point/history boundary. The Japanese and English guides agree. The kill test invokes the core restore method; the admin status renderer is checked separately by regression assertions.

On community, a delegating test SDK wrapper killed only its PHP process after the third real S3 PutObject, before manifest publication. The discoverable point references stayed exactly unchanged; a fresh capture then succeeded in 35.816 seconds with 529 resources. Partial resource objects are left in the test prefix; this test deliberately does not delete them.

**Scheduled operation:** a due weekly slot was set in the isolated fixture and executed through its actual `wp-cron.php`. A complete independent point was created, the next slot was reserved, and replaying the same slot returned `already_confirmed: true`. A second due run with synthetic pending history stopped with the expected pending-operation error, created no new point and reserved the next slot. Original config, pending state and cron option were restored. Automatic cleanup stayed disabled. This is an accelerated dispatch/retry check, not weeks/months of elapsed operation or deletion testing.

**Plugin Check 2.1.0:** final candidate runtime and maintained package documents checked on community: **0 errors, 107 warnings**, unchanged in count from the prior submitted check. Categories: direct database queries 34, uncached queries 32, metadata query performance 30, input sanitization heuristics 5, nonce heuristics 3, error logging 2, Japanese root Markdown filename 1. These warnings remain; a zero-error result does not mean warning-free or WordPress.org approval. No blanket suppression was added. The tool was deactivated after checking.

Focused regression passed on dm, including new Japanese/English unconfirmed-attempt instructions, existing recovery-only write guards and real S3 listing. PHP syntax and diff whitespace checks passed. Evidence and isolated harnesses: `D:/workspace/wp-rescue/release-readiness/operations-20261101/`. Submitted rc.6, tags and main remain unchanged; these are working-branch results.

## Browser completion check / 管理画面からの完了確認 — 2026-11-02 JST

Tested commit `1d6f0be` through the existing public HTTPS routes to the isolated community/dm sites, using Chrome and the existing guide operator accounts. Both operations were submitted by clicking the actual Japanese admin buttons; no CLI capture/restore was substituted. Server and proxy timeout settings were not increased.

- **Community:** checked the trusted-site/editing-paused confirmation and clicked **最初の保存を作成**. The 256 synthetic articles and 24 MiB TXT fixture produced a new 529-resource Baseline through history 3. Its manifest time was `2026-11-01T18:43:20Z` (November 2, 03:43:20 JST), key `site-snapshots/0abc36a309cd23ebfe56b8e48f80c2bb686ef01ffad0599e003be24daaf833f8/manifest.json`, version `n2rmDUM1i8qMIOy_O6j3FY8ATNzG.cBg`. The admin POST returned HTTP 302 and its result-page GET returned HTTP 200. The request-start timestamps were about 36 seconds apart; this is an approximate HTTP turnaround, not a precise profiler measurement.
- **Dm:** first preserved only the synthetic TXT file in the fixture's private temporary directory, so recovery would actually write the 24 MiB asset instead of merely reusing it. Selected the newly created point and history 3, confirmed destination replacement, and clicked **サイト全体を復旧**. The page reported **成功**, the exact same manifest/version, requested/applied history 3, 262 post records and **1 file written** at `2026-11-01T18:44:10Z` (03:44:10 JST). The POST returned HTTP 302 and result-page GET HTTP 200, with approximately 21 seconds between request-start timestamps.
- Read-only post-operation comparison matched all 256 synthetic article title/body/status values and the attachment's 25,165,824 bytes / SHA-256 `c38d2e95982aef0a387477869ed79d2df511f8ce81ccc516128e40e6371240c9` between source and destination.
- Neither application request timed out or displayed a PHP fatal error. Browser automation occasionally timed out while reading a navigating tab; the application HTTP results and final rendered screen independently confirmed completion. No product correction was needed for this run.

Evidence: `D:/workspace/wp-rescue/release-readiness/browser-20261102/` contains the rendered DOM records, recovery success screenshot, HTTP records and source/target comparison inputs. The preserved TXT fixture remains outside the web root. This establishes browser completion at the tested size and existing configuration; it does not establish a general maximum site size. No production content, submitted ZIP, tags or main branch were changed. The submitted rc.6 SHA-256 was checked again and remains unchanged.
