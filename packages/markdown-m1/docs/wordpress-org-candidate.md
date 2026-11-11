# Current distribution status / 現行版の配布状況

## 日本語

新しいGitHub公開候補は **0.3.3 rc.12（WordPress.org未提出）** です。TablePressの復旧先に必要な安全な設定値を用意し、未編集Markdownを含む参照関係を再保存・再復旧へ引き継ぎます。

**提出済みrc.11は審査担当者の回答待ちであり、公開承認済みではありません。** rc.11を含む以前のZIP・タグはそのまま保全しています。

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.12/ozeki-resilience-0.3.3.zip)
- [リリース説明](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.12) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.12)
- SHA-256: `8084a992fb593a65ca239fc8dc5b30b01061237424d768f106a2d1c63788ac6b`
- [確認結果・申請準備記録](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc12.md)

既存原本は更新版で読めます。新しい参照情報を含む原本・Baseline・Checkpointの復旧にはrc.12以降の対応版を用意してください。rc.11は新形式を読み取り時に拒否します。S3の既存原本・履歴は書き換えません。[導入ガイド](user-guide-ja.md)・[更新手順](install-update.md)を参照してください。GitHubの `Source code (zip)` は導入用ZIPではありません。

## English

The new GitHub candidate is **0.3.3 rc.12 (not submitted to WordPress.org)**. It supplies safe TablePress runtime defaults and preserves reference relationships across resaving and repeated recovery, including untouched Markdown.

**Submitted rc.11 remains awaiting the reviewer response; publication is not approved.** Earlier ZIPs and tags, including rc.11, remain unchanged.

- [Installable ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.12/ozeki-resilience-0.3.3.zip)
- [Release notes](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.12) / [Matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.12)
- SHA-256: `8084a992fb593a65ca239fc8dc5b30b01061237424d768f106a2d1c63788ac6b`
- [Verification and submission preparation](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc12.md)

Existing originals remain readable. New originals, Baselines and Checkpoints containing reference context require rc.12 or a later compatible reader; rc.11 rejects the new format during reading. Existing S3 originals and history are not rewritten. Follow the [setup guide](user-guide.md) and [update procedure](install-update.md). Use the installable ZIP, not GitHub's source archive.