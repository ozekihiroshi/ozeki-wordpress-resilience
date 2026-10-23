# Approval-pending kit preparation (opt-in prototype)

Tools → 復旧キットの準備 lists the applied generations from the protected editor. Select **承認待ちキットを準備**. The server derives an applied receipt from saved history; the browser cannot supply commands, paths, generation locators, Q or profiles. The external worker runs the existing `rbr-generation-kit.py` CLI and reports running, failed, interrupted, blocked, or stored-awaiting-independent-approval. No signature, approval renewal, reconstruction or publication is performed here.

## Explicit configuration

Load `RbrReconstructionConsole.php` and `RbrKitPreparation.php` from the external kit, then call `RbrKitPreparation::boot($factory, $ids, $reportPath, $inboxPath)`. Reuse the protected editor factory and enrolled page IDs. Plugin activation alone does not enable this feature.

Operator configuration schema `owr-kit-preparation-config-v1` has absolute `profile`, `inbox`, `state`, and `report` paths. Profile is the existing request-Q profile with pinned site/R/E/comparison references; it must not supply manual Q. WordPress may write only inbox. Profile, worker code, state, workspaces and report must not be writable by the WordPress account. Mount report read-only. Never install signing keys on WordPress.

Run `python3 tools/rbr-kit-preparation-worker.py --config /operator/config.json --allow-disposable-lab`; `--once` processes one pass. Configuration and runtime isolation are operator tasks. The current CLI is experimental-S3/generated-data scoped, not a general production backend. No permanent second EC2 is required, but privilege separation remains required.

## Failure and resume

The worker freezes receipt and profile in its private job directory; resume uses the same directory and CLI ledger. No automatic retry. After failure/interruption the screen offers an explicit next attempt. The existing CLI rechecks the input, fixed versions and retention. An unacknowledged PUT blocks the job for operator reconciliation, never a blind resend. Do not delete requests or journals to bypass this check. A pending request may be submitted again without duplicate execution. Worker flock and CLI workspace lock prevent concurrent execution.

Report freshness is 90 seconds. Long CLI execution can age a running report and disable requests; this is not proof of failure. Progress currently identifies the whole preparation stage, not percentage or per-object progress. Diagnostic categories are shown without private stderr, credentials or host paths; detailed logs remain operator-only. The latest 20 local operations are selectable. Profile changes create a different job identity and do not silently reinterpret old requests. Existing old-profile requests remain preserved.

## Validation boundaries

Contract tests cover duplicates, explicit resume, unknown PUT refusal, changed profile, malformed/symlink requests, stale reports and result binding. Dedicated UI integration uses a generated saved-history fixture imported from the earlier experimental editor receipt, not a new production edit. It exercises real WordPress permissions, browser selection/failure/resume, and the unchanged generation-kit CLI against experimental S3. This does not claim a new full editing or signed reconstruction trial.

日本語：管理画面の「ツール → 復旧キットの準備」から保存済み世代を選びます。S3保存完了後は「独立署名承認待ち」で止まり、承認は従来の別操作です。失敗・途中停止からは同じ入力・作業領域で明示的に再開します。結果不明の書込みは再送せず担当者確認になります。稼働中の長い処理でも報告が90秒以上古くなる場合があり、細かな進捗率は未対応です。外部設定・権限分離は必要で、本番用の自動導入ではありません。

## Recorded dedicated result

The dedicated browser requested preparation, displayed an injected pre-network failure, explicitly resumed the same generation and displayed stored-awaiting-independent-approval. The unchanged CLI prepared a real experimental S3 kit with the same request-derived Q; no uncertain PUT remained. Subscriber/anonymous access was denied and generated page/projection state stayed unchanged. Trial containers were removed; the existing interactive demo was preserved. See `evidence-public/kit-preparation-console.json`.
