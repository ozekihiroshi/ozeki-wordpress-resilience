# Current distribution status / 現行版の配布状況

**0.3.3 rc.22: update accepted and original review email answered on 2026-11-24. Awaiting reviewer response; NOT approved for publication. Not deployed to production.**

**0.3.3 rc.22は2026-11-24に更新受付・審査メール返信が完了しました。審査担当者の回答待ちであり、公開承認済みではありません。本番未導入です。**

[rc.22 submission and verification / 申請・確認記録](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/review/core-updates-20261124/RC22-PACKAGE.ja.md) / [Matching source / 対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/c7053f559de3e245465eec4466688ea5a684ba3c/packages/markdown-m1).

SHA-256: `59db41d96e210e892c2a0cf53f85d5d581436a2d86a84d362986d852249fbeba`

rc.22 requires the same candidate on the healthy source and prepared destination and a new trusted Baseline. Prerelease saved-data compatibility is not guaranteed; existing originals/history are not rewritten.

rc.22では健全な保存元と復旧先を同じ候補に揃え、新しい初回保存を作成します。公開前候補間の保存データ互換性は保証しません。既存原本・履歴は書き換えません。

## Previous rc.21 distribution / 以前のrc.21配布記録

**0.3.3 rc.21: update accepted by WordPress.org and original review email answered on 2026-11-24. Awaiting reviewer response; NOT approved for publication. The same ZIP is deployed to community.**

**0.3.3 rc.21は2026-11-24に更新受付・審査メールへの返信が完了しました。審査担当者の回答待ちであり、公開承認済みではありません。同じZIPをcommunity本番へ導入済みです。**

- [Candidate ZIP / 候補ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.21/ozeki-resilience-0.3.3.zip)
- [Matching source / 対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.21)
- [Verification and scope / 確認結果と範囲](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc21.md)
- SHA-256: `ec0b5cbedd7855054d87ef5656ffcfbde25335c25d4e939b0291d73acf0874de`

rc.21 preserves prepared destination templates/navigation, checks embedded Markdown document viewing conditions and avoids unnecessary media reconciliation during autosave. Prepare trusted software and complete normal setup before recovery; recovery does not install or initialize plugins. Archive formats and existing originals/history are unchanged. Update recovery destinations too. Previously textified embeds require their original or an explicit administrator reference edit.

rc.21は準備済みテンプレート・ナビゲーションを維持し、Markdown埋込み先文書自身の閲覧条件を確認します。自動保存時の不要な添付再照合も修正します。信頼できるソフトウェアを事前に導入・セットアップし、復旧処理はインストール・初期化を行いません。原本・履歴・保存形式は変わりません。復旧先も更新してください。以前に文字化した埋込みは原本から復旧するか、管理者が正しい参照を設定します。

Use the installable ZIP, not GitHub source archives. See [updating](install-update.md), [setup](user-guide.md) / [導入ガイド](user-guide-ja.md).

[Submitted rc.20 / 提出済みrc.20](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc20.md) / [Community rc.20 operation record / 本番更新・保存・日英履歴77件](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/operations/community-rc20-20261124.md). Existing ZIPs and tags remain unchanged / 既存ZIP・タグは変更していません。
