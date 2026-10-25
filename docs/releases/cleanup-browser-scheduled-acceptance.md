# Complete-site cleanup: browser and scheduled acceptance / サイト全体削除の画面・定期実行確認

## Work and boundary / 作業と範囲

Existing-feature verification and evidence organization; verified with limitations. Completion is standard-admin deletion, scheduled capture/cleanup, failed capture skipping cleanup, and recovery from a retained scheduled point. This checks preservation of usable independent recovery resources, not a new retention design.

作業は既存機能の検証・エビデンス整理。状態は検証済み・制限あり。完了条件は標準管理画面からの削除、設定時刻の取得・削除、取得失敗時の削除抑止、残した定期Checkpointからの復旧。独立した復旧資源を失わないという製品目的を確認した。

The 2026-10-26 trial reused community/dm containers, existing isolated source/target tables and content, and the disposable `delete-validation-20261026/` prefix. Standard AWS SDK EC2-role credentials were used. No IAM, live content, old S3 prefix, product code or published ZIP changes. A dedicated admin entrance, scoped SDK logging/fault guard, disabled updates/mail and isolated Cron queue were test arrangements, not product dependencies.

既存の隔離テーブル・コンテンツと専用使い捨てprefixだけを再利用した。認証はSDK標準EC2ロール。IAM・実サイト・旧S3範囲・製品コード・公開済みZIPは変更していない。専用管理画面入口、範囲制限付き通信記録／失敗注入、更新・メール抑止と隔離Cronキューは試験準備であり、製品の追加依存ではない。

## Observed results / 確認結果

| Route / 経路 | Result / 結果 |
|---|---|
| Standard Tools → Resilience / 標準管理画面 | Created a complete point through history 2; preview retained 14 versions and listed 17 candidates. Checkbox confirmation and deletion returned success, exactly 17 deleted. All 13 retained resources passed exact-version readback. / 履歴2までの一式作成後、保持14版・候補17版を確認し、確認チェックと削除で17版削除。保持13資源の固定版照合に成功。 |
| Scheduled 08:44 JST / 設定時刻 | Unchanged independent 13-resource point verified and confirmed; cleanup succeeded with zero deletions, retaining the prior boundary point; next weekly reservation registered. / 更新なしの独立13資源を照合・確定。削除0件で直前の基点も保持、次回予約成立。 |
| Scheduled 08:47 JST / 設定時刻 | Another independent point through 2; cleanup deleted the older unlabelled point's 14 versions and retained both active weekly points (28 versions). / 独立した履歴2までの一式を作成し、古い無区分基点14版を削除。有効な週次2点・28版を保持。 |
| Recovery on dm / dm復旧 | Latest scheduled Checkpoint alone restored body, title, publish state, image bytes and relocated links through history 2; no deleted ancestor or source DB used. / 定期取得した最新Checkpointだけで本文・タイトル・公開状態・画像・リンクを再現。削除済み祖先・元DBを不使用。 |

The first zero-delete result was conservative retention, not evidence of actual deletion; the later slot supplied that missing evidence. No timestamps were forged. Weekly settings were changed through the browser to near-future real times. After each due time, the existing server invoked unmodified `wp-cron.php` with only the isolated product event queue, rather than calling the product callback directly. This does not test HTTP loopback or weeks of unattended operation.

最初の削除0件は安全側の保持結果で、実削除の証拠ではないため、次の予定で古い無区分基点の削除を確認した。時刻改変はしていない。ブラウザで近い将来の実時刻を設定し、予定到来後、隔離した製品イベントだけを標準wp-cron.phpから実行した。製品コールバックの直接呼出しではないが、HTTPループバックや数週間の無人運転を検証したものではない。

## Limits and package identity / 制限と配布物

The objects had no Object Lock retention/Legal Hold. No bypass, locked deletion, interrupted deletion or natural monthly/yearly expiry was tested. The zero-day history window deliberately makes obsolete test points eligible; active weekly labels still preserve their points. The earlier [Checkpoint plus subsequent-history recovery](deletion-recovery-acceptance.md) remains separate: this trial absorbed history 2 into a new point before removing those obsolete history objects.

対象は削除保護・Legal Hold設定なし。ロック回避、保護中の削除、削除途中停止、自然な月次・年次期限経過は未検証。試験用の履歴保存期間0日で古い基点を候補にしたが、有効な週次区分は保持した。[先行するCheckpoint＋後続履歴の復旧](deletion-recovery-acceptance.md)とは別で、今回は履歴2を新基点へ取り込んでから旧履歴資産を削除した。

Executed source matches the unpublished candidate `ozeki-wordpress-resilience-0.3.1-gfs-lock-read.zip`, SHA-256 `8b14e94666e733cdc5018dbb4bdb4e7877ca9d91e3360f837d20877cece0a168`. This documentation change does not rebuild or publish a ZIP. [Installation/update evidence](unset-lock-final-m1-031.md) is separate. Local evidence: `release-readiness/cleanup-completion-20261026/` (credentials excluded).

実行コードは上記未公開候補と同一。今回は文書のみでZIP再作成・公開なし。[導入更新の記録](unset-lock-final-m1-031.md)は別試験。試験用資格情報は証拠文書に収録しない。

## Failed capture and cleanup suppression / 取得失敗時の削除抑止

At the real 08:50 JST slot, the scoped test guard rejected the first Checkpoint PUT before transmission. The product recorded `ok:false` and `Trial injected Checkpoint PUT failure`, did not confirm a manifest or call deletion, and booked the next weekly occurrence. Cleanup status remained the earlier 08:47 success record, not a new success for the failed run. Inventory remained exactly the same 28 Key/VersionId pairs; source content/member table hash was unchanged. The browser showed the failure and next reservation. This is injected failure, not an observed AWS outage. Injection was removed and test scheduling/automatic cleanup disabled at completion.

実時刻08:50 JSTの予定で、専用試験ガードが最初のCheckpoint PUTを送信前に拒否した。製品は失敗と具体的理由を記録し、マニフェスト確定・削除を行わず次週を予約した。削除結果は08:47の過去の成功記録のままで、失敗した回の成功ではない。28版のKey/VersionId一覧と元側のコンテンツ・会員テーブルハッシュは不変。画面でも失敗と次回予定を確認した。実AWS障害ではなく失敗注入である。終了後に注入を解除し、試験予約・自動削除を停止した。

An early test-runner invocation stopped at its own “Not due” guard before dispatch; running after the actual scheduled time succeeded. This was a test-runner timing mistake, not a product failure. No product correction or automatic retry mechanism was introduced.

予定前の試験ランナー呼出し一回は自身のNot dueガードで停止し、実時刻到来後に実行した。試験操作の時刻判断の問題であり、製品不具合ではない。製品修正や自動再試行機構の追加はしていない。
