# WordPress.org 0.3.3 rc.5 — startup-failure correction

**Documentation follow-up:** The bundled guides still directed readers to earlier ZIPs. GitHub guidance has since been corrected; repackage those corrections before submission. The recorded rc.5 ZIP remains unchanged and must not be treated as matching the updated guides. [Current distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

**Prepared, not submitted.** This replaces the unsubmitted rc.4 candidate, which must not be submitted. The submitted rc.3 ZIP and existing tags remain unchanged. Publication has not been approved. No upload or email reply has been sent for rc.5.

## 修正した不具合

rc.4では、設定名の移行に失敗すると起動中の例外が公開ページ・管理画面まで停止させる問題がありました。従来の試験は移行処理を直接呼んで例外を受け止めており、WordPress全体の起動経路を確認していませんでした。

rc.5は起動時に移行失敗を受け止めます。失敗中は通常の保護・復旧・定期処理を登録せず、公開閲覧と管理者ログインを維持します。保存要求を503で止め、管理者には日英の案内と「再試行」を表示します。原因を解消した次の要求で移行を再試行し、成功後に通常動作へ戻ります。保護設定をオフにする処理や、未完了キューを消す処理はありません。

WordPressが閲覧中にナビゲーションを自動作成する経路も実HTTP試験で検出しました。失敗中だけ標準のwp_navigation_should_create_fallbackを無効にし、既存データを書き換えず表示を継続します。

## Verification

[Exact ZIP validation](../../evidence-public/wordpress-org-033-rc5/validation.json), [startup failure checks](../../evidence-public/wordpress-org-033-rc5/startup-failure.json), [Plugin Check](../../evidence-public/wordpress-org-033-rc5/plugin-check.json), [package audit](../../evidence-public/wordpress-org-033-rc5/package-audit.json).

- Disposable WordPress 7.1.3 / PHP 8.3.35 / MariaDB with WP_DEBUG; local simulated S3. No production site or real AWS changes.
- Actual wp-load failure injection, not a catch around a direct migration call: database write failure and a separate connection holding the migration lock are both contained.
- Public HTTP page returns 200. Administrator sign-in succeeds; Tools → Resilience returns 200 with English/Japanese retry instructions.
- POST requests to comments, AJAX, admin-post, REST posts and CF7 feedback return 503. REST method override and CLI post creation are blocked too. Content, metadata, configuration and synthetic pending queues remain equal before/after failed startup.
- Removing the injected fault allows automatic retry; the migration completion marker is saved and protected article saving creates confirmed history again.
- Fresh ZIP installation, submitted rc.3 update, identifier/metadata/schedule migration, information-asset recovery from old Checkpoints and formal history, destination software preservation, custom uploads and ACF free readiness all pass.
- Plugin Check 2.1.0: **0 errors / 107 warnings**. Three added warnings refer to reading the request action in the failure guard without a nonce. That read only selects refusal or the normal core login path; it does not authorize a write. Login credentials and authentication checks remain with WordPress. All warnings are retained for review.
- The final ZIP is exactly the runtime-tested ZIP, without post-test content changes; packaged product files match source. Previous packaging exclusions remain in effect.

## ZIP

Candidate: **0.3.3 rc.5**; plugin header remains 0.3.3. 8,315,296 bytes / 3,823 files.

SHA-256: `83bbcad02d026bd1b2151fc8fea386669164fe4ee04d175f3b4082c9f88b2015`

Submitted rc.3 remains `066c4ae4f47f943a8b7cb4fa31efd6e256ad47772bdb1f4bd99c22a39804973e`.

The five review findings and identifier compatibility are covered by the [previous response record](wordpress-org-033-rc4.md); rc.5 adds the startup correction above. rc.4 is retained solely as an unsubmitted historical record.

## Upload note draft — not sent

0.3.3 rc.5 addresses the additional rc.3 review. Archived software installation has been removed; WordPress identifiers are migrated to ozeki_resilience names; development artifacts are excluded and custom upload paths are supported. A failed local migration preserves page viewing and administrator sign-in while pausing saves with retry guidance. Isolated installation, update, recovery and actual startup-failure checks passed. Plugin Check: 0 errors / 107 recorded warnings. SHA-256: 83bbcad02d026bd1b2151fc8fea386669164fe4ee04d175f3b4082c9f88b2015.

## Reply draft — original review thread, after upload

Thank you for the additional review. The revised package removes archived theme/plugin code installation; recovery imports information assets into WordPress with trusted software installed separately by the administrator.

Active WordPress identifiers now use the ozeki_resilience prefix with migration of existing settings, metadata and scheduled events. Old names remain only for migration and archived data, not active WordPress registrations. Packaging and directory-location findings are also addressed. Installation, update, recovery and failure during startup were tested with WP_DEBUG enabled.

Validation: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc5.md

Regards,
Hiroshi Ozeki
