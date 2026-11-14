# 0.3.3 rc.15 — 閲覧条件の継続と互換性確認

2026-11-14。**rc.15の既存申請への更新受付と元の審査メールへの返信が完了しました。審査担当者の回答待ちで、公開承認済みではありません。** 管理者による手動アップロードの受付・メール送信完了の報告に基づき更新しました。

## 変更と互換性

未対応プラグインが混在する場合の対応データ保全、英語初期設定の復旧、初回保存・日常保存の閲覧条件の引継ぎを改善しました。ページの会員制限とファイルの制限を区別し、非公開・条件不明のファイルを公開配置しません。保留した原本も再保存・再復旧に引き継ぎます。

復旧先にはrc.15対応readerを用意してください。新形式の原本と復旧点は旧readerが拒否します。既存原本・正式履歴は書き換えず読み取れますが、閲覧条件を記録していない旧ファイルは保留します。保存元を更新したら「ファイルの閲覧条件を再確認・記録」を実行し、正式履歴への確定を確認します。非公開ファイルのダウンロード配信機能を追加したものではありません。

[適用契約と互換性](../../packages/markdown-m1/docs/media-access-contract.md) / [更新手順](../../packages/markdown-m1/docs/install-update.md)

## 完成ZIPの確認

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.15/ozeki-resilience-0.3.3.zip) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.15) / [リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.3-rc.15)
- SHA-256: `5f8ce491ec286f3e84f3667ceaddc5416ac0febad81441d8fc3bca601ea6e4eb`
- 8,299,696 bytes / 3,816 files。Gitのソースアーカイブと製品40ファイルを照合。LinuxとWSLのビルドで同じハッシュ。依存ライブラリ変更なし。同梱8ガイド・相対リンク86件を確認し、開発資料・試験コードの混入なし。
- Plugin Check **2.2.0：エラー0／警告102**。同じcheckerでrc.14はエラー0／警告100。追加2警告は閲覧条件を直接DBから取得する固定SQLの直接読取りとキャッシュ不使用です。利用者入力をSQLへ挿入せず、古い閲覧条件を使わないため最新値を取得します。
- 初回チェックの内部例外メッセージ指摘は、管理画面出力時のエスケープを確認して、その境界を示す注釈を追加。動作変更なし。最終ZIPで再実行しました。
- dmの使い捨てWordPress 7.1.3 / PHP 8.3.36、専用DB・内部ネットワーク、公開ポートなし。AWS実認証情報なし、メール・Cron停止。
- 新規導入とrc.14からの更新に成功。配置3,816ファイルがZIPと一致し、余剰なし。既存データ・設定・有効化状態・保護オンを保持、定期保存・自動削除オフを維持。日英画面描画・復旧準備の契約確認に成功。
- 導入・更新はWP-CLI、画面確認はPHP描画です。ブラウザからのZIPアップロードや最終ZIPによる実S3往復を確認したという意味ではありません。

[ZIP監査](../../evidence-public/wordpress-org-033-rc15/package-audit.json) / [ソース一致](../../evidence-public/wordpress-org-033-rc15/source-match.json) / [Plugin Check](../../evidence-public/wordpress-org-033-rc15/plugin-check.json) / [警告比較](../../evidence-public/wordpress-org-033-rc15/plugin-check-comparison.json) / [導入・更新](../../evidence-public/wordpress-org-033-rc15/validation.json)

## 既存の実S3確認との関係

[実S3確認記録](../../packages/markdown-m1/docs/media-access-live-verification-20261114.md)では、同じ機能コードで保存・復旧後の利用・再保存・再復旧、旧形式読取り、実際の旧readerによる新形式拒否を確認済みです。これはソースを重ねた隔離試験であり、完成ZIP確認とは区別します。その後の差分は説明と上記の静的解析注釈です。

## 保全と提出状況

本番サイトには変更していません。既存原本・履歴、研究側の未コミット変更、既存ZIP・タグを保全しました。提出済みrc.14 ZIPのSHA-256は `453acc6930d57da11da72eaba5adf9c386d0d79aa179cfd15b12b82ad0ba5a2a` のままです。rc.15は管理者が手動でアップロードし、受付と元の審査メールへの返信完了を報告しました。今回変更したのはmainの説明文書とGitHubリリースの説明だけです。提出済みZIPとタグ内の文書は提出時のまま保全しています。

## Supplementary explanation for the submitted rc.15 update

Ozeki Resilience 0.3.3 rc.15 — update to the existing application

This candidate retains the earlier review-response fixes. It records file access conditions consistently in initial capture and daily history, including condition-only changes. Page membership restrictions are treated separately from direct file access. Public supported images remain usable, while unresolved media originals are retained without public placement through resaving and repeated recovery.

Existing S3 originals and formal history are not rewritten. New media originals and recovery points require the rc.15-compatible recovery reader; actual older readers reject them. Legacy files without recorded access conditions remain readable but are held rather than published. Administrators update recovery destinations too, and record current file access conditions on the source after updating.

Recovery still uses trusted WordPress, themes and plugins installed separately by the administrator. It does not deploy archived software.

The exact ZIP passed Plugin Check 2.2.0 with 0 errors and 102 warnings, isolated fresh installation and upgrade from rc.14, full file/source checks, state preservation and English/Japanese administration rendering. Two additional warnings versus rc.14 concern a fixed uncached database read of current access conditions. The same functional code previously passed isolated real-S3 save/recover/resave/recover and actual-old-reader compatibility checks; that trial preceded packaging and is recorded separately.

ZIP SHA-256: 5f8ce491ec286f3e84f3667ceaddc5416ac0febad81441d8fc3bca601ea6e4eb
Source: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.15
Checks: https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-033-rc15.md
