# 0.3.3 rc.2 公開準備記録

2026-10-28 JST。**未送信**。WordPress.orgでは0.3.2 rc.1が審査待ちです。

## rc.1からの追加

- 準備画面にACF無料版の基本フィールドを追加。PROは「保護対象外」、未使用は「対応不要」、既存定義があり無料版が無効なら有効化と初期保存を案内。
- 完了した初期保存にACF無料版の版を記録。現在の版・保存先と一致しない場合は新しい初期保存を案内し、新たな保護開始時に確認。古い保存を自動で確認済みにはしない。
- 有効な既存の記事保護は維持。PROを理由に記事保護を止めない。定義変更時の初期保存は引き続き利用者の操作で行う。
- 日英の説明・回帰試験を整合。

## 候補

- Ozeki Resilience / slug ozeki-resilience / contributor ozekihiroshi
- Version 0.3.3 / tag wporg-0.3.3-rc.2
- ozeki-resilience-0.3.3.zip / 7,467,808 bytes / 3,859 files
- SHA-256 `e080912fc512c7963d741e7ea25d62da398deb42cc6c279d3cade4f9032a0d70`
- [補足説明案](../../evidence-public/wordpress-org-033-rc2/submission-draft.txt)
- [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.2/packages/markdown-m1)

## 検証

[最終ZIP](../../evidence-public/wordpress-org-033-rc2/validation.json)：隔離WordPress7.1.3 / PHP8.3.35 / MariaDB / 模擬S3で、新規導入・初期保存・保護開始、0.3.2 rc.1からの更新、設定・履歴・未完了記録・復旧結果の保持、保存継続が成功。配置ファイルとZIPが全件一致。

実ACF無料版6.8.10で、古い初期保存を未確認とし、新しい保存後に現在の版を確認済みとする遷移を確認。日英HTML表示も確認。PRO・未使用・無効化・版変更・保存先変更・新規開始時の判定はローカル契約試験で確認。ブラウザー操作・実AWS・PRO製品本体・ACF全サイト復旧の新規試験を行ったものではありません。

公式Plugin Check2.1.0：**0 errors / 117 warnings**。[全件](../../evidence-public/wordpress-org-033-rc2/plugin-check.json)。[静的確認](../../evidence-public/wordpress-org-033-rc2/static-validation.json)：製品ソースと一致、依存ライブラリ3,785ファイルは提出済み0.3.2と同一。

0.3.3 rc.1・0.3.2 rc.1・0.3.1 rc.2のZIPとタグは不変。既存サイトや元の未コミット作業は変更していません。管理者による候補確認後、既存申請を更新します。
