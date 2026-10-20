# 初版候補の検証記録

2026-10-21更新。10月19日・20日・21日の専用構成での往復試験は完了。72時間観測・最終評価は未完了。

## 検証対象と証拠の範囲

|対象|今回の証拠|主張しないこと|
|---|---|---|
|WordPressプラグイン本体|管理画面・通知設定等の従来記録を別途参照。今回、その受入試験を追加実施したとは扱わない|下記Python件数をプラグイン本体の合格件数に換算しない|
|外部CLI・契約・試験ツール|Python試験と専用fixtureによる取得・保存・署名・復元・通知保持の検証|プラグインのインストールから本番復旧までの一貫した製品受入試験ではない|
|実験環境・AWS構成|実験用ロール・バケット・接続条件の確認|一般利用者の環境・本番構成の適合保証ではない|

現行プラグインのエントリーポイントは通知管理画面を起動する。今回のバックアップ往復試験は外部Python CLIと協調する専用WordPress/MariaDB fixtureを用いている。実WordPressを使用した事実だけでは、プラグイン本体の機能試験にならない。

## 今回の試験結果

|確認|結果|対象・制約|
|---|---|---|
|Pythonテストスイート|380件合格、失敗・エラー・skipなし|外部処理・契約・試験ツール等の集計。レビュー機能追加前。プラグイン本体の受入件数ではない|
|送信前失敗レビュー|9件合格|専用日次試験ツールの再試験保護|
|日次処理回帰／S3保存承認|14件／15件合格|外部Python処理。380件との重複を含み、足し算して製品の試験件数にしない|
|ローカル統合|51項目合格|専用fixture・模擬保管。後の往復試験と重複する検証項目を含む|
|実S3保存／隔離復元|34項目／42項目合格|専用fixtureと外部CLIによる実S3往復。プラグイン単体の合否ではない|
|文書・公開候補確認|リンク45件有効、365テキストファイルで秘密情報パターン該当なし|文書品質・ヒューリスティック検査。製品機能試験ではない|
|AWS事前確認|実験用writer/readerで合格|実験環境のVersioning・Object Lock・公開遮断・暗号化・ロール分離|

## 初日の往復試験（2026-10-19 16:32 JST）

外部処理による取得→実S3固定版保存→別プロセスの試験署名承認→署名検証後の隔離復元が完了した。三資産は合計29,842,299 bytes。固定版3件のPUTと独立GETが成功し、不明な送信は0件。保持期限の最小値は2026-11-23T07:33:46Z。復元後の検証と試験資源の削除も確認した。

実台帳とは別のコピーで配送失敗を注入し、復元前の未配送2件が同じIDで保持され、復元後に元警報と解消の計4件をローカル受信箱へ配送できた。信頼情報のハッシュも一致。実Pushover追加送信は0件。これは外部通知処理の継続性検証であり、WordPress管理画面からの配送試験ではない。

試験秘密鍵は破棄した。別プロセスでも同じWSLユーザーであり、物理的な鍵管理分離・人手承認を実証したとはしない。

[初日の公開集計](../../evidence-public/initial-release-first-day.json)

## 残る評価

3つの日次枠の保存・署名・隔離復元と72時間以上の観測を必要とする。初回観測は2026-10-19 15:55:56 JST。時間条件だけでも2026-10-22 15:55:56 JSTより前には完了しない。欠測は記録し、必要な証拠を再取得する。

環境起因の接続失敗と、原因未確定のfixture待機事象は[環境・試験基盤メモ](initial-release-environment-notes.md)へ分離した。これらをプラグインの既知不具合や合否件数に算入しない。製品の保護範囲・未実装機能・未検証の要件は[初版判定表](initial-release-readiness.md)で管理する。

## 2日目と継続観測（2026-10-20 10:42 JST時点）

10月20日分は29,843,290 bytesを保存し、承認待ちの観測後に試験署名・固定版取得・隔離復元まで完了。各日の保存34/復元42は外部CLIとfixtureの検査項目で、日数分を足して製品受入件数にしない。復元前後の未配送IDと信頼情報を保持した。初回のDocker事前確認失敗は送信前と確認して記録を残し再試験した。

監査原本2026-10-20T01:42:39.275458Zでは2セット59,685,589 bytes、結果不明PUT0、信頼情報10ファイルに変化なし、未配送0・未解消0。23観測中、2時間超の間隔は10月20日02:05:00〜06:31:33 JSTの約4時間26分33秒が1件。新たな2時間超の間隔はない。定期観測間の連続稼働を証明するものではない。

日次成功は3/3、72時間は未到達、観測の網羅性には既知の2件の空白がある。最後もこの3軸を別々に評価し、欠測を成功で補完しない。10月19日・20日・21日分を再保存しない。72時間経過だけで合格にしない。

原本は運用側の継続試験台帳・署名/復元台帳・時刻付き監査に保持。私有原本を公開ファイルへコピーせず、最終集計時に原本ハッシュと公開可能な結果を整理する。同じWSLユーザーの試験署名を物理的な署名担当分離の証明にしない。

### First-site二資産の実S3往復

新規ゲート6テスト（通常・最適化）、既存取得14テスト、既存三資産ゲート11テストを確認。専用実接続8ケースと4オブジェクトの固定版保存・保持・署名・復元、資源削除を確認。[集計](../../evidence-public/first-site-s3-recovery.json)。初回の再利用異常系試験はTimeoutExpiredで期待理由と異なり中断、S3送信0。失敗原本を残し、別の正常取得専用入口で往復を実施した。

### First-site停止確認タイムアウト修正

[再現・比較・修正後の集計](../../evidence-public/first-site-timeout-fix.json)。実添付欠落で60秒待ちを1回再現、条件を絞ったDocker比較3/3回で待機し、読み取り後復帰。新方式3/3回正常。修正後は単独3回・連続7ケース、取得契約17・一時保管4・既存署名ゲート6テストを確認。過去失敗は削除せず、S3往復の過去結果を書き換えない。

## 2026-10-20 二資産取得の日次接続

既存72時間観測とは別の生成WordPress/MariaDB、専用日次台帳で、取得・停止解除→実験S3の2固定版保存→独立読戻しと35日保持→署名承認待ちを確認。AWS-f222f329f1737d20、2 PUT、29,812,385 bytes。別の使い捨て試験署名を明示的に実行し、署名不正の読取り前拒否と承認済みへの移行も確認。日次処理は署名鍵を持たず、復元・本番再公開を行いません。

単体試験12件（通常実行）で同日重複・排他・中断・PUT結果不明による翌日停止・証拠再照合・改ざん・期限切れ・既存観測台帳の流用拒否を確認。独立署名ゲートの既存6件も合格。詳細は[日次接続](../guides/first-site-daily.md)、公開集計は evidence-public/first-site-daily.json。生成データの試験であり、実サイトへの導入・汎用収集アダプター・別ホスト署名運用の合格ではありません。

## 2026-10-20 19:59 JST 承認済み日次セットの隔離復元

AWS-f222f329f1737d20を、独立保管した署名文書・公開鍵ピン・取得設定ピンで検証後、S3固定Version IDの2 GET（29,812,385 bytes）から復元しました。追加PUT・再署名なし。保存元サーバーや取得フォルダは入力にせず、新規DB認証情報でnetwork=noneのDBと通信空間共有のWPへ復元。投稿1件、標準添付one.png、画像SHA256、HTTP200と投稿表示、WP-Cron停止・外部HTTP遮断を確認し、専用コンテナ・匿名ボリューム除去を確認済みです。

安全判定10件を通常・最適化実行で検証。署名不正、文書/公開鍵/設定ピン不一致を読取り前に拒否し、Version ID不一致や二番目の資産だけの改ざんでも復元を始めないこと、途中失敗を成功扱いしないことを確認しました。[手順・制限](../guides/first-site-daily-restore.md)、公開集計 evidence-public/first-site-daily-restore.json。既存の保存時承認記録は上書きせず、復元証拠は別記録です。実マルウェア・本番再公開・独立ホストでの署名運用を合格とする試験ではありません。

## 2026-10-20 日次状態への復元観測集約

元の二資産台帳を別フォルダへ複製し、AWS-f222f329f1737d20の実隔離復元証拠を登録。保存完了・承認済み・復元検証済みを分けてJSON表示しました。承認文書/公開鍵/設定/セット/取得試行、固定Version ID、取得物、隔離方式、投稿/画像/HTTP、後片付けを照合します。承認記録は上書きせず、観測をSQLiteへ追記します。

統合12ケース、集約単体6件（通常・最適化）、既存日次12件が合格。重複登録、読取り専用照会、期限切れ、別セット・固定版不一致・隔離不備・未承認への登録拒否、後の失敗と過去の成功の保持を確認。元の台帳・承認・保存受領のハッシュ一致、追加S3呼出し0を確認しました。公開証拠 evidence-public/first-site-daily-status.json、[操作と制限](../guides/first-site-daily-status.md)。担当者が確認するローカル観測であり、実行結果の独立署名/遠隔実行証明ではありません。自動登録・管理画面統合は未実装です。

## 2026-10-20 21:14 JST 復元結果の自動登録

別の専用台帳でAWS-f222f329f1737d20から2固定GET・29,812,385 bytesを隔離復元し、自動登録まで確認しました。追加PUTなし。専用コンテナ・匿名ボリュームの除去と、元の二資産台帳・承認・受領のハッシュ維持を確認済みです。登録commit直後の応答喪失を注入し、登録のみの再試行で観測1件を保ち、同一要求の再実行でもGET/復元を増やさないことを確認しました。

統合7ケース、ワーカー9件（通常・最適化）、日次回帰12件が合格。失敗レポートの自動登録とプロセスの最終レポート前終了も専用コピーで注入検証。実環境障害と混同しません。途中停止は同一要求の次回処理で結果不明として停止し、未完了資源は担当者による調査が必要です。失敗・中断後の新規復元を解禁するレビュー入口は未実装です。公開証拠 evidence-public/first-site-auto-recovery.json、[手順](../guides/first-site-auto-recovery.md)。元の三資産72時間観測や共通部品は変更していません。


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

## 2026-10-21 第3日次枠完了
3日次枠とも固定Version IDで保存・試験署名・隔離復元・未配送と信頼情報保持を確認。詳細は [3日次枠の集計](../../evidence-public/initial-release-three-days.json)。既知の約4時間26分33秒と約4時間24分08秒の欠測を保持。日次成功と72時間経過と観測網羅性を別評価し、72時間到達前の全完了判定は行わない。追加S3保存は停止するが観測は継続する。

## 生成側・取得側の独立watchdog管理画面

専用WordPress/MariaDB/Chromiumで12ケースを確認。PHP新規10項目・既存9項目。各対象の状態、警報発生・解消履歴、未配送集計、期限超過、欠落、ID入替え、サイト違い、未来時刻、不正履歴、サイズ超過、配送異常を検証。権限・POST405・設定/Cron/要求/observer台帳不変を確認。報告生成は既存observer、通知配送は模擬、表示異常は合成fixture。個別通知の受信・確認履歴を保証しない。本番配置・実通知・S3追加保存なし。初回ログイン待ちタイムアウトは原因未確定の試験基盤課題として保持し、プラグイン障害とは断定しない。独立した再試験の成功で初回記録を消さない。詳細は[手順](../guides/daily-watchdog-admin.md)と[evidence](../../evidence-public/daily-watchdog-admin.json)。72時間観測とは独立。

## 独立watchdogからWordPressへの定期SSH受渡し

専用の生成側・取得側・observer・relayコンテナとWordPress/MariaDB/Chromiumで確認。実watchdog処理・固定コマンドSSH・ホスト鍵固定・対象ID検査・周期取得を接続。生成処理停止による警報/回復、relay通信切断、元報告の5分以上の実時間期限超過、observer停止とrelay停止の区別、再開後の表示回復を確認。WordPressから報告書込み/SSH鍵読取り不可、重複relay拒否。通知はローカル記録用コールバック、同一物理ホストのコンテナ、systemdひな型のOS起動再試験は含まない。S3/本番/既存72h観測/共通部品は変更なし。最初のDockerアドレス枯渇は環境課題、次のhost検証ユーザー読取り拒否は試験基盤課題として保持し、製品失敗に混ぜない。新規v3の結果は[evidence](../../evidence-public/observer-status-relay.json)、[手順](../guides/observer-status-relay.md)。

## 独立watchdog報告転送のsystemd・専用VM再起動

外部watchdogと転送VMを分離し、実SSHで取得。専用Ubuntu KVMゲストでproductionサービス例の60秒周期、enabled/active、実行ユーザー・権限制限、重複ロックを確認。実時間5分以上停止した報告保持と管理画面stopped/stale、再開後の回復、ゲストOS再起動によるBoot ID変更と手動startなしの自動取得、警報/解消履歴保持を確認。WSLのBoot IDは不変。WordPress側は専用9p試験共有で出力を読む。本番/実S3/実通知/別物理ホスト障害は対象外。初回はゲストSSH起動待ちの単発timeoutが総期限内の再確認を飛ばす試験基盤問題で停止、記録を保持し修正後は新規VMで確認。詳細は[手順](../guides/observer-status-systemd.md)と[evidence](../../evidence-public/observer-status-systemd-vm.json)。72時間観測とは分離。

## 2026-10-21 状態報告の最終ZIP検証

専用生成データのWordPress環境でPlugin_Upgraderによる新規導入、10月19日候補からの同番号ZIP置換、無効化・再有効化に合格。設定・Cron・wp-config・要求ファイル・外部警報/回復台帳を保持し、管理画面の読取り専用性と編集者の拒否を確認。同じプラグインZIPで日次状態のHTTP試験も合格。最終キットのPython11件/PHP85チェック合格。WordPressコアの下書き掃除Cron初期化による比較失敗を切り分け、初期化後の完全一致で検証。詳細は `evidence-public/status-report-zip.json` と[手順](../guides/status-report-zip.md)。72時間観測の合格・本番適用・公開は別判定。
