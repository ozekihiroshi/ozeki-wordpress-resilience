# Multi-material reconstruction console

This console belongs to `owr-site-materials-v1`, separately from the retained three-page signed console. It reuses fixed-version receive, request-derived Q and the shared WordPress projection CLI. No old three-page receipt, fixture generation, source database or signature approval is substituted for the selected material generation.

## Setup and operation

Use the existing guarded dedicated editor enrollment. Configure an external `tools/site-reconstruction-worker.py --config /private/recovery.json` beside the editor worker. Reuse `transport`, `work` (the existing writer journal/object scope), `bridge` and `prefix`; add `recovery_work` (a private dedicated folder outside WordPress), `target_label`, `wordpress_image` and `database_image`. Images must be locally present pinned `sha256:` IDs. Do not place credentials or runtime configuration in the web-writable bridge.

For experimental S3, recovery uses its own reader transport ledger under `recovery_work/reader`; it never shares the writer transport journal. The worker reads up to the newest 50 journal records and verifies committed material generations through the configured storage adapter. It publishes the fixed receipt, Q digest, asset summary and jobs at `bridge/reconstruction/status.json`; WordPress reads it and writes only small selected-generation requests under `reconstruction/requests`. Arrange the same restricted shared-directory permissions as the editor bridge. First run the worker so these directories exist. The worker must have Docker access; WordPress does not invoke Docker or a shell.

In WordPress open **S3先行編集 → 素材世代から再構築**. Select an immutable generation, review its fixed Version ID, Q digest and material list, then choose **選択世代を専用復旧先へ再構築**. Results include the selected generation, Q, verification outcome, reconstructed IDs and private target identifiers. Reads do not alter source content. Only administrators can read or enqueue, and WordPress REST cookie/nonce authentication applies. A stale report (over 120 seconds) or changed Q/profile refuses requests.

The worker fetches and verifies the selected generation again immediately before calling `site-reconstruct-private.py`, which reuses the dedicated target builder and `site-wordpress-apply.php`. It creates a new internally networked WordPress/DB pair, checks pinned images and no default network route, disables Cron and outbound application effects, applies as drafts, checks the expected logical state and idempotent replay. Successful private targets are retained for operator inspection. No public port, DNS change or production overwrite is accepted. The protected source may continue to exist during this test but its DB is never an input to reconstruction.

## Failure and lifetime boundaries

An identical generation/Q/profile request maps to one job. Repeated clicks do not create additional targets. A failed or interrupted job is not automatically retried; inspect the private execution log, bundle and `target-*/resources.json` first. A restarted worker marks a previous running job interrupted. It does not infer success or delete resources. There is no retry/cleanup/preview UI yet. The dedicated test harness removes only its own target resources after verification.

Target DB/files currently use private temporary Docker storage. These are inspectable disposable recovery targets, not durable production installations; restarting/removing them can discard reconstructed state. Cold runtime bootstrap, external-host placement, browser preview/public activation, a durable deploy target and loss of the generation-reference journal remain separate operational work. Runtime images come from the local cache. The report contains a Q digest and material summary, not the full expected document. Older than 50 journal records require operator-side selection tooling.

Storage integrity/retention checks and new-schema signature refusal remain unchanged; no automatic signature integration or approval renewal is added. Invalid/expired material generations are displayed as ineligible. This feature introduces no cloud PUT operations: it reads existing generations and creates isolated local targets.

## Validation

The dedicated browser trial passed 43 checks, including the existing editing flow and reconstruction of both the latest seven-material generation and the original four-material generation. Each result matched its selected request-derived Q. The trial used a persistent S3 double, not live S3. Nine worker unit tests and PHP request contracts passed. Menu registration ordering and JSON key-order dependence found during integration were fixed. A WSL helper-launch timeout is recorded separately as an environment issue with unresolved cause. See [validation evidence](../evidence-public/site-reconstruction-console-validation.json).

## Live S3 follow-up

The experimental S3 browser trial also passed 43 checks: continuous edits, pre-save failure with unchanged WordPress content, resume after an actual worker exit following S3 commit, selection of latest seven-material and initial four-material generations, exact Q matches, duplicate suppression, and stale-report recovery. Existing scoped signing roles, fixed Version IDs and retention checks were reused; no IAM or production settings changed. The trial targets were removed after verification; retained S3 evidence was not deleted.

The first reconstruction click occurred while the button was disabled and sent no request. After confirming zero requests, the same browser was continued by clicking the enabled button once. The harness now explicitly waits for enabled state; this is not an unassisted run of that revised harness. Full live-S3 catalog revalidation is slow and can temporarily make the report stale. This remains a product responsiveness limitation, separate from the harness timing issue. Executor failures/interruption were covered by worker unit tests; a real S3 outage was not injected. See [live evidence](../evidence-public/site-reconstruction-console-live-s3.json).

## Bounded catalog reuse

The worker now caches only the verified catalog summary in its private recovery directory, keyed by storage context and the full fixed receipt. It reuses the summary for at most 3,600 seconds and never beyond the generation protection deadline. Clock rollback invalidates the cached age. The screen exposes the original check time and protection deadline separately from report freshness. A fresh heartbeat does not claim a fresh S3 check. Unchanged catalogs perform no S3 GETs; new or expired entries receive full verification.

Execution always fetches the selected fixed generation and all its materials anew through the existing receive function, including retention, hashes and request-derived Q, immediately before target creation. The previous consecutive duplicate receive is removed; cached catalog data never authorizes execution by itself. Changes or loss of retention after catalog creation still block reconstruction. Signature policy is unchanged.

An unassisted live-S3 browser trial passed all 43 checks with the corrected enabled-button wait. Both seven-material and four-material selected generations matched Q. The unchanged seven-generation catalog measured 0.115 seconds with zero storage GET calls in this environment; this is a warm-cycle measurement, not a cold-start or network SLA. All 38 related regression tests passed. First-time/expired catalog checks and long reconstruction work can still delay report updates; the 120-second stale-report refusal remains. See [evidence](../evidence-public/site-reconstruction-catalog-cache-validation.json).
