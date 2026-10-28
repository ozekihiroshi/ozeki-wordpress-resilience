# Combined recovery scope — 0.3.1

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

The combined final ZIP contains the CF7 upload-guard correction. One real-S3 complete Checkpoint through 21 and formal history through 29 recovered Posts/Pages, images, comments, CF7 definitions, Flamingo receipts, WP-Members and TablePress together. Bodies, links, image bytes, moderation, fields, member login/access restriction and table rendering were compared. This was PHP API integration; separate TablePress browser acceptance covered add/update/delete, search, sorting and pagination. Optional plugins are installed separately.

Only the exact CF7 uploads/wpcf7_uploads/.htaccess deny-all content is accepted (LF or CRLF). Other control/executable files remain rejected. No protection file is removed or weakened.

Confirmed history defines the recovery boundary. Adapter writes after WordPress completion are not S3-first article interception. Unconfirmed operations are not recovery candidates. This acceptance does not cover arbitrary plugins, premium modules, concurrent same-asset changes, mail transport or scheduled execution. New Markdown editing was not repeated in the combined test.

The inherited trial content URL mismatch and browser proxy/JavaScript setup were test-infrastructure issues, distinct from the product guard-file rejection. Existing dm memory limits were retained. No mail replay, IAM changes or formal release.

## 日本語

一つのCheckpoint（履歴21まで）と後続履歴29までから、投稿・固定ページ・画像・コメント・CF7・Flamingo・WP-Members・TablePressをまとめて復旧し、本文・リンク・画像・状態・関連情報・会員ログインと閲覧制限・表を照合しました。通常のPHP APIによる同居検証と、別途行ったTablePressのブラウザ検証を区別します。

CF7の既知のアクセス拒否ファイルだけを完全一致で許可する製品修正です。試験URL設定の修正とは別です。任意のプラグイン、有料拡張、同じ資産の同時更新、未確定履歴、メール送信、定期実行は今回の保証範囲を広げません。
