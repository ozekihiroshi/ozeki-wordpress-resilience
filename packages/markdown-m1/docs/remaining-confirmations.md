# Remaining confirmations / 残る確認事項

2026-10-26. This is a tracked boundary, not a request to add features or rerun completed tests. 今回は記録のみで、追加実装・試験は行わない。

| Item / 項目 | Type and state / 種類・状態 | Next distinct confirmation / 次の差分と完了条件 |
|---|---|---|
| Actual deployment trigger / 通常環境の起動方法 | Existing-feature verification; server-invoked standard wp-cron.php verified / 既存機能検証。標準入口のサーバ起動は確認済み | Select the deployment's actual trigger and confirm it dispatches due work and books the next slot. HTTP loopback is unverified and only needed if chosen. / 採用する起動方法から実行・次回予約まで。使わないHTTP方式を埋めるだけの試験は不要 |
| Interrupted deletion / 削除途中の失敗 | Existing-feature verification; real S3 interruption unverified / 既存機能検証。実S3途中障害は未確認 | First inspect existing evidence, then if needed use disposable assets to confirm failure reporting, stop and retained-point recovery. No automatic resume/rollback feature is implied. / 既存証拠を絞って確認後、必要なら失敗・停止・保持点復旧を最小検証。自動再開・巻戻し追加は目的外 |
| Long-term recurrence and natural expiry / 長期反復・自然期限経過 | Operational observation; calendar/overlap rules tested separately / 運用観察。日時計算・重複規則の試験は別途確認済み | Accumulate results under actual schedules. Do not block all development waiting a year or claim accelerated fixtures were a year-long run. / 実運用の結果を蓄積。年単位の待機を全作業の停止条件にしない |
| Lock behaviour in deployed AWS / 実AWSでのロック条件 | Environment conditions plus bounded verification; locked deletion not accepted / 環境条件と限定検証。保護中の実削除は未検証 | Confirm actual lock/Legal Hold explains blocked candidates; never bypass as an acceptance objective. / 保留理由との整合を確認し、回避成功を目的にしない |
| First-time user instructions / 初回利用者の導線 | Documentation/static review only / 文書・静的確認のみ | When separately scheduled, use the guide with a representative permitted setup and note unclear steps. Templates have not been applied anew to AWS. / 別途実施時に代表構成で迷う手順を確認。JSONを新規適用済みとはしない |

The candidate's installation/update evidence is inherited by pre.2 because executable/vendor entries are identical; the current guide does not expand that evidence. Standard-admin cleanup, scheduled capture/cleanup, failure-injected skip and retained-point recovery were confirmed in [PR52 evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/e87ba0b38898331252098d17bc16f649f5a16252/docs/releases/cleanup-browser-scheduled-acceptance.md). Unchanged-source capture and independent complete points are not new development items.

pre.2の導入更新は実行コード・vendor同一の候補の証拠を引き継ぎ、このガイドによって検証範囲を広げない。管理画面の削除・定期取得／削除・失敗注入による削除抑止・残存基点復旧は確認済み。更新なしの独立取得を再び未実装課題にしない。

IAM restrictions, IMDS reachability, runtime versions, disk/memory limits and unrelated core-update jobs belong to environment preparation. Loss of required recovery resources or false success reporting would be product issues. Environment setup must not be solved by silently weakening confirmation or deletion rules. Unknown/unsupported information and content outside the defined capture scope remain limitations, not automatic feature commitments.

IAM、IMDS到達性、実行環境の版、容量・メモリ、本体更新ジョブは環境準備の問題。必要資源の喪失・成功誤報なら製品課題。環境都合で確定・削除条件を弱めない。未対応情報を無条件に追加機能の約束へ変えない。
