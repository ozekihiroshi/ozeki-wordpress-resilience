# Phase 0 既存バックアップ機能の調査

調査日：2026年10月17日  
対象：D:\workspace\secure-s3-storage-for-wordpress、HEAD 627e47c2b31527ef1486e582b79fd5dba875843f、ソース表記0.3.0。

以下の参照パスと行番号はこのコミットのソースに対するもの。稼働環境での機能試験は未実施。

## 機能とコード上の根拠

| 項目 | 確認した実装 | 根拠 |
| --- | --- | --- |
| DB生成 | native/PHPのダンプ選択、SQLからgzip生成、サイズとSHA-256照合 | src/Backup/Database/DumpBackendSelector.php:34、src/Backup/DatabaseBackupService.php:25、src/Backup/Compression/GzipVerifier.php:15 |
| DB保存 | 圧縮物をS3 PUT、ChecksumSHA256、IfNoneMatch=*、HEADでサイズとチェックサム確認 | src/Aws/S3Storage.php:20 |
| DB取得補助 | 期待サイズとSHA-256でダウンロードを検証。VersionIdを指定する引数はない | src/Aws/S3Storage.php:100 |
| DB履歴 | WordPress option secure_s3_storage_backup_historyに最新20件を保存 | src/Backup/History/BackupHistoryRepository.php:7 |
| DB定期実行 | dailyのWP-Cron登録 | src/Cron/BackupScheduleManager.php:13、37 |
| DB保持処理 | 候補をListObjectsV2で列挙しDeleteObject。CLIは成功後に保持設定を適用 | src/Backup/Retention/S3BackupRetentionManager.php:158、291、src/Cli/BackupCommand.php |
| メディア形式 | uploadsのファイル別インベントリ。相対パス・サイズ・SHA-256をJSONL記録 | src/Backup/Media/MediaManifest.php:12、20、72、src/Backup/Media/MediaEntry.php:36 |
| メディア保存 | オブジェクトを転送・照合してinventory.jsonlとcomplete.jsonを保存。マルチパート対応 | src/Backup/Media/MediaUploadStep.php:18、39、59、160 |
| メディア比較 | 復元ディレクトリとインベントリの比較機能 | src/Backup/Media/MediaManifest.php:116 |
| 認証 | AWS SDKのデフォルト資格情報チェーンに委ねる。固定キーを引数で渡す実装ではない | src/Aws/S3ClientFactory.php:9 |
| CLI入口 | backup、status、mediaを登録 | src/Cli/CommandRegistrar.php:9 |
| メディアCLI | prepare、start、enqueue、tick、status、cleanup。statusはJSON出力 | src/Cli/MediaCommand.php:23、43、66、80、92、120 |

資格情報チェーンの採用だけで権限分離や短命資格情報が保証されるわけではない。保管先・実行主体の設定を別に確認する。

## 保存形式とキー構成

通常DBは「prefix/backups/database/YYYY/MM/DD/db-DB名-日時-乱数.sql.gz」。キー生成はDatabaseBackupService.php:109。S3UploadResult.php:7が返すのはbucket、key、size、ETag、SHA-256で、VersionIdは保持しない。

通常メディアは「prefix/backups/media/job_id/」。その下にinventory.jsonl、complete.json、files/SHA256相対パスがある。ファイル名のハッシュは内容ハッシュではなく相対パスのハッシュであり、内容の完全性はインベントリ内のSHA-256で照合する。根拠：MediaUploadStep.php:31、39、59。

complete.jsonはrun、inventory、inventory_sha256、files、bytes、object_key_ruleを含む。完了マーカーをサイト全体の復旧成功とは扱わない。

DBとメディアは別処理であり、同一時点の原子的なスナップショットを保証しない。M1では更新停止等の整合性確保手順が必要。

## 開発版のRecovery Set

既存プラグインにはM1と近い内部実装がすでにある。

| 要素 | 内容と境界 | 根拠 |
| --- | --- | --- |
| RecoverySet | collecting、publishing、complete、failed。固定intent、DBとメディアの保存先 | src/Backup/Recovery/RecoverySet.php:23、40、69、81 |
| RecoveryManifest | odbfs3-recovery-set、schema_version=1。環境、取得期間、DB、メディア、検証、対象外を保持 | src/Backup/Recovery/RecoveryManifest.php:25 |
| RecoveryCollector | enqueue、tick、publishによる永続状態・再試行の管理 | src/Backup/Recovery/RecoveryCollector.php:23、41、51 |
| RecoveryPipeline | DB・メディア実処理。呼出側がスケジュールする内部機能 | src/Backup/Recovery/RecoveryPipeline.php:23、41 |
| RecoveryPublisher | 条件付き公開、HEAD照合、GET原文照合、受領記録 | src/Backup/Recovery/RecoveryPublisher.php:20 |
| RecoveryObservation | manifestのハッシュにavailability／restoreの評価を結びつける | src/Backup/Recovery/RecoveryObservation.php:14 |

Plugin.phpとCommandRegistrar.phpの入口にはRecoveryCollector等を使う専用コマンドがない。内部クラスをそのまま安定した公開APIとみなさない。通常のバックアップコマンドが自動的にこの復旧セットを生成するわけではない。

内部セットのIDは32桁の小文字16進数（Contract.php:27）。M1例のRS-M1-001をそのまま渡せない。上位の表示IDと内部IDの対応を管理する案がある。

## RAMへ利用できる情報

RecoveryManifest.php:65のenvironmentはwordpress、php、plugin、database_server、table_prefix。ここでpluginはバックアッププラグインの版であり、全プラグインの一覧ではない。

DB・メディアのキー、サイズ、ハッシュ、取得・転送・検証時刻、backend、source_id、set_id、対象範囲は再利用候補。テーマ、全プラグイン、独自コード、サーバ構成、復旧手順、復旧権限の取得方法は上位RAMで補う。

既存マニフェストの対象外はwordpress_core、themes、plugins、wp_config、other_files、server_configuration（RecoveryManifest.php:10）。既存フォーマットは厳密なフィールド検査を行うため、そのJSONへ勝手に独自項目を足さず、上位RAMから原文ハッシュとともに参照する構成を提案する。

## 固定バージョン参照の不足

RecoveryManifestのartifactはversion_idを持つがnullを許す（:115）。RecoveryPipelineはDB、inventory、markerのversion_idをnullで生成し、取得したHEADのVersionIdを反映していない（:81、168、169）。メディア個別インベントリにもVersionIdフィールドはない。

一方、RecoveryPublisherはマニフェスト自体のHEADからVersionIdを取得し、GETと受領記録に使用する（:37、42、73）。「VersionId対応が全くない」とも「全資産が固定バージョンで保護されている」ともいえない。

M1の全必要資産の固定参照には、外部観測でVersionIdと期待ハッシュを照合して別カタログへ固定する等の補完が必要。null、文字列null、Versioning未確認を検証済み固定版として扱わない。条件付きPUTと一意キーだけで攻撃者による削除耐性を認定しない。

## 既存試験資産

tools/test-wordpress-recovery-local.sh、tools/test-wordpress-recovery-s3-bridge.sh、tools/test-recovery-s3-roundtrip.php、tests/manual/test-wordpress-recovery.php、およびRecovery関連の契約・収集・公開・パイプライン試験が存在する。

既存docs/aws-recovery-set-verification-2026-10-17.mdには、模擬データでnative/PHP各46検査に合格した報告がある。ただしfixtureの転送経路を含む限定試験で、運用WordPressからS3への一連の公開ワーカー実行ではないと明記されている。VersionIdなし、バケット設定の一部AccessDenied、大容量multipart等の対象外も記載されている。

今回これらを再実行していない。M1の証拠として流用せず、試験設計・コードの再利用候補とする。
