# 0.2.0 size-contract correction

The save/receive mismatch reported in PR #16 is corrected. A canonical asset may be at most 6 MiB (UTF-8 bytes including JSON structure), a stored object at most 8 MiB, and a submitted site at most 64 MiB. Image payloads still have a 4 MiB limit. These are simultaneous ceilings.

All assets are normalized and compressed before any PUT. The writer budgets the complete manifest, including request-derived Q, parent/approval fields, and 4 KiB for each canonical fixed-version reference. The transport must return references within that bound; unexpected transport results remain failures with journals retained, not blindly retried. The conservative manifest budget may reject otherwise small actual references. Size-invalid input creates no operation journal, changes no head, and writes no objects. Existing journals are retained. A corrected request can use the operation ID only when no earlier operation was started; unchanged retry/stale-head rules still apply.

Reader limits are not relaxed. Existing oversized generations remain rejected; they are not silently truncated or rewritten. The old original request must be reduced and submitted as a new valid edit where applicable; committed journals must not be deleted to force retry. Existing independent-signature conditions are unchanged.

Boundary tests cover canonical asset ceiling minus one/exact/plus one for ASCII and Japanese, complete manifest budget minus one/exact/plus one, the original failing example, a large later asset with prior history, corrected retry, and worker failure without object/head creation. Accepted cases are read back and compared with the submitted site. No cloud writes are necessary to prove rejection before the transport boundary.

Replacement ZIP lifecycle results are recorded after archive freeze in a separate evidence record. Prior v3 results/hashes remain historical evidence, not proof of this fix. No production changes or automatic publication are performed.

## Replacement ZIP results

PASS: the extracted v4 kit ran 25 material/worker tests, including boundary cases. Fresh installation and upgrades from alpha.4, alpha.5 and the previous 0.2.0 plugin each passed 24 browser checks, including a pending-save update and same-operation resume. Settings, history fixtures, Cron, posts/postmeta and bridge state were preserved. The former 0.2.0 external runtime's four stored/config files remained intact and its generation stayed readable while the corrected worker extended it.

A fresh private WordPress reconstructed seven assets from the persistent S3 double using only the final kit and received material bundle, matched the expected result and passed rollback verification with zero side-effect attempts. No production data or cloud writes were involved. Actual AWS verification remains the earlier separate evidence; this is not a new real-S3 run.

CI on 57f7005 passed on PHP 8.1 and 8.3, each discovering 843 Python tests with 54 explicit skips, followed by PHP contracts and distribution builds. [Machine-readable replacement evidence](../../evidence-public/site-materials-size-fix-validation.json). This result section/evidence was added after archive freeze. Neither archive was overwritten to embed its own results.

| Artifact | SHA-256 |
|---|---|
| ozeki-wordpress-resilience-0.2.0.zip | `54e0a5996138564d7c66c4919dda862667d901fe898ac6ff000b7390df79937c` |
| owr-development-kit-0.2.0.zip | `43f606032b6b6961397daf2f24ee5f291ad5d44f5ccf29c2ec8206ebf107a99b` |

The plugin ZIP is byte-identical to v3 because the defect was in the external worker. Deploy the corrected operator kit as well as the plugin; reinstalling the plugin alone does not install the fix. The old v3 operator kit remains preserved but is superseded for this workflow.
