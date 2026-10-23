# Site-materials 0.2.0 ZIP validation

This candidate packages the multi-material editor in the installable plugin and the worker/shared projection in the operator kit. Existing enrollment is opt-in. There is no automatic legacy-schema conversion.

Validation executes from the extracted frozen kit: fresh plugin ZIP installation, upgrade from the frozen alpha.5 plugin, and reinstall/update while a save is pending. Check plugin byte identity, administrator/subscriber behavior, pages, media, options, Cron and external request/report/journal bytes. The persistent S3 double is used for lifecycle fault injection; the independent real-S3 evidence is linked in README.

Results and ZIP SHA-256 values are recorded separately after completion, so the tested archives are not rebuilt to insert their own results. Production changes, cloud replays, public activation and automatic signature renewal are outside this task.

## Final result

PASS: fresh installation, published alpha.4 upgrade and alpha.5 candidate upgrade each completed 24 browser checks, including an update while a save was pending and exact resume afterward. Plugin ZIP bytes were checked after initial installation. Settings, legacy-history fixtures, Cron, posts/postmeta and pending request/report content were preserved. Legacy fixture preservation is not a claim of schema conversion or new approval.

The final extracted kit passed 19 material/worker tests. The previous material runtime's generated generation and four stored files remained intact while the new worker extended its history. The final kit also reconstructed seven assets in a fresh private WordPress, matched request-derived expectations and passed the rollback check; side-effect attempts were zero. This lifecycle trial used the persistent S3 double and performed no new cloud writes. Actual S3 evidence remains separate.

A first packaging attempt exposed a version-check dependency on list order, corrected before archives were built. The first HTTP update trial failed with root-owned updater directories. Aligning dedicated wp-content ownership corrected the harness; the plugin hash did not change. No production permission changes were made.

[Machine-readable final record](../../evidence-public/site-materials-zip-validation.json). This result/evidence entry was added after freezing the ZIPs; runtime files and the packaged README were not changed or repackaged afterward.

| Artifact | SHA-256 |
|---|---|
| ozeki-wordpress-resilience-0.2.0.zip | `54e0a5996138564d7c66c4919dda862667d901fe898ac6ff000b7390df79937c` |
| owr-development-kit-0.2.0.zip | `071b02af966b40b81a2c72efb9d1bcb7518270bcc3571cf4975f49d595bf36c4` |
