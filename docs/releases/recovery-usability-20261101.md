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

This run verifies the existing configured environment, not a first-time AWS deployment or a new user's independent completion. It does not establish the `source-no-delete` sample policy alone, large-site capacity, long-term scheduling, abrupt process-kill recovery, a full integration/version matrix or a new official Plugin Check result. These remain explicit follow-up checks before promoting a new release. The previous submitted Plugin Check result is not represented as a check of this candidate.

Submitted rc.6 SHA-256 remains `e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3`.
