# Administrator activation — browser acceptance

## Result

Fresh standard WordPress login succeeded on both existing isolated trial sites
(source community and recovery destination dm) using their unchanged administrator
credentials. Initial destination failure is retained in the
[native browser acceptance](native-details-browser-acceptance.md).

## Cause and responsibility

The combined-test fixture enabled WP-Members moderated registration but activated
only its subscriber, leaving the pre-existing trial administrators without `active`.
Read-only inspection found `mod_reg=1` and missing administrator activation on both
sites. WP-Members 3.5.8.1 checks activation at backend login, including administrators.
An already authenticated source session concealed this condition.

The recovery adapter restores global WP-Members settings and subscriber accounts;
it preserves destination administrators. Code inspection found no administrator
activation removal. Restoring moderation exposed a destination preparation omission,
not corruption of recovered content or S3 resources. The product documentation had
an important gap: retaining an administrator account does not guarantee login under
restored membership settings. Automatic administrator activation is not implemented.

## Targeted correction and checks

- Only the explicitly authorized isolated trial administrator on each site received
  `active=1`, guarded by exact database prefix, account ID, role and previous state.
- No password reset, role change, moderation disablement or authentication bypass.
  Direct metadata insertion avoided notification/history hooks.
- Before/after comparisons matched all other user rows and metadata, article records,
  WP-Members settings and the administrator credential row on each site.
- Chrome standard `wp-login.php` accepted the existing credentials and reached
  `wp-admin/` on each site. Source used explicit reauthentication. Normal login
  creates its own session; session creation is not a password or role change.
- Existing mail blocker and disabled Cron remained. No existing member/content,
  live-root site, IAM, product code or verified ZIP was changed. No mail sending,
  scheduled execution or formal release was performed.

Local evidence: `release-readiness/admin-activation-20261024/` contains source and
 destination before/after probes and dashboard screenshots. Credentials, tokens and
 private probes are deliberately not included in this repository.

## Operator instructions

English/Japanese root and package READMEs, the
[WP-Members checklist](../../packages/markdown-m1/docs/members.md#administrator-access-during-setup-and-recovery)
and [site recovery guide](../../packages/markdown-m1/docs/site-snapshot.md) now require:
source administrator activation at setup, designated destination administrator
activation before moderated recovery, and fresh standard login after recovery.
Do not approve unrelated members or disable moderation to satisfy this check.

The tested ZIP remains unchanged; these instructions apply to its existing behavior.
Its embedded documentation has not been rebuilt. Trial theme thumbnail support,
CRLF shell filenames and WSL sandbox access were separate test/tooling issues.
No additional recovery run was needed to diagnose and correct administrator access.

## 日本語

原因は同居試験で会員承認制を有効にした際、既存の試験管理者を有効化していなかったことです。
復旧で承認設定が再現され、未有効化の管理者が拒否されました。管理者情報の消失やS3破損ではありません。
両サイトの対象試験管理者だけを有効化し、既存パスワードで標準管理画面へ再ログインできました。
他会員・記事・承認制・管理者認証情報は比較で不変を確認しました。
製品コード修正ではなく試験準備の修正と、導入・復旧手順の不足の補完です。
既存セッションではなく新たな認証で確認し、一般会員の一括承認や承認制の解除は行いません。
検証済みZIPは変更せず、メール送信・定期実行・正式公開も行っていません。
