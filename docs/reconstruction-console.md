# Reconstruction console (generated-data prototype)

> **研究・旧構成の資料 / Research and legacy reference.** 現行製品の導入手順ではありません。See [current distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md) and [導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md).

The opt-in external kit now provides `RbrReconstructionConsole`. It does not change the published alpha.4 ZIP or automatically enable reconstruction on a production site.

## Screen workflow

1. Open the protected three-page editor. Follow **保存世代・Q・署名承認・再構築の状態を確認**, or Tools → **再構築の状態**.
2. Review local operation / generation / request-derived Q metadata. Saved does not mean independently approved.
3. Review separately registered external kits, their exact generation reference, Q digest, independent approval and expiry. An operator must build/register the matching kit and obtain approval outside WordPress; this is not automatic.
4. Request a private reconstruction of an approved, fresh item. Only an item identity and token enter the inbox; the browser cannot choose commands, paths or approval policy.
5. Review the result: running, verified (existing executor passed Q comparison), failed or interrupted. No public site is activated. Repeated requests for the same token do not repeat execution. Failed/interrupted executions require operator review; deleting journals to retry is not supported.

## Configuration and trust boundary

Boot `RbrReconstructionConsole::boot($factory, $ids, $reportPath, $inboxPath)` from the explicitly installed external kit, alongside the existing protected editor. Require the class first. The factory is the existing `RbrWordPressSave` factory. WordPress may write only the inbox; mount the report read-only. Config, received kits, approval files and worker outcome directory must not be writable by the WordPress account. Do not put signing keys on WordPress.

Run `python3 tools/rbr-console-worker.py --config /operator/config.json --allow-disposable-lab` as the reconstruction operator. `--once` performs one cycle. Config schema is `owr-reconstruction-console-config-v1`, with absolute `inbox`, `state`, `report` paths and `items`. Each item has `item_id`, `origin`, exact `generation` reference, `trust`, `approval`, `signature`, `receipt`, `work`, `site_id`, `set_id`. The work path is a previously fetched fixed-version kit. The worker revalidates its bytes, pinned plan, signature, current root-owned trust registry and expiry before calling the unchanged `rbr-approved-kit.py` executor with `received=True`. It does not sign, extend approval or bypass the current registry.

The worker uses a process lock and an external durable outcome journal. Report age >90 seconds disables requests; long execution can also make the last report stale (not proof of failure). The outcome is retained after the worker stops. Admin capability and edit capability for all enrolled pages are required; WordPress REST cookie nonce protects requests.

## Current limits

This is a generated-data lab entry, not a production restore/publication service. Matching-kit preparation, independent signing, trust-registry provisioning and runtime isolation remain operator tasks. The earlier demo used a filesystem S3 protocol double and an unrelated imported real-S3 generation. A later dedicated trial connects the current editor to a fresh experimental S3 prefix. Its old mock journal is archived without treating mock versions as AWS versions; current page text and enrollment context are retained. This one-off generated-data re-enrollment is not a general migration feature. The existing executor creates disposable WordPress targets and compares Q; it does not leave a public reconstructed website online. Worker/service installation is explicit, not automatic. All inputs and states are preserved on failures; no automatic cleanup or approval renewal.

## Dedicated validation

Seven queue-worker tests and six PHP queue checks passed. Actual WordPress permission checks denied anonymous/subscriber access; the browser rejected a POST without a REST nonce. A browser request for the independently approved, previously fetched S3 generation 3 ran the existing executor twice; both logical results matched the request-derived Q, with zero external side-effect attempts. The browser displayed the verified result and disabled duplicate execution. Temporary reconstruction resources and scoped network rules were removed; the interactive editor remains.

Environment: a transient Wsl/Service/WSAETIMEDOUT interrupted final status polling; access recovered without restarting WSL. Root cause remains undetermined. Test infrastructure: the isolated browser initially lacked the loopback relay needed for port 18714; the harness was corrected. Neither event is counted as a plugin test failure or silently erased.

## Register the generation saved by this editor

Pass the actual applied `/owr-rbr/v1/save` response (including `expected_ref`) to the existing `rbr-generation-kit.py --generation ... --profile ... --work ... --execute-generated-lab`. Use a request-Q profile with only site/R/E/comparison references; do not author or substitute Q. After an independent operator approves the resulting fixed root and the kit has been fetched, `tools/rbr-console-register.py` verifies the existing approval and received kit, then compares the applied generation and expected-binding references exactly. It creates a new worker configuration; it refuses to overwrite an existing one.

Required flags: `--save-receipt`, `--received`, `--trust`, `--approval`, `--signature`, `--receipt`, `--inbox`, `--report`, `--state`, `--output`, `--item-id`, `--site-id`, `--set-id`. Run under the same independent trust-registry and isolated runtime arrangement as the approved CLI. No signing key is needed by registration or WordPress.

Registered items require a local match. The management screen identifies the corresponding saved generation and Q. Both the UI and request API reject an item that no longer matches the displayed applied history (latest 20 operations). The worker additionally pins the expected Q digest and still performs the unchanged approval checks. Older generations outside this bounded history need operator handling, not deletion of evidence.

Preparing a kit and obtaining independent approval remain external operations. The screen never auto-approves an edit. Prior successful outcomes remain historical results when the worker stops or an approval expires.

## Current-editor real-S3 validation

The current dedicated editor was switched to a new, read-only-preflighted experimental S3 prefix. Existing user edits were retained and the mock journal was archived separately. A browser added a test paragraph and saved one real generation. The actual HTTP request/response, journal Q and kit Q matched before signing. A separate root-only test signing account approved the new root (same host, not physical independence). Signed fetch retrieved 75 fixed objects and two pinned runtime archives into a fresh directory, while original asset and builder directories were hidden from the recovery namespace.

The same management screen displayed the local generation/Q match and submitted reconstruction. Both new WordPress runs matched the exact request-derived Q; side-effect attempts were zero. The screen displayed verified success and disabled duplicate execution. Thirteen Python contract tests and PHP queue/local-match checks passed. The reconstruction daemon and scoped network rules were cleaned up; the lightweight scoped S3 broker remains for the dedicated editor. Further edits require their own kit preparation and independent approval. No production changes, approval renewal or automatic publication occurred. Evidence: `evidence-public/current-editor-reconstruction-console.json`.
