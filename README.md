# Ozeki WordPress Resilience

English | [日本語](RAADME-jp.md)

**Preserve WordPress information assets in S3 and reconstruct the supported site state in a new WordPress after losing the original server or database.**

Resilience is for WordPress maintainers who need independently stored content and an explicit recovery history. The operating database is not the only recovery source. Complete originals, metadata and confirmed operations remain in S3; recovery uses a trusted initial snapshot or independent Checkpoint plus later confirmed history.

This is on-demand reconstruction, not continuous replication or an infrastructure backup. It neither provisions servers nor switches DNS. A permanently running second EC2 instance is not required; an administrator prepares a suitable recovery WordPress when needed. Ozeki Database Backup for S3 is a separate product, not a dependency.

**Start here:** [package identity, protection scope, untracked changes and minimum source/destination setup](packages/markdown-m1/docs/start-here.md). Formal release remains deferred; use the candidate identified below.

## Current package

The product is **0.3.1** (`packages/markdown-m1`). This candidate is `ozeki-wordpress-resilience-0.3.1-save-verification-final.zip`, including the consolidated bilingual documentation and native article deletion, featured-image and category/tag support. Identify it by filename and the SHA-256 in its accompanying validation record. Formal release is deferred. The root 0.2.0 research plugin is not the current product.

## Design and recovery boundary

1. **Establish a trusted starting point.** The administrator judges the existing site suitable, pauses editing and creates a complete initial snapshot. It contains supported content, files, presentation state and selected runtime software.
2. **Save complete asset versions during normal use.** Markdown stays readable `.md`; native post/page bodies are complete HTML; supported adapter records use JSON; media remains files. Each update saves a complete version of the affected asset, not a content delta or a new whole-site inventory.
3. **Confirm successful operations in S3.** Protected article saves store the original before WordPress application. Native article detail/deletion operations, comments and the supported third-party adapters capture completed operation data instead. In both cases, WordPress persistence, S3 storage and formal-history confirmation must succeed before an operation is recoverable.
4. **Create independent Checkpoints.** The complete-site Checkpoint uses the prior S3 baseline and confirmed history, not a fresh read of the live site. It contains its own required resources, rather than only an inventory referencing old ancestors.
5. **Reconstruct when requested.** Download and verify the selected complete baseline and its subsequent history, then replace supported content on a prepared destination. The old server, old DB and local pending queue are not recovery inputs.

The administrator-trusted initial state and accepted save data are design assumptions, not malware-free certifications. Fixed S3 Version IDs and hashes verify stored identity; they do not prove that submitted content was harmless. The full baseline also captures selected theme/plugin code and content-table records as portable files/JSON; reconstruction is not a promise to reinstall every component from a clean official distribution.

Only **confirmed S3 formal history** extends a trusted baseline. Prepared originals are not automatically adopted. If the source is lost before confirmation, omit that operation: an unconfirmed new article is absent, and an unconfirmed update leaves the previous confirmed version.

Saved publication state, including `publish`, is reproduced. Internet exposure, server/network access and DNS remain administrator decisions. There is no product requirement to convert everything to drafts or obtain a separate publication approval.

## Supported content and plugins

| Source | Recorded and recovered scope | Important limits |
|---|---|---|
| WordPress Posts and Pages | Standard create/publish/update, body, title, slug, recorded attributes, parent/order, discussion settings, Trash/untrash, permanent deletion, featured-image set/replace/remove and category/tag assignments | No complete draft/scheduled-publication guarantee; global term administration, arbitrary metadata and menu/front-page/sticky deletion side effects excluded |
| Local images | Supported upload originals before registration; referenced originals/generated sizes, attachment information and alt text bound to an article version | JPEG/PNG/GIF/WebP/AVIF; 32 MiB per file. Unused media, external/CDN assets and arbitrary binary overwrite tools are not tracked |
| Core comments | Addition, edits, moderation, Trash/untrash, permanent deletion, replies and approved counts | Completed-operation capture; restore through site-wide recovery, not individual text recovery |
| **Ozeki Markdown Documents** | Normal editor; complete Markdown source, title, state and supported document links; Mermaid, math and code syntax preserved | Separate plugin required for Markdown and the current supplementary text-recovery path. Rendering needs compatible plugin/runtime; arbitrary external links and plugin relations are not a general migration guarantee |
| **Contact Form 7** | Completed form definitions and deletion, referenced form relationships | No mail replay; submission attachments and arbitrary extensions excluded |
| **Flamingo** | Received inquiries, fields/channels, later edits, spam/ham, Trash/restore and permanent deletion | No address-book or attachment recovery; request-end capture; deleting a form does not delete its inquiries |
| **WP-Members** | Core subscriber accounts, configured fields, approval, core settings and post/page restrictions; saved password hashes enable login | No privileged/custom roles, paid extensions, CAPTCHA secrets, sessions or profile-file uploads. Unrelated destination account collisions are rejected; administrators preserved |
| **TablePress** | Core tables, IDs, cells, options/visibility, display settings, add/update/delete and ID changes; article shortcodes | No premium modules, arbitrary external imports, personal editor preferences or same-table concurrency guarantee; restored custom CSS uses inline mode |

Tested optional versions include CF7 **6.2.3**, Flamingo **2.6.4**, WP-Members **3.5.8.1** and TablePress **3.4.1**. They are separately installed, not bundled in the Resilience ZIP. Capture a new trusted baseline after changing recorded runtime software; version compatibility is not inferred from a successful earlier test.

The **initial snapshot** also captures supported uploads (including the tested PDF), theme/parent theme, menus, templates, navigation, global styles and selected settings. This does **not** mean later changes to those resources are automatically tracked. Theme/menu/template/global taxonomy administration changes and unsupported plugin settings need a new trusted baseline. Not every installed plugin is covered.

## Prepare and use

1. Install the dedicated product ZIP in WordPress. The plugin declares WordPress 6.4+ and PHP 8.1+; this is not a test claim for every combination. The tested CF7 6.2.3 requires PHP 8.3+. Use InnoDB for managed content tables, ZipArchive and writable resource directories. Install the plugins required for the content you use.
2. Configure normal AWS SDK credentials on the server, preferably an EC2 instance role where available. No SSH credential helper, Python worker, shared bridge, Docker or custom editor is required by the product. Docker was used only as a test environment.
3. In **Tools → Resilience**, set bucket, region, dedicated prefix ending in `/` and optionally expected account owner/retention days. Enable S3 versioning. Specifying Object Lock retention requires a suitably configured existing bucket; the plugin does not configure IAM or bucket policies.
4. Grant prefix-scoped listing, fixed-version reads and writes (`ListBucket`, `GetObject`, `GetObjectVersion`, `PutObject`); Object Lock writes additionally require `PutObjectRetention`. Normal saving/recovery needs no delete or retention-bypass permission. Use one writing WordPress per prefix; the destination can use read-only S3 access.
5. Resolve pending history, pause source editing and create a trusted **complete site initial snapshot**. Enable protection for subsequent supported operations. Continue using normal WordPress/plugin interfaces.
6. Use the **site-wide** controls to create a manual complete Checkpoint. The older supplementary asset Checkpoint is not a complete site snapshot. Scheduled execution remains deferred.
7. Prepare a designated destination with a different URL, compatible WordPress release line, required plugins and S3 access; disable its write protection. Under **Site-wide recovery — primary workflow**, select a complete snapshot/Checkpoint and use **Restore complete site**. This replaces destination content and presentation state; do not run it on an unrelated active site.
8. Inspect the recorded result and verify content and required behavior. The administrator decides network exposure separately. When WP-Members moderated registration is used, verify that the designated administrator is activated on the source at setup and on the destination before recovery. Restoring membership settings does not activate destination administrators. After recovery, verify a fresh sign-in through the standard WordPress login screen; an existing session is not sufficient. Keep member moderation and other accounts unchanged.

**Individual recovery is supplementary:** select one formal version per asset under **Confirmed formal history / Individual recovery**. It restores text/attributes and matching identities while leaving unrelated content intact. It does not restore media files, themes, menus, comments or plugin-adapter state; use site-wide recovery for those.

## Failures, retention and limits

- Protected article original-storage failure prevents confirmed WordPress application; application/verification failure rolls back managed transactional data. Native editing keeps WordPress's standard editing controls; the additional stale-form token applies to the Markdown full editor.
- For post-success adapters, the source change can already be visible when S3 fails. **Resume history** retries frozen pending data; article confirmation checks the applied state. Do not claim all adapters intercept before the source write.
- A surviving source can resume pending history. Source loss with pending history does not make the final unconfirmed change recoverable. Cross-system atomic commit is not claimed.
- Keep the complete selected Checkpoint and every resource/history record needed after it. Older ancestors are unnecessary only once an independent complete recovery point and its tail are safely retained. Do not prune required versions with an unrelated lifecycle rule.
- Cleanup is optional and disabled by default. The existing supplementary asset-path cleanup has contract tests, not real-S3 deletion acceptance or a general complete-site cleanup guarantee. Do not infer scheduled complete-site operation from an asset-path timer. See the separate [asset Checkpoint/cleanup scope](packages/markdown-m1/docs/checkpoints.md).
- Source text is limited to 5 MiB valid UTF-8 without NUL. History listing scans the dedicated prefix and targets small deployments. Multiple writing installations and arbitrary concurrent changes to the same asset are unsupported.
- No universal plugin compatibility, server provisioning, network cutover, complete scheduling-state recovery or automatic replica synchronization. Source AWS/SMTP configuration, administrator credentials and sessions are not imported. WP-Members subscriber password hashes are an explicit supported exception to exclusion of account credentials.
- Recovery verifies resources before replacement and rolls back handled write failures. Process-kill recovery and automatic rollback after abrupt termination are not accepted guarantees. Arbitrary external side effects during save and untested object-cache combinations are not covered.

## Evidence and issue classification

See the [installation and ZIP update procedure](packages/markdown-m1/docs/install-update.md) and [later standard-admin browser update acceptance](docs/releases/browser-zip-update-m1-031.md). The validated 0.3.1 ZIP replaced a prior same-version trial deployment through Upload Plugin / Replace current with uploaded; settings, history 68, empty pending queues and recovery results were preserved. A later [nonempty-queue browser update](docs/releases/pending-zip-update-m1-031.md) preserved the same article and native-detail operations, then resumed them as formal history 69–70 with pending work cleared. This accepts those two operations, not arbitrary adapter queues or version migrations. The initial premature capture was corrected in the test procedure; no product fix was required. Upload limits, file-modification policy and mixed file ownership were environment setup issues, not product code corrections. Earlier extraction/overwrite acceptance is separate. The earlier browser-update evidence refers to the editor-save-final ZIP; the site-retention-final packaging check is separate.

[Combined final-ZIP acceptance](docs/releases/combined-final-m1-031.md): fresh install and update preserved settings/history; both installations reconstructed one real-S3 Checkpoint through 21 plus confirmed history through 29. Posts/Pages, images, comments, forms/receipts, member login/restrictions and tables matched. ZIP installation tests used extraction/activation and overwrite update, not browser Plugin_Upgrader. PHP 8.1/8.3 contract CI passed for the PR #26 code.

[TablePress browser acceptance](docs/releases/tablepress-browser-acceptance.md) additionally covers standard-editor add/update/delete and recovered search/sort/pagination. It does not establish browser acceptance for every adapter. [Native editor acceptance](docs/releases/native-m1-031.md) covers standard editing and images in Chrome; the in-app browser's blank editor iframe is a separate unresolved browser issue.

**Product correction:** CF7's exact known deny-all `uploads/wpcf7_uploads/.htaccess` is preserved. Other control/executable files remain rejected. **Environment/test infrastructure:** dm memory limits, proxy/fixture URL configuration, a reused test DB prefix and standalone test paths are recorded separately; they are not new product dependencies. Mail sending, scheduled execution, real-S3 cleanup and formal release remain deferred.

## Detailed documentation and history

[Complete site recovery](packages/markdown-m1/docs/site-snapshot.md) · [Comments](packages/markdown-m1/docs/comments.md) · [Forms](packages/markdown-m1/docs/forms.md) · [Membership](packages/markdown-m1/docs/members.md) · [TablePress](packages/markdown-m1/docs/tablepress.md) · [Combined scope](packages/markdown-m1/docs/combined.md)

[Preserved historical README and research instructions](docs/archive/readme-before-product-consolidation-20261024/root-en.md). Old 0.2.0 workers, private previews, draft-only targets and signing experiments are not current product requirements. Historical evidence remains available without defining the current product's completion conditions.

## Native article details

Permanent article deletion, featured-image selection/replacement/removal and category/tag assignment/removal now join confirmed S3 history and site-wide replay. The extension captures successful final operation state; it does not change article-body S3-first saving. Required thumbnail files and new category ancestors are preserved. Included in this candidate. Global taxonomy administration, menu/front-page/sticky cleanup and arbitrary metadata remain excluded. See [scope and measured acceptance](packages/markdown-m1/docs/native-details.md).
## Recovery result display

The site-wide result shows success, failure or completion unconfirmed; the exact Checkpoint key and S3 Version ID; the Checkpoint history boundary and subsequent applied history range/count; restored post records and files written/replaced. Detailed JSON retains the latest attempt and last successful result. Post counts include all post types, not only public articles; unchanged files may be reused, so zero writes does not mean no recovered files. Failure/unfinished attempts do not reuse prior success counts and do not prove zero changes or completed rollback. A missing Checkpoint listing is reported as unavailable, not inferred. This local administrative result is not S3 formal history and is not a complete audit log.


## Save status

The admin screen reads confirmed S3 history once and shows the latest sequence, time and asset separately from local pending operations and recorded errors. Resume history reuses the existing recovery queue; a read failure is unknown, not empty history. No pending queue does not prove protection of unsupported operations. Included in the save-status-final candidate. Recorded errors may be old or absent; the display is local administrative feedback, not a durable audit log. Unconfirmed operations remain excluded from recovery.

[Validated ZIP / 検証済みZIP](release-candidates/20261025-save-verification/ozeki-wordpress-resilience-0.3.1-save-verification-final.zip)

See the [save-history resume procedure](packages/markdown-m1/docs/save-resume.md) and [measured acceptance](docs/releases/save-resume-acceptance.md): after original storage, a test-only formal-history PUT interruption left history at 56 and two pending records. Browser resume confirmed the same operations as 57–58, cleared pending work and recovered the display. This was not an actual AWS outage or a test of every failure mode. The earlier documentation-only follow-up did not modify its ZIP; this candidate includes the subsequent editor fixes below.

## Standard editor save corrections

The editor-save-final candidate displays a structured save-failure reason in the standard editor. A Save may send both a REST body request and a legacy meta-box request; the latter omits a body already matching confirmed S3 content and attributes. Identical native detail state, including media bytes, is also omitted. Changed or unconfirmed state remains protected; unavailable equality reads preserve the pending operation. This is not general request deduplication or concurrent-writer support.

Browser acceptance on the existing trial article confirmed an original-PUT rejection retained the old body, displayed the reason and left history at 67; retry after removing the test interruption confirmed one changed body as 68, matching S3, with no pending history. This was not a real AWS outage. Flamingo independently refreshes contact dates on profile updates; WordPress editor preferences use that user-update path. This third-party behavior was not changed, and the earlier individual request cannot be retrospectively proven. Existing contacts/members/content stayed unchanged during the article-only follow-up.

## Recovery preflight and history 68 acceptance

Complete-site recovery replaces the destination content set; destination-only posts, drafts and auto-drafts are not implicitly retained. Before replacement, compare both directions: source-only records to add, matching IDs with changed fields, and destination-only records to remove. Include every post type/status, not only published posts. Review or separately preserve destination-only content before proceeding; individual text recovery has different behavior. This comparison is currently test/operational tooling, not an automatic product UI gate or a complete metadata/file impact assessment.

The existing Checkpoint through 33 plus formal history through 68 reconstructed trial article 37 with an exact S3-original body match and matching title, slug and `publish` state. The first preservation check detected removal of one destination-only empty auto-draft. The test preflight had missed that direction; the product performed its documented complete replacement. The exact backed-up draft was restored separately, and final existing-content/member checks passed. This does not establish automatic draft preservation. No new browser recovery test was performed; this acceptance used the existing product recovery method and direct comparisons. See the recovery procedure for the preflight checklist.

### Complete-site retention preview (site-retention-final candidate)

The administration screen can now list retained Checkpoints and assets, potential deletion candidates, and reasons deletion cannot be established. It uses the configured recovery-point retention days and S3 fixed-version `LastModified` in UTC; the highest confirmed-history boundary is always retained together with its required tail. Nested media references are included. Article and shared pending operations stop calculation. This is a read-only preview, not a deletion action or a verification of delete permissions.

If `s3:ListBucketVersions` is unavailable, current fixed versions are inspected and required assets can still be displayed, but hidden older versions remain unassessed and no deletion candidates are certified. Unknown objects remain protected; legacy asset snapshots, ambiguous versions, missing references or history gaps require review. Object Lock/Legal Hold inspection failures never establish deletability. The legacy deletion path is blocked when complete-site snapshots exist. No scheduling or actual deletion has been added. Large inventories require synchronous S3 reads and may reach hosting request limits.

## Selected recovery point — point-time-final candidate

The site-wide recovery screen now accepts a Checkpoint and an inclusive formal-history end number. It applies only that range, rejects missing required history/resources before replacement, and displays requested and actual boundaries. Checkpoint-only recovery is supported. Timestamps help selection; a formal record is not necessarily an entire user edit. Theme/menu changes outside recorded adapter scope still require a new trusted baseline. Included in the point-time-final candidate. Standard-browser acceptance selected Checkpoint 33 with ends 67 and 68 and verified both result boundaries and the corresponding article bodies. The selectors reset after completion; use the recorded result to identify the applied point. ZIP fresh-install and same-version extraction-update checks are separate from that browser acceptance.

## Recovery failure detection — recovery-errors-final candidate

Complete-site recovery checks database START/COMMIT failures and verifies persisted settings, origin metadata, recovery results and attempt records. Unchanged values are accepted. A caught failure terminates with an escaped HTTP 500 response showing the cause; it does not automatically continue or retry. If recording the failure also fails, the current response shows that error and warns that stored results may belong to an earlier attempt. Durable failure recording cannot be guaranteed when the database is unavailable. A failure after COMMIT may leave content applied; failure does not imply zero changes or completed rollback. No new rollback mechanism was added.

Focused acceptance used actual WordPress/database in the existing dm isolated environment, synthetic S3 assets and deliberately invalid SQL. It is not real AWS outage, connection-loss/unknown-COMMIT, browser or forced-process-stop acceptance. The final ZIP fresh/extraction-update checks preserve settings, confirmed history, synthetic pending records and results; pending records are not resumed. Previous browser recovery and ZIP-upload evidence remain separate.

## Separated originals — separated-assets-final candidate

New code uses a shared content/metadata partition for normal saves, initial snapshots and Checkpoints. Plain Markdown/HTML/media remain independently readable; known structured content (including table cells and inquiry values) is extracted into separate files. Unknown captured fields are retained. Included in this candidate. New records require this reader; the earlier recovery-errors-final ZIP cannot read the new format. Existing legacy assets remain readable without rewriting S3. The certification/activation policy is unchanged. See [format and verification limits](packages/markdown-m1/docs/separated-assets.md).

Real-S3 acceptance used existing community/dm hosts and standard EC2-role authentication: standalone originals from normal save, initial snapshot and Checkpoint; reconstruction from 24 fixed Checkpoint versions without the old environment. Package acceptance is separate: fresh activation and replacement of the previous ZIP, preserving settings, non-empty pending records and read-only S3 history. No new browser/all-plugin rendering or failed-operation resume trial is claimed. Unknown captured information is preserved, not newly certified. No automatic migration, deletion or release.

[Separated-format final ZIP acceptance](docs/releases/separated-assets-final-m1-031.md): fresh installation and replacement passed; read-only S3 checks and synthetic pending-state preservation are distinct from earlier browser and reconstruction tests.

## Recovery application rules — application-rules-final candidate

After PR #41, complete-site recovery now projects recognized attributes/settings after baseline-plus-history replay and before destination mutation. Unknown captured values remain in S3; the result lists items not automatically applied and their reasons without exposing values. Known invalid types stop recovery. Custom/extension settings, widgets and unrecognized theme settings can be withheld, so visual equivalence is not claimed for those configurations. Software activation policy is unchanged. See [rules and focused verification](packages/markdown-m1/docs/application-rules.md).

This candidate includes the application rules. Existing real-S3 acceptance restored seven records through history 1 from 24 fixed Checkpoint reads; originals were unchanged and 21 omitted paths/reasons were reported. This is separate from ZIP installation/update checks. Unknown/custom settings remain stored but may not be applied, changing appearance or behaviour. No new all-plugin runtime or browser acceptance is claimed.

[Application-rules final ZIP validation](docs/releases/application-rules-final-m1-031.md): fresh activation and replacement preserve settings, history, synthetic nonempty pending state and results. This is distinct from earlier real-S3 restoration and browser evidence.

## Original verification before history confirmation

This candidate re-reads the operation originals, metadata, split parts and referenced media using fixed versions and the existing S3 client before confirming formal history. A read/hash failure leaves the operation unconfirmed for the existing resume path. It also distinguishes body/detail pending state and records capture failures before queue registration. The status page reads history; it does not recheck all resources when displayed. Earlier histories are not retroactively verified. See [scope and verification](packages/markdown-m1/docs/commit-verification.md). No automatic retry, new worker or release.

[Save-verification final candidate and evidence](docs/releases/save-verification-final-m1-031.md): completed with separate fixture, real-S3-read/isolated-WordPress and ZIP installation/update scopes. Formal publication remains deferred.
