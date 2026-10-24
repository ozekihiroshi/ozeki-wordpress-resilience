# Native article details — 0.3.1 final ZIP validation

## Result
Fresh installation and overwrite update from the unchanged combined-final 0.3.1 ZIP passed in two isolated namespaces in existing dm Docker. Activation/bootstrap and ZIP extraction were tested; browser Plugin_Upgrader was not tested.

Settings, restore-result records, asset identities, trial content/comments, membership credentials/settings, form/inquiry state, TablePress data/settings, frozen pending queues and existing Cron configuration were preserved. Real S3 history remained 37 records, SHA256 a98c1ef7cc0c93df2b299956fe4dff3e900f73acd3b46167258dd43a8b3fc760. Default SDK EC2 role used; no S3 writes or IAM changes.

Both installations restored the existing complete Checkpoint through33 and confirmed history through37. Deleted article/comment absent; featured-image ID, bytes and rendered image, category/tag IDs matched. Recovery imported23 posts and10 files per destination. Source DB/queues were not recovery inputs. Mail attempts0. All3812 installed ZIP files matched before/after recovery. Final documentation-only heading correction was applied to both installations and bytes/results rechecked; executable code unchanged.

Checkpoint/comments/forms/membership/TablePress/capture/cleanup/upload-guard/native-state/frozen-resource queue contracts passed against final ZIP code. Failure injection uses in-memory S3, not an AWS outage. Existing live dm probe hashes unchanged. No live content modifications, mail, scheduled execution or formal publication.

## Product scope and limitations
Native Post/Page permanent deletion, thumbnail set/replace/remove and category/tag assignment/removal now replay through site-wide recovery. This adapter captures successful operation state at request end; standard body S3-first saving is unchanged. Frozen resource retry does not reread a changed attachment. Deletion cleanup includes revisions/comments/relations and child reparenting.

Global taxonomy administration, arbitrary metadata/taxonomies, menu/front-page/sticky deletion side effects, standalone media deletion/binary overwrite and same-asset concurrency remain excluded. Pre-enqueue process loss is not guaranteed. Only confirmed formal history is recoverable. No new browser-click acceptance is claimed.

## Environment / test infrastructure
Standalone tests initially referenced repository-relative src paths; harness copies were corrected to load ZIP source, then passed. No product correction was needed during packaging. Existing duplicate DISABLE_WP_CRON warning in the live probe is environment configuration, distinct from product behavior. Unused DB prefix was verified with read-only SQL before installation. Windows git cannot resolve this WSL worktree metadata; WSL git diff checking passed.

## 日本語
新規導入・旧combined-final ZIPからの更新で、設定・履歴37件・保留データと試験コンテンツの保持を確認しました。両方で既存S3のCheckpoint33＋履歴37から復旧し、完全削除・アイキャッチのバイト列と表示・カテゴリー／タグを照合しました。本文のS3先行保存と、追加属性の操作成功後保存は区別します。分類そのものの管理、任意メタデータ、メニュー等の削除連動は対象外です。試験の相対パス修正と環境のCron重複警告は製品修正ではありません。既存コンテンツ・メール・定期実行・正式公開は変更していません。

ZIP SHA-256: `602cefdd40e2def981a9b550bc3a6aa5d264c01d6b9bec96e1e6e1d19d2329dc`
