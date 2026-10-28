# M1 completion report — 2026-10-24

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

**Decision: the twelve specified M1 acceptance cases passed in the dedicated generated-data environment. This is M1 completion, not completion of the entire charter or a production deployment.**

Product ZIP: `ozeki-wordpress-resilience-0.3.0-m1.zip` (byte-identical to tested candidate3), SHA-256 `73d71109c8a3b41c637f460937a4f7079108e40c473dc152a102042f7d4c0dba`, 7,298,852 bytes.

## User functionality delivered

- Normal Ozeki Markdown Documents editor: publish and update with complete `.md` preservation before confirmed WordPress application.
- Stable document UUID and independent complete versions; ordered successful asset history in S3. No per-edit whole-site inventory or content deltas.
- Tools → Resilience: storage settings, formal history, document/version selection, pending-history resume and restore results.
- Fresh WordPress reconstruction using S3 history and pinned originals. Preserves raw source, title, slug, status and stored dates; maps recorded document URLs in rendered links without changing raw Markdown.
- An S3 failure prevents the protected WordPress write. Failed/incomplete application rolls back. Formal-history failure after a successful WordPress commit is visible and resumable.

## Measured acceptance

Final run: `/home/ozeki/.local/share/owr-md-m1-20261024-live02`. Collected evidence: `D:/workspace/wp-rescue/release-readiness/m1-20261024/live-acceptance/`.

| Requested case | Observed result |
|---|---|
| 1. Create and publish A | Passed through the ordinary Markdown admin editor and Publish button. |
| 2. Direct S3 raw retrieval | Passed; downloaded the fixed-version `source.md` without a reconstruction decoder. Content-Type readback is `text/markdown; charset=utf-8`. |
| 3. Multiple A updates | Passed; A has five complete versions; B has two. Seven formal operations in order. |
| 4. Mermaid, formula, code | Passed; canonical raw bytes and SHA-256 retained, including Japanese code text. Browser form submission uses CRLF; the test compares the submitted bytes, not an LF-normalized file. |
| 5. Publish B | Passed; B was also updated. |
| 6. A/B relationship | Passed for ordinary Markdown links to the documents' recorded canonical URLs. |
| 7. S3-original failure | Injected failure blocked application, preserved the previous source and added no formal version. |
| 8. WordPress application failure | Injected incomplete source application was rejected and rolled back. Abrupt PHP termination before confirmation also rolled back. Neither became formal history. |
| 9. Source loss | Removed the source WordPress and its tmpfs database containers before creating the target. No source DB, operational outbox or source settings were transferred. |
| 10. Fresh WordPress | Installed both plugins on a different WordPress/DB and configured the S3 prefix. |
| 11. Restore A/B | Selected the latest formal version of each in the admin page and reconstructed from S3. |
| 12. Compare | Raw source, title, slug and `publish` status matched independently prepared expectations. The rendered A→B link points to the new host and opens B. |

Additional checks: A has one stable UUID across its versions; B has a distinct stable UUID; stale editor submissions are rejected; formal-history write failure resumes the same order/key; all seven directly downloaded raw hashes match their S3 history references. Raw/history Object Lock readback has the same GOVERNANCE cutoff (`2026-11-29T02:22:04Z` for the sampled operation). No retention extension or existing-object mutation was performed.

## Charter attainment

- Articles 1, 2: the Markdown slice of normal operation and recovery after original-server loss is demonstrated; not all WordPress asset types.
- Articles 3, 4, 5: independent full `.md` originals plus metadata; no unnecessary conversion or content deltas.
- Article 6: only verified successful protected operations enter formal history; interrupted/prepared files remain separate.
- Article 8: document/version selection is available; whole-site point selection is not claimed.
- Article 9: the first complete Markdown Documents path is implemented and exercised.
- Articles 12, 13: WordPress plugin + S3, no standing recovery server and no Backup for S3 dependency.
- Article 14: direct raw use and new-WordPress reconstruction verified. Checkpoint-based site recovery remains later scope.
- Article 7, broader Articles 10/11 and the entire Article 15 are **not** claimed complete by M1.

## Limits and unperformed work

No open failure remains among the twelve stated test cases. This does not mean every deployment, failure timing or plugin combination was tested.

The interval between WordPress commit and independent formal S3 history remains explicit: if the original server is lost during that interval, the operation is unconfirmed from S3 alone. The system restores confirmed history, rather than inferring success from a prepared original. The local pending option is an operational retry outbox, not recovery authority. A pending record whose current WordPress fingerprint no longer matches is not blindly certified.

M1 exclusions remain: scheduling state/automatic protection at scheduled publication, unpublished-draft recovery, all standard post/page paths, arbitrary external plugins, business data, periodic Checkpoints, whole-site provisioning/network cutover, legacy cleanup and advanced monitoring. Quick/bulk/delete/import/API paths outside the full Markdown editor are not automatically protected; they are not prohibited. Existing documents are not bulk-enrolled retrospectively. User accounts/author-account mapping and arbitrary old URLs/embedded plugin-specific relations are not restored. Each restored document is assigned to the recovery operator by normal WordPress insertion.

Infrastructure exposure is the administrator's responsibility. There is no all-draft conversion, product-specific publication approval or external-publication prohibition gate.

## Test infrastructure versus product runtime

Tested: WordPress 7.1.3, PHP 8.3.35, MariaDB 11.8, Markdown Documents 0.1.1 ZIP (SHA-256 `9291771f6fcd286341b089887674ed89f3add1ad047852e7af64be035e788b2f`), Chromium through the existing WebDriver test adapter. Product minimum PHP 8.1 / WordPress 6.4 is declared but the complete version matrix was not exercised.

The real S3 test used the existing experimental writer/reader roles through a **test-only authentication transport**. Credentials stayed on their hosts; no IAM changes were made. This authenticated transport replaces the SDK handler only in the test MU-plugin. The product ZIP contains no Python, SSH helper, shared bridge or test worker. It uses AWS SDK for PHP 3.392.1 and its normal credential provider. Hosting-specific direct default-provider IAM setup has not been deployment-tested here and remains an installation check; this report does not present the test transport as the production configuration. The bundled SDK matches `composer.lock`.

New runtime requirements are the explicitly selected Markdown Documents dependency and transactional InnoDB/named-lock support. AWS SDK already existed in the repository and is reused. No extra service or database has been introduced.

## Defects and evidence classification

- **Product defect fixed:** document identity was converted to boolean on updates. It is now retained as a string and refreshed after the writer lock. Stable/distinct identity assertions were added. Candidate1/local intermediate passes are superseded; candidate1's live attempt was deliberately stopped and its S3 objects preserved.
- **Environment:** Docker's automatic network pool was exhausted. A non-overlapping dedicated subnet was selected, without deleting existing networks.
- **Test foundation:** corrected read-only bootstrap mounting, duplicate include/plugin-discovery caching, reused the available WebDriver adapter instead of an unavailable Python Selenium package, and corrected textarea-property and line-ending comparisons. These are not plugin defects.

All M1 test containers/networks were removed after the final pass. Existing experimental S3 objects, research code/evidence, the original uncommitted research changes and production systems were preserved.

## Next milestone

First validate normal server credential provisioning in the intended hosting setup. Then extend the independent product contract deliberately: existing-document enrollment and deletion/status transition coverage, followed by periodic Checkpoints and additional standard WordPress asset adapters. Do not reintroduce old research workers or publication gates to obtain those features. No release, production rollout or GitHub merge was performed in M1.
