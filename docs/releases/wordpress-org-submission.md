# WordPress.org申請内容 — Ozeki Resilience 0.2.0

2026-10-26 JST。GitHub公開済み、WordPress.org申請は未送信。
これは送信前の入力用資料です。WordPress.orgのログイン後フォームへの入力・同意チェック・アップロード・送信は行っていません。実際のフォーム項目はログイン後に確認します。補足欄がない場合、英語の審査説明は追加資料または審査メールへの回答用に使用します。

## 提出する値

| 項目 | 内容 |
| --- | --- |
| 申請アカウント／Contributors | `ozekihiroshi` |
| Plugin Name | `Ozeki Resilience` |
| 希望slug | `ozeki-resilience`（予約・確定は未実施） |
| Version / Stable tag | `0.2.0` |
| Requires at least | `6.8` |
| Tested up to | `7.1`（今回の確認環境は7.1.3） |
| Requires PHP | `8.1`（今回のZIP導入環境は8.3.35） |
| License | `GPLv2 or later` / `GPL-2.0-or-later` |
| Tags | `backup, recovery, amazon s3` |
| 提出ZIP | `ozeki-resilience-0.2.0.zip`、63,540 bytes |
| 作者 | `Hiroshi Ozeki` |

氏名・版・要件などはZIP内のヘッダー/readmeに設定済みです。全項目が申請フォームの独立した入力欄とは限りません。連絡先メールは申請アカウントに登録されたものを使用し、この資料では推測していません。

**短い説明（readmeと同一）：**

> Save supported content to immutable S3 generations before applying it to WordPress; reconstruct it with a separately configured worker.

## 審査担当者が取得できる配布物

- [申請候補リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.2.0-rc.1)
- [提出するプラグインZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.2.0-rc.1/ozeki-resilience-0.2.0.zip)
- [対応する外部キット](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.2.0-rc.1/owr-development-kit-0.2.0.zip)
- [固定ソースコミット](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/bbe3440c368ef96de58b27703180f06c1d5e6e1c)
- [同じコミットのソースZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/archive/bbe3440c368ef96de58b27703180f06c1d5e6e1c.zip)（参照用。WordPressへの導入用ではありません）
- [導入条件](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/bbe3440c368ef96de58b27703180f06c1d5e6e1c/setup.txt)
- [確認結果・警告の判断](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/bbe3440c368ef96de58b27703180f06c1d5e6e1c/docs/releases/wordpress-org-checks.md)
- [SHA-256一覧](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.2.0-rc.1/SHA256SUMS)
- [最終ZIP検証記録](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.2.0-rc.1/validation.json)

WordPress.orgへ提出するのはプラグインZIPのみです。外部キットとGitHub自動生成ソースZIPは補足資料です。プラグインと外部キットは公開URLから認証なしでダウンロードし、検証済みSHA-256との一致を確認済みです。ZIP自体は再生成・変更していません。

```text
355c8ca843984088c706c80555faa45ee5350677ef85002504a799335fcb0219  ozeki-resilience-0.2.0.zip
2c7317684c42f8c6e1df43eff980bb32ddfdfb75d4d49f5197412f0d62e010f9  owr-development-kit-0.2.0.zip
```

## Reviewer notes — English text ready to use

Hello Plugins Team,

I am preparing Ozeki Resilience 0.2.0 for review under the requested slug `ozeki-resilience`. The WordPress.org contributor account is `ozekihiroshi`. The installable plugin is `ozeki-resilience-0.2.0.zip`; the separately downloadable operator kit is not a WordPress plugin ZIP.

The exact packaged source is commit `bbe3440c368ef96de58b27703180f06c1d5e6e1c`, also tagged `wporg-0.2.0-rc.1`. All review artifacts, hashes and setup instructions are publicly available here:
https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.2.0-rc.1

The plugin is the WordPress interface for an explicitly enrolled, operator-managed workflow. Supported posts/pages and PNG/JPEG images are committed to immutable S3 generations by a separate worker before being applied to WordPress. Activation alone does not configure storage or enable protection. The matching external runtime is provided in the release. Its current live-S3 adapter requires the dedicated SSH signing environment documented in setup.txt; it is not a generic AWS-account configuration wizard. The filesystem transport is only a test double. These dependencies and external-service data transfers are disclosed in readme.txt. No private credentials are needed to download or inspect the source or kit; exercising live S3 requires a compatible operator-provisioned environment.

Recovery restores saved post statuses, including `publish`, to an operator-prepared WordPress target. The plugin does not automatically isolate that target or configure DNS, TLS or public access; restored published posts can be visible immediately if the destination is accessible. Supported-content limits and unsupported integrations are documented. The older independently signed/research workflows included in the operator source kit are separate from the installable plugin's supported scope.

The frozen plugin ZIP passed installation, old-directory switching, reinstallation, settings/content preservation and installed-file hash comparisons. Plugin Check 2.1.0 static/runtime checks on WordPress 7.1.3 reported 0 errors and 61 warnings. The warning report and manual dispositions are included. In particular, specific native filesystem operations are retained for private local worker IPC because OS locks, permissions and atomic same-filesystem rename are part of its durability contract; narrowly scoped PHPCS annotations document these cases. No blanket security-check suppression was used. We do not claim that zero automated errors is approval or that historical live-S3 tests cover new untested environments.

The display name and distribution directory have changed from the GitHub preview to `Ozeki Resilience` / `ozeki-resilience`. The setup guide instructs operators to deactivate the old directory before activating the new one; existing option keys and external journals remain unchanged. This submission candidate is the specific 0.2.0 package linked above; other development/pre-release lines in the GitHub repository are not part of the submitted ZIP.

Thank you for reviewing the package and its disclosed external-runtime requirements.

## 公開状態と証拠の時点

GitHubの公開リリースは審査用候補として作成し、既存リリースやLatest指定を置き換えていません。ブランチ上の本申請資料はZIP確定後の文書追加であり、配布ソースは上記固定コミットのままです。

`validation.json`内の`remote_push: false`と、同梱文書内の公開前という記述は検証時点の記録です。今回の公開を理由に過去の証拠を書き換えていません。公開状態はリリースページおよび`evidence-public/wordpress-org-publication.json`で記録します。

[公式申請ページ](https://wordpress.org/plugins/developers/add/)ではログインが必要です。申請送信、slug確定、利用規約等への同意、審査承認はいずれも未実施です。
