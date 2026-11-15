# Current distribution status / 現行版の配布状況

**0.3.3 rc.18 is a GitHub release candidate. It has not been submitted to WordPress.org. Submitted rc.16 is awaiting the reviewer response; publication has not been approved.**

**0.3.3 rc.18はGitHub公開候補で、WordPress.orgには未提出です。提出済みrc.16は審査担当者の回答待ちで、公開承認済みではありません。**

- [Installable ZIP / 導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.18/ozeki-resilience-0.3.3.zip)
- [Matching source / 対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.18)
- [Verification / 確認記録](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc18.md)
- SHA-256: eadc9ec4de01f06014414a9bb709b11905019e525fdbdc918f45d3626d2f2d97

Recovery does not install or initialize plugins. Prepare trusted software and complete its normal setup first. WP-Members recovery retains prepared runtime settings/schema versions and applies supported information. rc.17 also preserves registered attachment originals, previews, metadata and access conditions together. New attachment recovery points require rc.17 or a compatible later reader; rc.16 rejects them. Do not resume saving or cleanup with an older version after using the new format. Existing originals/history are not rewritten. Missing originals in older points are reported as incomplete.

復旧処理はプラグインのインストール・初期化を行いません。信頼できるソフトウェアを事前に導入・セットアップし、WP-Membersの準備済み動作設定・版情報を維持して対応情報を戻します。rc.17は添付原本・付随画像・添付情報・閲覧条件を一組で保全します。新しい添付復旧点にはrc.17以降の対応版が必要で、rc.16は拒否します。新形式を使った後に旧版で保存・整理を続けないでください。既存原本・履歴は書き換えず、旧復旧点の原本不足は未完了として報告します。

Use the installable ZIP, not GitHub source archives. See [updating](install-update.md), [setup](user-guide.md) / [導入ガイド](user-guide-ja.md).
Previous submission: [rc.16 record / 提出済みrc.16の記録](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc16.md).
rc.18 also retains prepared TablePress global settings, destination theme CSS and widget configurations; unverifiable placements are held for review. No new recording format is introduced.

rc.18ではTablePress全体設定・復旧先の追加CSS・ウィジェット本体設定も維持し、照合できない配置は保留します。新しい記録形式の追加はありません。
