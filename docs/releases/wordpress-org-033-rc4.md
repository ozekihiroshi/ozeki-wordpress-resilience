# WordPress.org 0.3.3 rc.4 — review-response candidate

Status: **superseded, not submitted; do not submit this candidate**. The startup-failure handling was incomplete. Use the [rc.5 candidate](wordpress-org-033-rc5.md). Publication has not been approved. The submitted rc.3 ZIP and all existing tags remain unchanged. ZIP upload and reply in the original review thread require the user's final go-ahead.

## 審査指摘への対応

| 指摘 | 対応 |
|---|---|
| S3から実行コードを復旧先へ配置 | 除外。ソフトウェアは信頼できる配布元から事前導入し、情報資産を復旧する。 |
| 不要なBAT・Pythonファイル | 配布対象から除外。 |
| AI生成と思われる開発資料 | 維持する利用文書の明示リストだけを同梱。開発資料はGitHubに残す。 |
| 復旧先をWP_CONTENT_DIRに固定 | wp_upload_dir()の保存先を使用。独自アップロード先とURLを隔離確認。 |
| 短いowr接頭辞 | WordPress上の設定・メタデータ・hook・管理画面登録・nonce等をozeki_resilience系に変更。旧設定と予約を自動移行。 |

こちらで必要な修正と確認を終えた状態であり、審査担当者の承認を意味しません。

## Identifier migration / 識別名の移行

- Settings, pending queues, protection state, post/member recovery mappings and Checkpoint schedules are migrated before capture hooks start. Existing current-name values take precedence; conflicting legacy rows are retained without being used. Failures stop initialization and remain retryable. Repeated migration does not replay pending operations.
- 設定値・未完了キューの内容はそのまま引き継ぎます。旧名が残るのは移行用の対応表・旧予約の解除・旧原本の読み取り／除外規則です。旧名でのWordPress登録や新しい設定書込みはしません。
- S3 schemas such as `owr-md-history-1` and history discriminators such as `owr_comment` are archive-format values, not WordPress hook/option/post-type registrations. Existing originals, Checkpoints and formal history are neither renamed nor rewritten. Old archive metadata is translated only in the destination projection.
- The administrator opens **Tools → Resilience** (`tools.php?page=ozeki-resilience`). Any custom integration that used the old S3-client filter must use `ozeki_resilience_m1_s3_options`; old hooks are not re-registered. Standard installations require no manual database edit or new Baseline for this rename.

## Checks / 確認

[Evidence](../../evidence-public/wordpress-org-033-rc4/validation.json), [Plugin Check](../../evidence-public/wordpress-org-033-rc4/plugin-check.json), [contracts](../../evidence-public/wordpress-org-033-rc4/contract-checks.json), [package audit](../../evidence-public/wordpress-org-033-rc4/package-audit.json).

- WordPress 7.1.3 / PHP 8.3.35 / MariaDB / WP_DEBUG enabled, disposable containers and local simulated S3. Existing sites and real AWS were not changed.
- Fresh installation, protection start, Japanese rendering; information-asset recovery with independently installed Markdown Documents, CF7, Flamingo and TablePress; ACF free readiness.
- Submitted 0.3.3 rc.3 → candidate: settings, queues, posts, recovery results and history retained; post/member mapping and scheduled time preserved; no old hook registration or duplicate old schedule; protected saving continues.
- Partial migration failure and retry, repeated migration, and preservation of already-current values passed. An intermediate build also passed the submitted 0.3.2 update path; its separate result is retained.
- Old Checkpoint plus formal history restored with new metadata identifiers, unchanged S3 objects and destination software. PHP syntax and 29 standalone contracts passed.
- Plugin Check 2.1.0: **0 errors / 104 warnings**, all recorded. A metadata-key warning in the identifier helper concerns local array projection, not an unbounded database query. The prepared identifier SQL produced no unescaped-parameter warning.
- Final packaging corrects only the Japanese and English README submission notices after the runtime-tested ZIP. Every runtime/dependency file is byte-identical to that tested ZIP; all packaged product files match the worktree. This distinction is recorded with both hashes rather than representing the two archives as identical.

## ZIP

Candidate: **0.3.3 rc.4** (plugin header remains 0.3.3), 8,312,336 bytes / 3,822 files.

SHA-256: `726e2024b5bd5f8b05dda188e4394de4fedbf8f9070bff6f478ab38984e91d30`

Runtime-tested ZIP SHA-256: `5c7bae3a2f0413e34522f09e11cf22cc189cc591042c87bea0735c2c26c0019b`.

Submitted rc.3 remains `066c4ae4f47f943a8b7cb4fa31efd6e256ad47772bdb1f4bd99c22a39804973e`.

## Upload note draft — not sent

0.3.3 rc.4 addresses the additional review of rc.3: recovery imports information assets only; software is installed separately from trusted distributors. WordPress identifiers use the ozeki_resilience prefix with migration of existing settings, mappings and schedules. Development artifacts are excluded and custom upload paths are supported. Isolated installation, update and recovery checks passed; Plugin Check reported 0 errors / 104 recorded warnings. Candidate SHA-256: 726e2024b5bd5f8b05dda188e4394de4fedbf8f9070bff6f478ab38984e91d30.

## Reply draft — send in the original review thread after upload

Thank you for the additional review. The revised package removes archived theme/plugin code installation; recovery now imports information assets into WordPress with trusted software installed separately by the administrator.

Active WordPress identifiers now use the ozeki_resilience prefix, with automatic migration of existing settings, metadata and scheduled events. Old names remain only for migration and reading archived data, not active WordPress registrations. The other packaging and directory-location findings have also been addressed, and installation, update and recovery were tested in isolation with WP_DEBUG enabled.

Validation: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc4.md

Regards,
Hiroshi Ozeki
