# Current distribution status / 現行版の配布状況

## 日本語

新しいGitHub公開候補は **0.3.3 rc.13（WordPress.org未提出）** です。Flamingoの復旧時の受信値欠落を修正し、rc.12までの修正も含みます。**提出済みrc.12は審査担当者の回答待ちであり、公開承認済みではありません。** 以前のZIP・タグは保全しています。

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.13/ozeki-resilience-0.3.3.zip) / [リリース説明](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.13) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.13)
- SHA-256: `34eee728e5c6d78f6e8368256d60676a0df7085e8a35ed343f787afd2898c2b8`
- [確認結果・申請準備記録](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc13.md)

既存のFlamingo受信原本の移行は不要です。欠落した状態で再保存した受信は、値が残る以前の原本から復旧します。復旧先にも更新版を用意してください。rc.12で導入した参照情報を持つ復旧点にはrc.12以降の対応readerが必要です。S3原本・履歴は書き換えません。[導入ガイド](user-guide-ja.md)・[更新手順](install-update.md)を参照してください。GitHubのSource code (zip)は導入用ZIPではありません。

## English

The new GitHub candidate is **0.3.3 rc.13 (not yet submitted to WordPress.org)**. It fixes missing Flamingo receipt values during recovery and includes the earlier fixes. **Submitted rc.12 remains awaiting the reviewer response; publication is not approved.** Earlier ZIPs and tags remain unchanged.

- [Installable ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.13/ozeki-resilience-0.3.3.zip) / [Release notes](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.13) / [Matching source](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.13)
- SHA-256: `34eee728e5c6d78f6e8368256d60676a0df7085e8a35ed343f787afd2898c2b8`
- [Verification and submission preparation](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc13.md)

Existing Flamingo receipt originals need no migration. Receipts already re-saved with missing values require an earlier original that still holds them. Update recovery destinations too. Recovery points containing the reference context introduced in rc.12 require rc.12 or a later compatible reader. Existing S3 originals/history are not rewritten. Follow the [setup guide](user-guide.md) and [update procedure](install-update.md). Use the installable ZIP, not GitHub's source archive.
