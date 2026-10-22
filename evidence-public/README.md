# 公開検証結果の索引

更新：2026年10月19日。ここは公開用集計であり、署名された証拠原本そのものではない。秘密情報・DB内容・署名付きURL・秘密鍵は置かない。原本はGit対象外の.local/、evidence/、WSL専用領域で管理する。

M1の一部は例示識別子、後続の実サイトパイロットは実際のサイト名・バケット名等を含む。全て例示値とは扱わない。版番号・AWS識別子は認証情報ではないが、公開範囲のレビューは必要。改変検知の信頼起点は独立公開ピンと署名である。

| 対象 | 集計 | 意味 |
| --- | --- | --- |
| 模擬M1 | [m1-summary.json](m1-summary.json) | 当時の条件での模擬復元 |
| 共通DB部品 | [shared-core-recovery.json](shared-core-recovery.json) | 抽出部品を用いた再実証 |
| 初回取得 | [initial-live-stream-capture.json](initial-live-stream-capture.json) | ストリーム取得と圧縮実測 |
| 保管前の隔離復元 | [initial-live-quarantine-restore.json](initial-live-quarantine-restore.json) | ローカル取得物からの内容確認 |
| 正式バケット | [production-storage-canary.json](production-storage-canary.json) | 専用試験版の保持・拒否・固定版取得 |
| 保存・署名 | [protected-candidate-publication.json](protected-candidate-publication.json) | 8資産と台帳・署名等12オブジェクトの独立確認 |
| S3起点の復元 | [signed-s3-candidate-restore.json](signed-s3-candidate-restore.json) | 新規固定版取得・署名ゲート・基本復元確認 |
| USB公開信頼情報 | [usb-candidate-trust-copy.json](usb-candidate-trust-copy.json) | 読戻しと署名確認。取外しは利用者申告 |
| 保持ロジック | [production-retention-offline-tests.json](production-retention-offline-tests.json) | オフラインの転送契約検査。AWS攻撃耐性の判定ではない |

過去の失敗を後の成功で消さず、各ガイドの続報から現在の状態を辿る。[現在の計画](../docs/spec/10-operationalization-plan.md)と[公開受入条件](../docs/spec/07-cyber-resilience-release-gates.md)を合わせて読む。

[取得整合性の模擬試験](capture-consistency-lab.json)：SQLite/実ファイルの12ケース。MariaDBやWordPressの運用制御を実証した記録ではない。

- [WordPress / MariaDB取得停止の実測](wordpress-consistency-lab.json): 専用協調更新入口の10ケース。実サイト全更新経路の停止保証ではない。

- [実WordPress更新経路と取得整合性判定](wordpress-route-consistency.json): 専用構成で先行分を含む19ケース。管理画面/REST/cron等と終了処理を待ち、実観測から判定。本番範囲は未完了。

- [SSH・外部キュー・子プロセスの制御](wordpress-external-writers.json): 専用の制限された更新経路で先行分を含む29ケース。本番の任意SSH/rootや既存キュー製品への対応を意味しない。

- [キュー復旧・再配送](wordpress-queue-recovery.json): 専用環境37ケース（キュー復旧8ケースを含む）とPython契約92件。DB・ファイル・キューの共通チェックポイント、ACK喪失、世代拒否、隔離を検証。本番承認ではない。

- [三資産の署名付き復旧セット](protected-queue-set.json): 専用環境51ケース、Python契約103件。実WordPress/MariaDB・キュー復元と実RSA署名。S3はローカル模擬であり、実AWS Object Lock/IAMの実測ではない。

- [実S3三資産往復試験](real-queue-s3-roundtrip.json): 分離したEC2ロールで固定版・保持証拠・署名を実検証し、隔離復元・キュー再配送まで43ケース合格。削除拒否はIAM明示Denyを含み、本番承認ではない。

- [日次バックアップ専用環境](daily-backup-lab.json): 日次状態・再試行・同日重複排除と51ケースの実WordPress復元。保存先は模擬S3、全Python128件、定期ジョブは未有効化。

- [実S3日次保存と独立承認](daily-s3-approval-lab.json): 34ケース・Python143件。未署名の三資産保存→承認待ち→別プロセスの署名取込みを実測。新セットの復元・本番運用・定期起動は未実施。

- [承認済み日次セットの隔離復元](approved-daily-restore.json): 42ケース・Python156件。既存署名と独立ピンを使い、実S3の3固定版GETからDB・全ファイル・キューを復元。S3書込み・本番復元はなし。

- [日次監視・試験通知](operations-monitor-lab.json)：4種類の異常、通知重複防止・解消・再送・監視元障害を専用環境で検証。実通知先への送信なし。

- [メール通知・定期実行・監視停止検知](monitor-email-scheduling.json)：関連42件と実systemdタイマー・ローカルSMTP往復。外部宛先への送信なし、試験用サービスは停止済み。

- [dm専用SSH heartbeat](dm-heartbeat-ssh.json)：実SSH18項目・関連56件。権限分離、停止・解消、既存FTP/MySQL/SSHの維持を確認。実通知なし。


- [Trust lifecycle](trust-lifecycle.json): 12 generated-data checks and one explicitly unmet old-trust rollback requirement. Same-machine simulated media, not a real USB or independent-person exercise. [Method and operations](../docs/guides/trust-lifecycle.md).

Current recovery trust: [mandatory checkpoint deployment](../docs/guides/current-recovery-trust.md), [generated acceptance evidence](../evidence-public/current-recovery-trust.json). Missing administrator checkpoint now blocks recovery; no production checkpoint was installed.

[Trust registry SSH](trust-registry-ssh.json): 13 real-SSH checks, 4 protocol regressions, initial classification defect and fix; separate VM stopped.

[SSH trust to recovery](trust-ssh-recovery.json): four integration cases, actual WordPress restore, fixture S3, initial test-path correction retained.

[Real S3 with SSH current trust](trust-real-s3-recovery.json): four integration cases, two actual fixed-version GETs, no PUT, real offline restoration and cleanup.

[Trust final ZIP](trust-final-zip.json): frozen artifact hashes, install/update/state retention and 52 packaged trust tests.

Recurring current-trust operations: [runbook and six targeted connection checks](../docs/guides/trust-recurring-operations.md). Generated data, temporary local host representations; no new real SSH/S3 or 72-hour acceptance claim.

Additional [two-VM recurring SSH verification](../docs/guides/trust-recurring-ssh.md) passed seven checks: per-host readback, partial authentication failure, actual expiry and explicit refresh recovery, with signed approvals unchanged. No new S3/restore or 72-hour coverage claim.

[Recurring trust final ZIP acceptance](../docs/releases/recurring-trust-final-zip.md): fresh install, same-version update, settings/history and unchanged approval retention verified; prototype only, separate from 72-hour evaluation.
