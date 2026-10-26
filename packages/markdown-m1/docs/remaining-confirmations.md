# Remaining confirmations / 残る確認事項

2026-10-26. This is a tracked boundary, not a request to add features or rerun completed tests. 確認済みと未確認の境界を記録する。

| Item / 項目 | Type and state / 種類・状態 | Next distinct confirmation / 次の差分と完了条件 |
|---|---|---|
| Actual deployment trigger / 通常環境の起動方法 | Existing-feature verification; server-invoked standard wp-cron.php verified / 既存機能検証。標準入口のサーバ起動は確認済み | Reference selected: server-invoked standard wp-cron.php; existing dispatch/next-slot evidence reused. HTTP loopback only needs verification if chosen. / 基準はサーバから標準wp-cron.php起動。実行・次回予約の既存証拠を使用。HTTP方式は採用する場合だけ確認 |
| Interrupted deletion / 削除途中の失敗 | Existing-feature verification; real deletion followed by injected interruption and retained-point recovery verified / 既存機能検証。実削除後の試験遮断と保持点復旧は確認済み | [Result / 結果](recovery-readiness.md): one real deletion, second request blocked before transmission, no later calls; not an actual AWS outage. / 実削除1件後に2件目を送信前遮断、後続処理なし。実AWS障害ではない |
| Long-term recurrence and natural expiry / 長期反復・自然期限経過 | Operational observation; calendar/overlap rules tested separately / 運用観察。日時計算・重複規則の試験は別途確認済み | Accumulate results under actual schedules. Do not block all development waiting a year or claim accelerated fixtures were a year-long run. / 実運用の結果を蓄積。年単位の待機を全作業の停止条件にしない |
| Lock behaviour in deployed AWS / 実AWSでのロック条件 | Environment conditions plus bounded verification; locked deletion not accepted / 環境条件と限定検証。保護中の実削除は未検証 | Confirm actual lock/Legal Hold explains blocked candidates; never bypass as an acceptance objective. / 保留理由との整合を確認し、回避成功を目的にしない |
| First-time user instructions / 初回利用者の導線 | Browser installation → Baseline → native update/history → separate recovery verified with existing roles, after supplying the Markdown dependency / Markdown依存を補い既存ロールで一連の操作を検証済み | [Evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/user-guide-onboarding.md). Prerequisite and upload-limit guidance corrected; not an unassisted-guide acceptance or exact IAM-template deployment. No repeat of the successful recovery is required solely for this wording change. / 前提・容量案内を修正。補助なしの受入やIAM JSON新規適用は未確認。文言修正だけのために成功済み復旧を繰り返さない |

The candidate's installation/update evidence is inherited by pre.2 because executable/vendor entries are identical; the current guide does not expand that evidence. Standard-admin cleanup, scheduled capture/cleanup, failure-injected skip and retained-point recovery were confirmed in [PR52 evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/e87ba0b38898331252098d17bc16f649f5a16252/docs/releases/cleanup-browser-scheduled-acceptance.md). Unchanged-source capture and independent complete points are not new development items.

pre.2の導入更新は実行コード・vendor同一の候補の証拠を引き継ぎ、このガイドによって検証範囲を広げない。管理画面の削除・定期取得／削除・失敗注入による削除抑止・残存基点復旧は確認済み。更新なしの独立取得を再び未実装課題にしない。

IAM restrictions, IMDS reachability, runtime versions, disk/memory limits and unrelated core-update jobs belong to environment preparation. Loss of required recovery resources or false success reporting would be product issues. Environment setup must not be solved by silently weakening confirmation or deletion rules. Unknown/unsupported information and content outside the defined capture scope remain limitations, not automatic feature commitments.

IAM、IMDS到達性、実行環境の版、容量・メモリ、本体更新ジョブは環境準備の問題。必要資源の喪失・成功誤報なら製品課題。環境都合で確定・削除条件を弱めない。未対応情報を無条件に追加機能の約束へ変えない。

Reference trigger: server invocation of standard wp-cron.php, using existing acceptance evidence. Exact IAM-template deployment and active-lock verification remain environment-dependent; see [current evidence](recovery-readiness.md).

基準の起動方式は検証済みの標準wp-cron.phpのサーバ起動。IAM完全版の実適用と実ロック有効時の確認は環境条件が未解決。[今回の記録](recovery-readiness-ja.md)を参照。
