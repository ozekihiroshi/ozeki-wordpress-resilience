# Isolated CF7 input preservation regression

`run.py` provisions disposable dm Docker containers on an internal network, submits synthetic CF7 feedback, exercises the real product capture/queue/Store/reconstruction code, and removes its containers, volumes and network in finally. The fixture supplies only Plugin configuration, file-backed object transport, fault injection and a mail sink. No S3 or production mount is used.

Deployment directory: `/tmp/flamingo-input-preservation-20261128`.
Place these fixtures there, an unmodified previous-main SiteSnapshot as `OldSiteSnapshot.php` (class renamed only), a current `product/` copy of `packages/markdown-m1/{src,tools,tests}`, and the official CF7/Flamingo ZIPs. The runner uses the already provisioned WordPress core/wp-cli cache at `/tmp/owr-community-rc23-roundtrip-20261128` and the dm Docker socket shown in the script. Do not point it at a production WordPress tree.

Run `sudo -n python3 /tmp/flamingo-input-preservation-20261128/run.py`. Inspect `result.json`: require `all_checks_passed`, all `snapshot` and `reconstruction_retry` checks, no `error`, and empty `cleanup_errors`. HTTP receipt-view checks inspect authenticated server-rendered HTML; they are not browser JavaScript tests. The interruption cases deliberately exit PHP at the argument filter, and do not claim to test every possible machine power-loss instruction boundary.

The included renamed reader is comparison code from the earlier main, not deployed product code. The prior output-based reconstruction fixture remains historical investigation evidence; this fixture validates the new input-based contract.
