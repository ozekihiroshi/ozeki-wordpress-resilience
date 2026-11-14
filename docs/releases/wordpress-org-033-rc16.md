# 0.3.3 rc.16 — 履歴一覧の表示修正・公開候補

2026-11-14。**rc.16はGitHub公開候補でWordPress.org未提出です。提出済みrc.15は審査担当者の回答待ちで、公開承認済みではありません。** 本番サイトはrc.15のままです。

## 変更と互換性

記事用title／statusを持たない閲覧条件などの履歴にも、表示専用の補完処理を適用します。既存値・空欄は保持し、不足した状態は公開・非公開と推測せず「未記録」と表示します。閲覧条件には日英の名称を付けます。閲覧条件の記録を補助的なMarkdown復旧へ渡す判定漏れも防止しました。これらの記録はサイト全体の復旧で扱います。

**rc.15から保存形式の変更・移行はありません。** 既存原本・履歴を書き換えず読み取ります。rc.15で導入した画像関連記録には対応readerが必要という条件は継続します。[修正理由と再発確認](history-display-20261114.md) / [更新手順](../../packages/markdown-m1/docs/install-update.md)。

## 完成ZIP

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.16/ozeki-resilience-0.3.3.zip) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.16) / [リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.16)
- SHA-256: `c5f98640b96fd85c47404d8bddab235efc0387e0e04bfd78131d120a488184ae`
- 8,300,208 bytes / 3,816 files。rc.15との差分は製品PHP1ファイルと説明4ファイル。依存ライブラリ変更・削除ファイルなし。
- 固定Gitソースアーカイブと製品40ファイルを照合。同梱8ガイド・相対リンク86件を確認。開発資料・試験コードを配布ZIPに含めません。

## 完成ZIPによる確認

- Plugin Check **2.2.0：エラー0／警告102**。同じcheckerでrc.15もエラー0／警告102で、警告コード別件数は同じです。警告ゼロを意味しません。
- communityホスト上の使い捨てWordPress **7.0 / PHP 8.3.31**。本番とは別DB・内部ネットワーク、公開ポート・本番マウント・AWS認証情報なし。CPU・メモリ制限あり。メール・Cron・自動更新停止。終了後に専用コンテナ・ネットワークを削除。
- 新規導入・有効化とrc.15からの更新に成功。全3,816配置ファイルがZIPと一致し、余剰ファイルなし。更新前後の既存データ・設定・有効化状態のハッシュ一致を確認。保護オン、定期保存・自動削除オフを保持。
- 新規導入・更新の両方で、9種類×4条件（title/statusあり・欠落・null・空欄）の36件を日英で表示。PHP警告なし、既存の記録済み値とエスケープを保持、履歴ファイルのハッシュ不変、再読取り結果一致。閲覧条件の個別Markdown復旧を拒否。
- 日英の初期設定案内、復旧準備の契約確認も通過。
- 導入・更新はWP-CLI、画面はPHPによる実際の管理画面描画です。履歴は隔離環境の合成フィクスチャで、実S3や本番履歴の再試験ではありません。今回の変更は表示と補助的復旧の判定であり、保存形式や通常のサイト全体復旧処理には変更がありません。

[ZIP監査](../../evidence-public/wordpress-org-033-rc16/package-audit.json) / [ソース一致](../../evidence-public/wordpress-org-033-rc16/source-match.json) / [Plugin Check](../../evidence-public/wordpress-org-033-rc16/plugin-check.json) / [警告比較](../../evidence-public/wordpress-org-033-rc16/plugin-check-comparison.json) / [導入・更新](../../evidence-public/wordpress-org-033-rc16/validation.json)

## 保全

本番サイト・既存S3原本と履歴・研究側の未コミット変更には手を加えていません。提出済みrc.15 ZIPはSHA-256 `5f8ce491ec286f3e84f3667ceaddc5416ac0febad81441d8fc3bca601ea6e4eb` のままです。既存ZIP・タグを保持し、rc.16を別タグとして公開します。WordPress.orgへの送信・審査メール返信は未実施です。

## Supplementary explanation (not sent)

Ozeki Resilience 0.3.3 rc.16 — update to the existing application

This candidate retains the prior review-response fixes and corrects the history display for records without article title/status attributes, including file-access records. English and Japanese displays preserve existing values and use read-only fallbacks for missing metadata. File-access records are rejected by the supplementary Markdown recovery paths and remain handled by complete site recovery.

No recording format change, migration or rewrite is introduced relative to rc.15. Existing S3 originals and formal history remain unchanged. The rc.15-compatible reader requirement for media records continues to apply. Recovery never deploys archived WordPress, theme or plugin code.

ZIP SHA-256: c5f98640b96fd85c47404d8bddab235efc0387e0e04bfd78131d120a488184ae
Source: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.16
Verification: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc16.md

The exact ZIP passed Plugin Check 2.2.0 (0 errors, 102 warnings; unchanged warning-code counts from rc.15), isolated fresh installation and upgrade from rc.15, full installed-file/source checks, state preservation, and English/Japanese history rendering for 36 fixture records. Existing fixture history remained unchanged.
