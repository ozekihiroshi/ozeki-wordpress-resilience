# 不具合受付・通知の運用記録 / Support operations

確認日 / Checked: 2026-10-28 JST。管理者 / Maintainer account: `ozekihiroshi`。

## 受付先・確認結果 / Routes and verified settings

- [GitHub Issues（日英テンプレート）](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues/new/choose)：選択画面・本文・プレビューを確認済み。
- GitHubの **Watch → Custom → Issues** を有効化し、保存後のチェック状態を確認済み。
- [GitHub通知設定](https://github.com/settings/notifications)の **Participating, @mentions and custom** は **on GitHub / Email** がともに有効。Watchingも同じ配信設定。
- WordPress.orgは **審査待ち（Awaiting Review）**。公開承認済みではありません。

The Japanese/English GitHub templates were checked in the chooser, editor and preview. **Watch → Custom → Issues** is enabled and was verified after saving. GitHub notification settings enable both **on GitHub** and **Email** for custom subscriptions and Watching. WordPress.org status remains **Awaiting Review**, not approved or published.

## WordPress.org公開後に行うこと / After WordPress.org publication

1. 公開されたプラグインページの **Support** を開き、管理者アカウントでログインします。
2. **Subscribe to this plugin** をクリックし、新規トピックのメール購読を承認します。
3. **Unsubscribe from this plugin** に変わったことを確認し、本記録に設定日を追記します。

この購読はまだ未設定です。公開申請の審査通知やGitHubのWatch設定では代替されません。

After publication, open **Support** from the published plugin page while signed in, select **Subscribe to this plugin**, and confirm email subscription to new topics. Verify that it changes to **Unsubscribe from this plugin** and record the date here. **This subscription is still pending**; review emails and GitHub Watch do not replace it.

## 運用 / Operations

- 不具合は日英テンプレートで受付。質問にはBlank issueも使用できます。公開の報告に認証情報や非公開データを含めないよう案内しています。
- GitHubとWordPress.orgに同じ報告がある場合は相互リンクし、修正の追跡はGitHub Issuesにまとめます。WordPress.orgの審査メールは利用者サポートとは別です。
- 通知設定は管理者アカウントごとの設定です。担当者を追加・変更した際は、各担当者が購読とメールの受信先を確認します。
- 確認用Issue・トピックは投稿していません。通知設定の確認であり、実際のメール到着テストは実施していません。コード・ZIP・タグは変更していません。

Bug reports use the Japanese or English template; questions may use a blank issue. Keep credentials and private data out of public reports. Cross-link duplicate reports between GitHub and WordPress.org, and track fixes in GitHub Issues. Plugin review emails are separate from user support. Subscriptions are per account: each new maintainer should check subscriptions and email delivery. No test issues/topics were posted or email delivery tests performed. Code, ZIPs and tags were unchanged.
