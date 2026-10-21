# 初版整備の判定表

2026-10-21。詳細な現在値は[現状一覧](current-status.md)、過去の経緯は[進捗履歴](initial-release-history.md)を参照。履歴中の「未実装」を現在の判定として使わない。

|項目|現在の判定|
|---|---|
|1 棚卸し・範囲|現状一覧へ整理済み。試作版、専用検証と本番適用の境界を明記|
|2 導入・定期実行・停止|個別手順は検証済み。設定作成と読取り専用計画を追加。本番自動配置は未提供|
|3 取得から復元|専用生成データによる実S3・分離ロール・独立試験署名・隔離復元を確認済み|
|4 継続運転|3日次枠完了、72時間経過は未達。既存の2欠測区間を保持|
|5 GitHub初版候補|PR #3マージ・CI・検証済みZIPあり。正式リリースと72時間最終判定は未実施|

[担当者の操作](../guides/first-site-operator-runbook.md)／[設定作成](../guides/external-deployment-plan.md)／[配布範囲](plugin-candidate-scope.md)／[検証対象の区別](initial-release-verification.md)
