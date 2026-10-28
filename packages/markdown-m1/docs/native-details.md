# Native article details and deletion

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

Included in the 0.3.1 native-details-final candidate. Prior combined-final ZIP remains unchanged.

For published or already-protected standard Posts/Pages, successful permanent deletion and the final request state of featured-image selection/removal and category/tag assignment/removal are recorded as complete `native-state-json` originals in the shared S3 formal history. Standard post/body saving retains its existing S3-first behavior. These additional operations are post-success capture, not pre-write interception. New category definitions and their ancestors needed by an assignment are included.

The adapter reuses the durable pending queue. Thumbnail originals and generated sizes are frozen with metadata before enqueueing; S3 resource writes and the complete state record must succeed before history confirmation. Retry uses the frozen bytes and fixed operation keys, not the current attachment. A lost PUT response is reconciled. Individual files retain the existing 32 MiB limit; the encoded resource queue has a 128 MiB operation ceiling. Capture failure before durable enqueueing is not a confirmed operation; inspect errors. Process loss before request-end capture and concurrent same-asset changes remain outside guarantees.

Site-wide replay applies thumbnails and native taxonomy relations, recalculates category/tag counts, and removes deleted articles, revisions, associated metadata/comments/relationships and stored HTML. Child records move to the saved parent's parent. Unrelated content remains in the recovery state. Missing parents/images or identity conflicts fail rather than silently accepting an inconsistent operation. Individual text recovery refuses these detail records.

Scope does not extend to global term rename/delete administration, arbitrary taxonomies, featured-image binary overwrites, standalone media-library deletion, menu-link cleanup, sticky-post/front-page option changes or arbitrary plugin metadata. After such changes, create a new trusted baseline. Removing an article from WordPress does not delete retained S3 objects.

## Actual integration

Existing isolated TablePress/combined trial namespaces were reused on community and dm (`wp-backup.ceri.link` host). The pre-existing trial article 21 received category/tag assignments and image selection; new disposable article 33/comment 3 were used for deletion. No live site's existing content was edited.

- Shared S3 history 30–33: thumbnail/category/tag state, disposable article and comment; independent complete Checkpoint through 33.
- Tail 34–37: thumbnail/tag removal, thumbnail replacement and new tag/category assignment, comment deletion and permanent article deletion.
- Product recovery from that Checkpoint plus tail through 37 on dm: deleted article/comment absent, thumbnail ID/bytes/rendering, category/tag IDs match; zero mail attempts.
- Source DB/local queue are not recovery inputs; expected fixture is assertions only. Existing live dm probe hashes unchanged.
- Regression contracts cover removal/counts, revisions, unrelated preservation, repeat/identity rejection and frozen-resource failed write/resume/lost response/no duplication. Failure injection uses an in-memory S3 double, not a forced AWS outage.

Tests use normal WordPress PHP APIs and request-end callbacks. Browser clicks were not an additional acceptance in this task. No new infrastructure, IAM, mail, scheduler or formal release. Existing duplicate DISABLE_WP_CRON probe warning is environmental; no new environment failure was observed.

## 日本語

通常投稿・固定ページの完全削除、アイキャッチの設定／差替え／解除、カテゴリー・タグの割当て／解除を、操作成功後の確定データとして共通S3履歴へ接続しました。本文の既存S3先行保存は維持します。新規カテゴリーの親階層と必要な画像資産も保存します。正式履歴未確定の操作は復旧に採用しません。

実S3のCheckpoint33と後続履歴37からdmの専用試験WordPressへ復旧し、削除結果・画像バイト列と表示・分類を照合しました。ブラウザ操作ではなくWordPress標準APIによる検証です。分類そのものの名称変更／削除管理、メニュー・固定表示設定の削除連動、任意メタデータは対象外です。既存の実サイトコンテンツ・メール・定期実行は変更せず、今回のnative-details-final候補に収録します。
