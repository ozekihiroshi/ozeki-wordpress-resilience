# Current reconstruction CLI entry points

The development kit contains `rbr-plan.php`, `rbr-s3-kit.py publish` and the independently approved `rbr-approved-kit.py` entry. The unsigned S3 fetch command is disabled. See [signed-kit operation](../docs/spec/rbr-signed-kit.md) and [ZIP setup/preservation](../docs/releases/rbr-signed-kit-zip.md). Install Composer dependencies from the included lock file before PHP-based tests/tools. These generated-data CLIs are not installed by the WordPress administration plugin ZIP.

The following index describes the wider historical prototype and does not imply automatic production enrollment.

# ツール一覧と実行条件

2026年10月19日整理。ファイル移動で既存参照を壊さず、用途と入口を整理した。Git公開用のコードと、Git対象外の取得物・資格情報・証拠原本を分ける。

| 分類 | 主な入口 | 操作と注意 |
| --- | --- | --- |
| オフライン契約検査 | `tests/`、[開発環境](../docs/guides/development-setup.md) | クラウド・実サイトを変更せず検査。依存物の初回導入は通信あり |
| 実サイト候補の署名検証 | `verify-protected-candidate.py --help` | 独立公開ピン、承認、署名、anchor、取得済み資産を読む。サイトコードは実行しない |
| M1署名・復元 | `verify-recovery-approval.py`、`run-independent-recovery.py` | 合成M1形式専用。復元はDocker資源を作成。実サイト候補形式と互換ではない |
| 版固定転送 | `versioned-s3-transfer.php`、`src/VersionedAssetStore.php` | 設定次第でS3 PUT/GET。retention_days=35なら保持検査。CLIの存在だけで運用自動化済みとは扱わない |
| M1取得・発行 | `capture-m1-assets.py`、`prepare-m1-bundle.py`、`m1-live-storage.py`、`publish-m1-set.py` | 模擬試験用。保存元へ一時コピーする旧経路を含む。初回実サイトの直接送信とは別 |
| 共通DB部品 | `dump-database.php`、`vendor-backup-core.py` | ダンプ/同梱版生成。後者は--checkで確認。部品単体で保持・署名・復旧判定は完結しない |
| メタデータ契約 | `recovery-metadata.py`、`bind-m1-observations.py` | M1 RAM/Recovery Setの生成・評価。protected-candidate-v1の発行器ではない |
| 初回実サイトパイロット | `pilot/` | 下記。対象が固定されており、日次ジョブや汎用インストーラーとして使わない |

## pilot/ の扱い

| ファイル | 役割 | 副作用 |
| --- | --- | --- |
| publish-protected-candidate.py | 初回8資産の直接送信・復旧ロールでの独立読戻し | S3へ保持付きPUT、手元へダウンロード |
| sign-protected-candidate.py | 保管候補の独立署名と署名文書の保存 | PC秘密鍵で署名、新規公開ピン、S3 PUT |
| restore-s3-candidate.py | S3取得済み候補の署名ゲート後の隔離復元 | Dockerイメージ・新規ボリューム・コンテナ |
| scoped-s3-presign.py | EC2内で短時間・対象限定リクエストを署名 | EC2メタデータ資格情報を使用。内部ヘルパーであり直接操作しない |

送信・署名・復元の3入口は `--help` または引数なしでAWS/署名/Docker処理を始めない。実行には `--execute-pilot` が必要。ただし、このフラグは対象・鍵・権限・整合性のレビューを代替しない。Python最適化実行（-O/-OO）は拒否する。内部ヘルパーも最適化実行を拒否する。

現在は2026年10月18日のサイト・セット・接続名・ローカルパスに固定。成功済みセットの再実行は不要で、署名更新機能も未実装。パイロットをそのまま定期実行しない。スクリプト内のassertを製品用の明示的な入力拒否へ移行し、引数・設定・再開契約を整える作業は後続段階。

## 署名形式を混ぜない

- M1：`owr-recovery-approval-v1` → `verify-recovery-approval.py` / `run-independent-recovery.py`。
- 実サイト候補：`owr-protected-candidate-approval-v1` → `verify-protected-candidate.py`。スコープは保管内容の完全性を確認した候補に限定。

ダウンロードしたスクリプトを無条件で起動しない。検証器と信頼ピンを取得物から独立して管理する。`--help` の例は安全な説明表示用であり、復旧作業の開始指示ではない。

## 取得整合性（初期模擬試験）

`capture-consistency.py` は観測JSONと独立した期待書込み元一覧を読み、整合性の受入可否を返す。`simulate-capture-consistency.py --output NEW_FILE` は一時SQLite DBと実ファイルで12ケースを検査し、既存出力を上書きしない。実サイト・AWS・Docker・資格情報には触れない。[契約と制約](../docs/spec/11-capture-consistency-contract.md)。既存の実サイトパイロットへの必須ゲート統合は未完了。

### WordPress / MariaDB 取得停止の専用試験

`run-wordpress-consistency-lab.py` は `--execute-lab --output NEW.json` の明示指定時のみ、既存ローカルイメージから外部通信できない使い捨て環境を作る。実際のDB/ファイル更新と復元で停止・待機・解除を検証する。[手順と制限](../docs/guides/wordpress-consistency-lab.md)。

`run-wordpress-consistency-lab.py --execute-lab --routes --output NEW.json` は、実管理画面・REST・cron等の試験と `capture-consistency.py` への実測接続も実行する。PHPの受付全体を一時停止する専用環境向け試作。[手順と適用範囲](../docs/guides/wordpress-route-consistency.md)。

`run-wordpress-consistency-lab.py --execute-lab --external --lab-image owr-external-lab:local --output NEW.json` は先行PHP経路に加え、専用SSH・別コンテナのキュー・固定ジョブの子プロセスを試験する。事前に専用イメージを構築する。[構築・実行・制約](../docs/guides/wordpress-external-writers.md)。

### キュー復旧の専用試験

`run-wordpress-consistency-lab.py --external` は `wordpress-queue-recovery-lab.py` も実行する。`queue-recovery.py` が三資産の組合せと完了ジョブの復元結果を検証する。[方針・再実行](../docs/guides/queue-recovery.md)。

### 三資産の署名検証ゲート

`protected-queue-set.py` は転送アダプターを注入する三資産の検証API。`protected-queue-lab.py` を `--external` 試験から呼び出す。既存の実サイト用pilotと本番鍵は利用しない。[仕様と試験範囲](../docs/guides/protected-queue-set.md)。

### 実験用S3アダプター

`queue-s3-adapter.py` と `lab-s3-request.py` が専用バケットとEC2ロールの転送を扱う。`--s3-lab` は実AWSへの書込みを伴い、通常の `--external` は従来どおり模擬。必要ポリシーと実行手順は[実S3往復試験](../docs/guides/real-queue-s3-lab.md)。

## 日次の監視・試験通知

`operations-monitor-lab.py` はS3日次台帳を読み取り専用で観測し、永続outboxからローカル試験受信箱へ通知する。`monitored-restore-lab.py` は承認済み専用セットの復元試験に開始・失敗・成功の永続記録を付ける。[設定・閾値・障害対応](../docs/guides/operations-monitor-lab.md)。常駐化や実通知は行わない。

## メール配送と独立watchdog

`monitor-runtime-lab.py monitor/watchdog` はsystemdから1回ずつ呼ぶ入口。`monitor-delivery.py` はTLS必須のSMTP配送、`smtp-test-receiver.py` は転送機能のないループバック試験受信機。[メール・タイマー設定](../docs/guides/monitor-email-scheduling.md)。

## dmへの生存記録配送

`heartbeat-ssh.py` は固定コマンドのSSH受信とホスト鍵固定の専用鍵送信を提供する。`monitor-runtime-lab.py` の `heartbeat_ssh_config` で完了後の配送を指定する。[dm配置・権限・検証](../docs/guides/dm-heartbeat-ssh.md)。

## 通知先別の独立配送

notification-dispatch-lab.py は既存outboxを読取り専用で取り込み、宛先別の永続配送状態を保持する専用環境のワーカー。pushover-adapter.py はHTTPS送信・確認照会・取消を提供する。[手順と制限](../docs/guides/pushover-notification-lab.md)。既存スケジューラーへの接続は未実施。

## 通知機能自身の健全性

notification-health.py は配送状態から秘密値を含まないhealth reportとheartbeatを生成します。notification-dispatch-lab.py の正常完了時に更新し、既存の独立watchdogへ渡せます。[設定・検知範囲](../docs/guides/notification-health-lab.md)。

## 通知管理画面との橋渡し

notification-admin-bridge.py は設定候補を外部接続設定と照合して初回構成を作り、配送状態を秘密情報なしで返します。run-notification-admin-lab.py は実WordPress/MariaDB/Chromiumの隔離試験。[管理画面手順](../docs/guides/wordpress-notification-admin-lab.md)。

notification-live.py は外部担当者が候補を明示適用する apply と、稼働DBを正として配送・テスト要求・状態出力を行う run を提供。[切替手順](../docs/guides/notification-live-switch.md)。旧dispatch設定を直接書き換えて運用しない。

notification-transfer.py は専用SSHの receive / exchange、ワーカー用の stage / publish を提供。run-notification-transfer-lab.py は外部通信不可のコンテナ2台で実SSH・分離ユーザーを検証する。[配置・権限・再送手順](../docs/guides/notification-transfer.md)。

notification-runtime.py は relay / worker / watchdog の1周期実行入口。run-notification-runtime-lab.py は別プロセス・実SSHによる定期実行と停止・復帰・通信断の試験。[運用・設定例](../docs/guides/notification-runtime.md)。

## 外部設定作成と導入計画

`external-deployment-plan.py plan|generate` は既存プロファイルとtopologyから読取り専用計画または新規フォルダーへの設定下書きを作る。[手順と未設定事項](../docs/guides/external-deployment-plan.md)。SSH接続・サービス登録・秘密情報作成は行わない。

[生成設定の配置試験](../docs/guides/generated-deployment-lab.md)：既存SSH/定期処理/独立watchdog/WordPressを再利用。限定専用環境での導入経路の検証で、本番自動配置ではありません。

[生成設定の3VM systemd試験](../docs/guides/generated-systemd-lab.md)：既存サービスを再利用し、60秒周期、実停止・再開、OS再起動後の自動起動と画面回復を専用環境で確認。

設定生成・systemd配置の[ZIP検証手順](../docs/guides/deployment-zip.md)。固定ZIPと専用環境で確認し、72時間判定とは分ける。

## First capture readiness

`first-capture-readiness.py`: read-only operator review gate; never starts capture. See [conditions and operator checklist](../docs/guides/first-capture-readiness.md).

`first-capture-entry.py`: initial capture API with mandatory admission re-read under the capture lock and immediately before fencing. `run-first-capture-entry-lab.py` verifies rejection and actual generated WordPress/MariaDB capture; no S3 or signing.

Daily admission: `Coordinator.tick_admitted` reuses mandatory capture admission and rechecks before S3 adapter creation. See [daily admission](../docs/guides/daily-capture-admission.md).

`recurring-capture-review.py`: explicit operator issuance, maximum 168 hours, no overwrite or automatic renewal. See [recurring confirmation policy](../docs/guides/recurring-capture-review.md).

Operator review display: optional `review_file` on preflight relay adds redacted status to existing admin report. [Setup and validation](../docs/guides/operator-review-admin.md).

`run-operator-review-periodic-lab.py`: periodic report and UI recovery using existing relay/transfer, generated transport, isolated WordPress. See [scope](../docs/guides/operator-review-periodic.md).

`run-operator-review-systemd-lab.py`: existing generated configuration harness, real pinned SSH, three disposable Ubuntu VMs, systemd stop/restart/reboot and operator review UI. [Scope and procedure](../docs/guides/operator-review-systemd.md).

ZIP admission/review acceptance: `run-deployment-zip-lab.py --operator-review` uses packaged code, actual WordPress install/update, generated daily records and immutable external state. [Guide](../docs/guides/admission-zip.md).

`run-onboarding-recovery-lab.py`：生成WordPress/MariaDBで取得判定付き日次処理→試験署名→隔離復元→日次結果登録を接続。ローカル固定版代替を使用し、実AWS/実SSHは対象外。[操作と範囲](../docs/guides/onboarding-recovery.md)。

`run-onboarding-ssh-s3-lab.py`：生成サイトの実SSH棚卸しから、取得判定・実験S3・試験署名・隔離復元・日次登録まで。[構成・保存先・再実行時の注意](../docs/guides/onboarding-ssh-s3.md)。


Trust lifecycle: `trust-lifecycle-cases.py` checks disposable signing-key rotation/revocation and simulated media readback against the existing gate. See [scope and known rollback limitation](../docs/guides/trust-lifecycle.md). No S3, production keys or physical USB.

Current recovery trust: [mandatory checkpoint deployment](../docs/guides/current-recovery-trust.md), [generated acceptance evidence](../evidence-public/current-recovery-trust.json). Missing administrator checkpoint now blocks recovery; no production checkpoint was installed.

`update-current-recovery-trust.py`: administrator-only validation/deployment of the fixed current registry. See [procedure](../docs/guides/trust-registry-update.md).

`trust-registry-ssh.py`: bounded pinned SSH delivery to the existing registry updater; never automatically retries. See [SSH guide](../docs/guides/trust-registry-ssh.md).

`run-trust-ssh-recovery-lab.py` / `trust-ssh-recovery-cases.py`: explicit generated-data SSH-to-recovery integration using actual offline restore and fixture storage. Requires dedicated development Docker privileges; see [scope](../docs/guides/trust-ssh-recovery.md).

`run-trust-ssh-recovery-lab.py --real-s3` reuses existing experimental object versions with the existing real reader via `trust-recovery-s3-broker.py`; no PUT. See [scope](../docs/guides/trust-real-s3-recovery.md).

Recurring current-trust operations: [runbook and six targeted connection checks](../docs/guides/trust-recurring-operations.md). Generated data, temporary local host representations; no new real SSH/S3 or 72-hour acceptance claim.

- `rbr-generation-kit.py`: fixed S3 generation receipt + explicit R/E/C/Q profile to an approval-pending kit. Preserves the generation, checks common retention horizon, copies short-protected profile dependencies; no fixture generation, signing or WordPress execution. See [contract](../docs/spec/rbr-generation-kit.md).

- `rbr-coordinate-s3-lab.php` / `rbr-coordinator-transport.py`: scoped experimental real-S3 generation coordinator; see [connection guide](../docs/spec/rbr-live-coordinator.md).

`run-rbr-wordpress-save-lab.py --output NEW_PRIVATE_DIRECTORY` exercises the opt-in three-page save API with real WordPress HTTP/MariaDB and the existing S3 contract double; see docs/spec/rbr-wordpress-save.md. It requires locally available pinned images and Composer dependencies, exposes no public ports, and removes its dedicated containers. No real AWS writes or editor-button integration.

`run-rbr-wordpress-save-s3-lab.py --output NEW_PRIVATE_DIRECTORY --vendor-cache LOCAL_COMPOSER_VENDOR --case api-UNUSED_SUFFIX` reuses the HTTP/MariaDB cases with the existing real experimental S3 broker and a private Unix socket. It requires WSL/Linux, pinned local Docker images, matching Composer dependencies and the existing community/dm test roles. It checks the exact prefix is empty before writes; refuses reuse. It creates retained experimental S3 objects and deletes only its dedicated containers. Do not rerun a failed lab into a new prefix blindly: inspect its private transport journal and pending operation first. Only generated data; never install its MU-plugin or fault controls on a live site. See the save API specification and live evidence.

`run-rbr-wordpress-editor-lab.py --output NEW --vendor-cache LOCAL_COMPOSER_VENDOR` tests the opt-in protected editor in isolated WordPress/MariaDB/Chromium with a persistent S3 double. Uses directly launched, matching ChromeDriver; no production or AWS writes. Private browser logs may include test cookies. See docs/spec/rbr-wordpress-editor.md.

### Protected editor with real experimental S3

`run-rbr-wordpress-editor-s3-lab.py --output NEW_PRIVATE_DIR --vendor-cache MATCHING_VENDOR --case api-UNUSED_CASE` reuses the browser scenarios and restricted S3 role broker. An exact-prefix empty read is mandatory. Three generations are written and retained; never blindly rerun an unknown result or delete the journal. Private logs may contain generated cookies. Success/retention evidence: `evidence-public/rbr-wordpress-editor-s3.json`.
