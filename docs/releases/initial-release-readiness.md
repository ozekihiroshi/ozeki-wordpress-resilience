# 初版候補の範囲と完了判定

2026-10-21更新（3日次枠の往復試験完了、72時間観測は継続）。今回の5項目を管理する現行計画。以前の運用化計画は開発履歴として保持する。対象は研究・開発版であり、導入だけで本番の保護が始まる完成版ではない。

## 何を提供するか

保存元を失ったときにも、外部に残した固定版と独立した信頼情報から復旧を判断できる基盤。中心は取得整合性、保持、独立署名検証、隔離復元である。通知はその失敗・未完了・監視停止を見落とさないための補助である。

|機能|実装|専用環境|実環境での確認|初版の制限|
|---|---|---|---|---|
|取得整合性|DB・ファイル・キューの停止/排出/解除と判定|実WP/MariaDB、HTTP・REST・cron・SSH・キューで検証|実サイトの初回ストリーム取得を実施|任意サイトの全更新経路を自動制御しない|
|保管|Version ID固定、35日保持、別ロール取得|模擬と実S3で検証|正式バケットの実サイト候補と専用canaryを確認|全権限昇格経路の耐性は未認定|
|署名|保存完了と承認を分離、復元前の必須署名ゲート|不正署名・期限・別鍵・文書差替えを拒否|PC署名鍵、暗号化USBコピー、公開信頼情報の読戻し|日次承認更新・鍵失効・代替担当の運用は未完成|
|復元|固定版取得、隔離DB/ファイル/キュー復元|生成データの一致・再配送を検証|実サイト候補の隔離復元と基本表示を確認|無感染認定・再公開承認は行わない|
|日次処理|排他、二重保存防止、結果不明で停止、承認待ち|実S3保存→承認→復元を検証|本番の日次常設運用は未実施|今回の3日次枠・72時間試験で継続性を評価|
|通知・監視|通常警報、外部watchdog、設定切替、テスト送信|実SSH・WP画面・停止再開・未配送保持を検証|PushoverからiPhoneへのテスト受信を確認|本番監視の常設化、SMTP実接続、他通知サービスは未完了|

## 判定対象の区別

上表はプラグイン本体だけでなく外部処理・試験用実装を含むプロジェクト全体の到達点。今回の34/42項目は外部CLIと専用fixtureによる検証であり、インストール可能なプラグインの製品受入試験ではない。[検証記録](initial-release-verification.md)で対象を区別する。

製品課題は提供機能・要件に関する欠陥や未達。環境・試験基盤の事象は[別メモ](initial-release-environment-notes.md)で扱い、それ自体を製品の未達・公開阻害条件にしない。原因未確定は断定せず、製品との関連が確認された場合だけ製品課題へ移す。環境で実行できなかった試験の証拠不足は別途残す。

## 今回の5項目

|番号|完了条件|状態|
|---|---|---|
|1|上表の範囲・未達・製品境界を確定|整理済み|
|2|開始前確認、配置先、操作、成功表示、停止・再開を一続きに説明|統合ガイドを作成|
|3|新しい専用セットで取得→実S3→別プロセス署名→隔離復元を実測し、障害通知・信頼情報保持の試験も照合|10月19日・20日・21日完了。各日の外部構成で保存34項目・復元42項目を確認（件数は合算しない）。未配送と信頼情報の保持も確認|
|4|3日次枠と72時間以上の実経過。欠測・承認待ち・監視停止・通知失敗・容量変化を記録|3セットの保存・試験署名・隔離復元が完了。追加保存は行わない。72時間の最短到達は10月22日15:55:56 JST。既知の4時間26分33秒と4時間24分08秒の観測空白を別々に残して評価する|
|5|README、ガイド、検証結果、既知制限、共通部品責任を整え、公開前確認|開発候補の配布・公開説明は別途整備。継続観測の評価のみ結果待ち|

実S3試験は `isolated-queue-lab` の生成データと実験バケットだけを対象にする。最大3セット、1セット128MiB以下。保持は35日であり、試験終了時に削除しない。署名は使い捨ての試験鍵を別プロセスで扱う。本番の人手承認やOS/物理的な署名権限分離の代わりとはしない。

## 製品と共通部品の責任

Ozeki Database Backup for S3とResilienceは独立導入。他方を自動インストールする必須依存は設けない。既存製品にも復旧関連機能があるので「保存だけ」と説明しない。Resilienceはサイト全体の必要資産・保持・独立検証・信頼の起点・復旧判定を担当する。

共通PHP DBダンプ部品の保守元は `packages/backup-core`。利用側には固定版を取り込み、契約試験と版を記録する。MariaDB CLIによるストリーム取得をこの部品へ統合済みとはしない。将来の収集アダプター・旧資産互換は別の契約変更として扱う。

## 公開の条件

研究・開発版の公開と、侵害後の安全な本番復旧を保証する製品公開を区別する。CR01〜CR08の総合未達は残す。取得物、秘密鍵、トークン、署名付きURL、私有台帳は公開しない。実測原本を公開用に書換えず、集計と原本ハッシュを別記録にする。既存タグを上書きしない。


[今回の検証記録](initial-release-verification.md)に、試験件数・接続障害・未解決事項を記録しています。


[インストール用開発候補の公開説明](plugin-candidate-review.md)は、継続観測と並行して整備する。

## 72時間観測と並行して進める製品化（2026-10-20）

[最初の対応構成・取得契約](../spec/13-first-site-capture-profile.md)と[導入から復旧までの操作](../guides/first-site-operator-runbook.md)を追加した。今回は仕様・手順の整理であり、収集アダプターや本番サービスの実装完了ではない。

|分類|残る課題|次の進め方|
|---|---|---|
|製品の未達|単一サイトの汎用収集、通常WP参照検査、キューなし資産契約、実更新経路の停止と解除|新規専用環境で設定検査と取得アダプターから実装。現行3日試験のfixture・成功条件を途中変更しない|
|製品運用の未達|外部導入、署名更新/失効/代替担当、日次常設、容量と保持期限後の整理|操作手順に沿い未実装の入口と担当者判断を受入項目へ落とす。実サイトの停止条件は適用前に確認|
|外部試験・評価|残り1日次枠、72時間、欠測を含む最終集計|既存計画のまま継続。外部試験をプラグイン受入に換算しない|
|環境・試験基盤|WSL/Dockerの過去起動障害、原因未確定のdrain_timeout|原本を保持して別メモで追跡。再発時に実行可否を確認し、原因が実証された場合だけ製品課題へ移す|

共通PHP部品の採用は独立した作業。Backup for S3の公開済み0.4.0は、その採用やResilienceの製品化が済んだ証拠とはしない。

### 新規収集アダプターの進捗（2026-10-20）

設定検査、設定ハッシュ固定、サイト排他、停止・排出・ストリーム取得・解除、二資産とキュー不存在の結果記録を実装。専用WordPress/MariaDBで通常の添付参照と別DB読込み、障害時の解除を確認した。[手順・検証範囲](../guides/first-site-capture-lab.md)。製品の残課題は汎用ホスト接続、独自プラグイン/外部依存の適合調査、二資産取得物の保管・署名・復元接続。実サイト向け手順の未実装表示は維持する。既存72時間fixtureのコード・判定条件は未変更。

### 2資産の保管・署名・復元（2026-10-20）

専用環境のDB/filesを固定S3版と35日保持証拠へ結び付け、別プロセスの試験署名と独立pinから取得し、新規隔離WordPressで投稿・添付・HTTPを確認した。[検証手順と制限](../guides/first-site-s3-recovery-lab.md)。既存72時間観測とは別。外部開発用入口であり、汎用導入、物理的な署名環境分離、日次・UI接続、途中失敗再開CLIは未達。

## 2026-10-20 二資産日次接続の追加

取得アダプターの日次入口、固定版保存完了と署名承認待ちの分離、別操作の署名承認反映を専用環境で実装・検証しました。重複防止・結果不明停止・証拠再照合を含みます。[手順と制限](../guides/first-site-daily.md)。既存三資産72時間観測の合否や網羅性は変えず、本番日次配置・管理画面統合・承認後の自動復元は未達のままです。

2026-10-20追加：承認済み二資産日次セットの[明示的な固定版隔離復元](../guides/first-site-daily-restore.md)を専用環境で検証しました。自動復元、日次statusへの結果集約、管理画面統合は未達です。元の72時間観測と観測空白の評価は変更しません。

2026-10-20追加：日次statusへの[復元観測の明示登録・集約](../guides/first-site-daily-status.md)を専用コピーで検証しました。保存・承認・復元検証・期限切れ・失敗を分離して表示します。自動登録、管理画面、別ホストからの転送は未達です。元の三資産72時間観測とは独立です。

2026-10-20追加：[復元結果のローカル自動登録](../guides/first-site-auto-recovery.md)を専用環境で実装・検証。成功/失敗/中断/登録待ちを分離し、登録のみ再試行・重複抑止に対応しました。途中停止資源の調査と新規要求解除、管理画面、別ホスト転送は引き続き別課題です。


## 2026-10-20 interrupted recovery cleanup
Generated-only CLI now supports inspect-interrupted and hash-bound cleanup-reviewed, then a new request ID. Ownership-token/immutable-ID checks, shared-volume rejection, per-removal inspection, failure-preserving reviewed_closed state; 42 unit/regression tests passed. Dedicated real Docker interruption and new fixed-S3 isolated restore passed (2 GET, 0 PUT). See ../guides/first-site-recovery-cleanup.md and ../../evidence-public/first-site-recovery-cleanup.json. Initial image-key mismatch was an external test-script defect before resource creation, preserved and reviewed closed. Original 72-hour observation remains incomplete; no production release claim.


## 2026-10-20 read-only daily recovery admin view
Implemented bounded external status export and WordPress administrator-only read-only daily/recovery/cleanup page. PHP validation65 and exporter6 checks passed; real isolated WordPress authenticated HTTP test passed, including editor403, anonymous login, POST405, missing/stale/invalid reports and unchanged source ledger/evidence. Initial late POST rejection returned HTTP200 after headers; fixed with load-page guard (product issue, not environment). See ../guides/daily-admin-status.md and ../../evidence-public/daily-admin-status.json. No production deployment, remote transport, scheduled export or visual browser acceptance. Existing72h observation unchanged and incomplete.


## 2026-10-20 daily admin browser verification
Real isolated Chromium login/sidebar navigation, administrator/editor/anonymous access, POST405, stale/missing/invalid reports and interruption/cleanup display passed. 1440px desktop and390px viewport inspected; mobile table wrapping fixed using minimum width760px and scrollable focusable region. Final five browser scenarios passed; daily evidence/ledger, resilience options, cron and request files unchanged after initialized setup. Test data synthetic/copied; noS3 or notification calls. One earlier login timeout remains unclassified due missing historical diagnostics, retained separately (final rerun not used to erase it). See ../guides/daily-admin-browser.md and ../../evidence-public/daily-admin-browser.json.72h observation still separate/incomplete.


## 2026-10-20 periodic daily status and SSH handoff
Implemented publisher/pull CLI with periodic loop, exclusive locks, fixed read-only SSH command, pinned host key, nonce/site/schema/time/rollback checks, atomic reports and separate receiver health. Last report retained on failure; WordPress shows transfer failure/source failure/source stale/relay stopped/binding invalid. Dedicated actual SSH16 checks, three periodic updates excluding initial one-shot, Python9, PHP76, WordPress HTTP6 health states passed. Source ledger/evidence unchanged, dedicated containers removed, no production/72h changes. systemd examples not deployed; five-minute state transitions use injected timestamps. See ../guides/daily-status-periodic.md and ../../evidence-public/daily-status-periodic.json.


## 2026-10-20 actual systemd stop and resume
Additional dedicated WSL user-systemd test passed with container publisher/relay, actual pinned SSH and Chromium WordPress page. Three periodic updates, duplicate rejection, 314.66 seconds of real stopped time with unchanged source/report/health bytes, stopped display, receiver-only restart/source-stale display and full restart/healthy display verified. Prior recovery/cleanup results remain visible. No timestamp injection in this trial; no S3 calls or production changes. Earlier test-harness PID escaping, Docker SIGTERM exit143 classification and temporary-directory ownership issues were identified and corrected; not plugin defects. Dedicated units/containers/network removed. Production system-unit hardening, separate physical hosts and reboot remain untested. See ../../evidence-public/daily-systemd.json and ../guides/daily-status-periodic.md. Existing72h observation remains separate/incomplete.


## 2026-10-20 production systemd units and guest OS reboot
Dedicated Ubuntu24.04 KVM guest, Docker network=none, generated fixture only.
Original unit baseline passed36 checks before/after guest reboot. Strengthened production examples:
empty capability sets, device/kernel/control-group/clock/hostname protection, namespace and address-family
restrictions, executable-memory restrictions, publisher private network. Final examples used unchanged
in guest;71 checks before and71 after actual OS reboot passed, enabled services resumed without manual
start, 60-second updates and source/report history maintained. Guest Boot ID changed; WSL Boot ID unchanged.
Final reboot-to-verification about38sec. VM removed; private raw evidence retained. S3 calls0.
No product test failure; initial lab copy-mode warning resolved by install0644. Separate physical hosts,
other OS versions and power loss remain untested. Security heuristic2.6/3.0 is not a security guarantee.
See ../guides/daily-status-systemd-production.md and ../../evidence-public/daily-production-systemd.json.
72-hour observation remains separate/incomplete.


## 2026-10-21 separate-VM outage and recovery
Two dedicated Ubuntu KVM guests with independent kernels/disks and private data network, same physical host.
Unmodified hardened production units at60sec; source ledger only on source, relay private key only on receiver.
12 workflow checks and50 role checks before/after passed.
Data-NIC outage: repeated transfer failures preserve exact report hash while publisher continues; reconnect recovers.
Source-only OS poweroff/power-on: receiver remains running, old report retained, enabled publisher automatically resumes.
Receiver-only OS poweroff/power-on: source remains running and updating, enabled relay automatically resumes latest report.
Only restarted guest Boot ID changes; WSL unchanged, original generated fixture/history unchanged; S3calls0.
Both guests/container removed; raw keys/disks private. No new browser or external notification test.
Network-vs-remote-OS cause cannot be inferred from transfer_failed alone. Physical-host failure domains remain shared.
See ../guides/daily-two-vm-recovery.md and ../../evidence-public/daily-two-vm.json. Old72h observation remains separate/incomplete.

## 2026-10-21 daily report independent watchdog
Two dedicated guest VMs and an observer outside both guests. Real-time100s freshness deadline, pinned read-only SSH probes, data-link loss/source OS stop/receiver OS stop all produced alarms and recovery notifications. Local HTTP503 kept pending events; retry delivered them. Observer restart retained state without duplicate accepted event IDs. No external push/mail delivery or physical-host failure test. Initial Docker launcher argument error was a lab harness issue corrected before fault injection. See [guide](../guides/daily-watchdog.md) and [evidence](../../evidence-public/daily-watchdog.json). Existing72h observation remains separate and incomplete.

Daily-watchdog final review: initial restart transient heartbeat_invalid prompted a real6s slow-response regression, which failed before the observer clock fix and passed afterward. This is a product observer defect, distinct from the Docker launcher harness error. Full new-VM v2 trial passed with no heartbeat_invalid; initial evidence retained separately.11 unit/regression tests passed. See daily-watchdog guide/evidence.

## 生成側・取得側の独立watchdog管理画面

専用WordPress/MariaDB/Chromiumで12ケースを確認。PHP新規10項目・既存9項目。各対象の状態、警報発生・解消履歴、未配送集計、期限超過、欠落、ID入替え、サイト違い、未来時刻、不正履歴、サイズ超過、配送異常を検証。権限・POST405・設定/Cron/要求/observer台帳不変を確認。報告生成は既存observer、通知配送は模擬、表示異常は合成fixture。個別通知の受信・確認履歴を保証しない。本番配置・実通知・S3追加保存なし。初回ログイン待ちタイムアウトは原因未確定の試験基盤課題として保持し、プラグイン障害とは断定しない。独立した再試験の成功で初回記録を消さない。詳細は[手順](../guides/daily-watchdog-admin.md)と[evidence](../../evidence-public/daily-watchdog-admin.json)。72時間観測とは独立。

## 独立watchdogからWordPressへの定期SSH受渡し

専用の生成側・取得側・observer・relayコンテナとWordPress/MariaDB/Chromiumで確認。実watchdog処理・固定コマンドSSH・ホスト鍵固定・対象ID検査・周期取得を接続。生成処理停止による警報/回復、relay通信切断、元報告の5分以上の実時間期限超過、observer停止とrelay停止の区別、再開後の表示回復を確認。WordPressから報告書込み/SSH鍵読取り不可、重複relay拒否。通知はローカル記録用コールバック、同一物理ホストのコンテナ、systemdひな型のOS起動再試験は含まない。S3/本番/既存72h観測/共通部品は変更なし。最初のDockerアドレス枯渇は環境課題、次のhost検証ユーザー読取り拒否は試験基盤課題として保持し、製品失敗に混ぜない。新規v3の結果は[evidence](../../evidence-public/observer-status-relay.json)、[手順](../guides/observer-status-relay.md)。

## 独立watchdog報告転送のsystemd・専用VM再起動

外部watchdogと転送VMを分離し、実SSHで取得。専用Ubuntu KVMゲストでproductionサービス例の60秒周期、enabled/active、実行ユーザー・権限制限、重複ロックを確認。実時間5分以上停止した報告保持と管理画面stopped/stale、再開後の回復、ゲストOS再起動によるBoot ID変更と手動startなしの自動取得、警報/解消履歴保持を確認。WSLのBoot IDは不変。WordPress側は専用9p試験共有で出力を読む。本番/実S3/実通知/別物理ホスト障害は対象外。初回はゲストSSH起動待ちの単発timeoutが総期限内の再確認を飛ばす試験基盤問題で停止、記録を保持し修正後は新規VMで確認。詳細は[手順](../guides/observer-status-systemd.md)と[evidence](../../evidence-public/observer-status-systemd-vm.json)。72時間観測とは分離。

## 2026-10-21 状態報告の最終ZIP検証

専用生成データのWordPress環境でPlugin_Upgraderによる新規導入、10月19日候補からの同番号ZIP置換、無効化・再有効化に合格。設定・Cron・wp-config・要求ファイル・外部警報/回復台帳を保持し、管理画面の読取り専用性と編集者の拒否を確認。同じプラグインZIPで日次状態のHTTP試験も合格。最終キットのPython11件/PHP85チェック合格。WordPressコアの下書き掃除Cron初期化による比較失敗を切り分け、初期化後の完全一致で検証。詳細は `evidence-public/status-report-zip.json` と[手順](../guides/status-report-zip.md)。72時間観測の合格・本番適用・公開は別判定。
