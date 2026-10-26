# GFSロック設定なし対応・最終配布候補（2026-10-26）

- 作業の種類：配布物作成・導入更新の差分検証・文書整理。
- 状態：検証済み・制限あり。未公開。
- 完了条件：新規導入・更新、設定／履歴保持、最終ZIPとの全件一致、英日説明とハッシュ記録。達成。
- 製品完成への寄与：任意の削除保護が未設定の固定版も正しく保持評価できる修正を導入可能にする。

## 配布物

ファイル：ozeki-wordpress-resilience-0.3.1-gfs-lock-read.zip
SHA-256：8b14e94666e733cdc5018dbb4bdb4e7877ca9d91e3360f837d20877cece0a168
サイズ：7447608 bytes。3,829 files。表示版0.3.1だけでなくファイル名とハッシュで識別する。

前回GFS候補との製品コード差分はsrc/Store.phpのみ。残りは英日README・GFS文書・導入案内。vendor全件は公開済みZIPと同一。ZIP内相対リンク検査・ソース一致・破損検査に合格。

## 検証結果・境界

1. ZIP内コードでunset-object-lock/site-retention/checkpoint-lifecycleの3差分試験に合格。既存依存試験も同時実行。メモリS3による設定なし・拒否・通信失敗・版の不在・その他404・HEAD失敗の試験であり、実AWS障害／実削除の試験ではない。
2. 既存dm Docker本体・DBを再利用し、別テーブルowrunsetzip_20261026_fresh_/upgrade_、別コンテンツ/tmp/owr-unset-lock-final-20261026/で新規導入と公開済みv0.3.1-pre.1からの更新に合格。GFS/S3設定、未実行予約、合成未確定操作2件、失敗理由、個別／全体復旧結果、試験記事を保持。合成キューは再開してはならない。
3. 標準認証で既存実S3正式履歴1件のハッシュと原本SHA-256一致を確認。S3読取りのみ。新規履歴書込み・再開・復旧の再実行は今回不要で未実施。
4. 最終ZIP配置後の再起動確認も合格。新規・更新両配置の全3,829ファイルが最終ZIPと一致。既存サイトの前後probe一致、メール0、Cron実行なし、自動更新停止。
5. 実S3プレビューで保持3点・資源12件・候補4件・全版一覧不変を確認したのは先行unset-lock-20261026/RESULT-ja.mdの試験。今回のZIP試験とは区別。候補は現時刻を試験用基準にした結果であり、保持設定変更ではない。実管理画面への配備／ブラウザ操作は未実施。

DISABLE_WP_CRON already defined警告は既存共有設定と試験起動の重複で、検証合格とは別に記録。新たな製品課題として取り込まない。

削除拒否維持、実削除・IAM変更・既存S3資産／会員／コンテンツ変更なし。公開済みZIP913bac85cb704f24edaaa76d793222d5b25676eef0ad87543b102c7d1933762f、前回GFS ZIP88367d9c9b1fd3e201fb1066ca7e6695122915fb9e892b57ae7cce0ff11e3829は不変。リリース公開なし。

証拠：install-result.txt、final-install-result.txt、zip-contract-results.json、build-result.json（開発領域release-readiness/unset-lock-final-20261026）。配置用send.shは実行済み、再実行しない。
