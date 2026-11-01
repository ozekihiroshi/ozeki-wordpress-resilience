# WordPress.org 0.3.3 rc.7 — recovery preparation and usability

**Prepared on November 2, 2026; not submitted to WordPress.org.** The previously submitted rc.6 and review-email reply remain awaiting the reviewer response. Publication is not approved. Submitted ZIPs and existing tags are preserved.

## 今回の向上 / Improvements

- 復旧先では保存・保持変更・削除を禁止し、不要な操作ボタンを表示しません。S3へ送る前にも書込み操作を拒否します。
- 復旧ポイントに記録されたWordPress・プラグインの版と、復旧先に入っている版を比較し、次に必要な操作を示します。テーマ情報は再導入の参考です。
- 日英で不足条件・失敗理由・中断後の再実行方法を案内し、前回の復旧ポイントと履歴番号を保持します。
- 導入・復旧ガイドを現行動作に揃えました。保存形式、既存S3資産、実行ソフトウェアを管理者が別途準備する方針は変更していません。

Recovery destinations reject S3 mutations before SDK calls and hide writer controls. The screen compares recorded and installed software versions, provides Japanese/English next actions, and retains the last recovery selection. Guides clarify separate recovery URLs, attachment coverage, new Baselines for untracked changes and interrupted recovery retries. These changes do not add an installer or change stored data formats.

## Artifact

- [Installable ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.7/ozeki-resilience-0.3.3.zip)
- [Matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.7)
- Candidate **0.3.3 rc.7**; WordPress plugin header/stable tag **0.3.3**.
- **8,282,477 bytes / 3,813 files**.
- SHA-256: `b8e2d8d8961463da42f223990461f29ff7a3546212f459983ec1ebec0d307b58`
- [Package audit](../../evidence-public/wordpress-org-033-rc7/package-audit.json): product files match source; 3,776 vendor files match rc.6; eight bundled guides; no development scripts/tests/tools in the ZIP.

## Verification

- [Final ZIP validation](../../evidence-public/wordpress-org-033-rc7/validation.json): new isolated site on community, WordPress 7.1.3/PHP 8.3.36, installed with the WordPress upgrader via WP-CLI, activated and rendered its unconfigured admin screen. All 3,813 installed files matched the ZIP.
- Existing community source and dm recovery fixtures were privately backed up, installed from the exact submitted rc.6 ZIP, then updated through the WordPress upgrader to rc.7. Settings, pending-state options, recovery-attempt/result options and post counts matched before/after; all 3,813 files matched on each site. Pending queues were empty; this is not a new nonempty-queue migration test.
- Focused regression passed on dm after installing the final ZIP: recovery-only S3 mutation guards, hidden writer controls, Japanese/English requirements and interruption guidance, missing WordPress version guidance, and real-S3 point listing.
- [Plugin Check 2.1.0](../../evidence-public/wordpress-org-033-rc7/plugin-check.json) against the newly installed ZIP: **0 errors / 107 warnings**. Warnings remain documented, unchanged in count; this is not approval or a warning-free claim.
- [Operational and browser evidence](recovery-usability-20261101.md): the same runtime was tested with real S3 on community/dm for 32/128/256 synthetic posts and 1/8/24 MiB attachments, process interruption/retry, accelerated scheduled dispatch/duplicate prevention, and actual admin-browser capture/recovery. The final packaging changes only README status and changelog. Largest browser run completed without timeout; content and attachment hashes matched.
- Capacity beyond the tested size and elapsed long-term operation remain outside these results. The current implementation has no new capacity guarantee. No production content or IAM configuration was changed.

Submitted rc.6 SHA-256 is still `e7ca01f16903945bbf67d6e6254f5e2f6a8e28afa7fced586675df55556e22b3`. Research worktree changes are preserved. The public main branch includes the reviewed usability work; archival/research assets remain available in their branches and Git history.

## Submission note draft — not sent

Ozeki Resilience is intended for incidents where the original WordPress environment can no longer be trusted. Its purpose is to preserve supported information independently so that publishing and service can resume on a fresh WordPress, alongside existing backup arrangements. This leads to three principles: preserve independent information assets; install executable software separately from trusted distributors; apply only recognized content/settings rules instead of blindly importing the old environment. Recovery does not deploy or execute archived theme/plugin code. Standard Posts and Pages need no additional plugin; integrations require their compatible runtime separately. Independent originals and recovery points deliberately provide redundancy rather than minimizing storage or restoration time.

0.3.3 rc.7 updates the existing application with recovery-destination write/delete guards, recorded software version guidance and clearer Japanese/English failure and interruption instructions. Software is still installed separately from trusted sources; recovery imports supported information assets. Stored data formats are unchanged. The exact ZIP passed fresh installation and rc.6-to-rc.7 update checks on isolated WordPress sites. Plugin Check 2.1.0: 0 errors / 107 documented warnings. Real-S3 and admin-browser save/recovery checks passed at the recorded test sizes. Package SHA-256: b8e2d8d8961463da42f223990461f29ff7a3546212f459983ec1ebec0d307b58.

## Explanation update after packaging — 2026-11-02

The main-branch README (Japanese/English), WordPress readme and setup/recovery guide now explain the purpose and principles before the mechanics. They clarify preparedness and redundancy, separately supplied software, selective application and optional integrations. Runtime code is unchanged. These wording changes are **not in the already-built rc.7 ZIP or tag**; prepare a new candidate containing them before submission. The hash and validation above still describe the unchanged rc.7 artifact. The expanded submission-note draft above has not been sent.
