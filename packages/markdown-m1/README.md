# Ozeki WordPress Resilience


**Unreleased candidate — conditional dependency:** In `ozeki-wordpress-resilience-0.3.1-readiness.zip`, native-only Baseline/recovery does not require Markdown Documents. Active Markdown Documents is included; if Markdown documents or originals remain while it is inactive, capture stops before saving. For Markdown recovery, prepare and activate the recorded compatible plugin first (tested 0.1.1). Published pre.2 is unchanged and still requires it at the admin Baseline entry. See the [candidate verification](docs/optional-markdown-verification.md).
**First-time users:** Follow the [installation-to-recovery user guide](docs/user-guide.md), including the first Baseline and daily operation. [AWS setup and complete replacement IAM policies](docs/aws-setup.md) are provided. The current published trial is [v0.3.1-pre.2](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/v0.3.1-pre.2). Released ZIPs are unchanged; use the online guide for current instructions.

[Questions about reconstruction](docs/recovery-faq.md): how IDs, serialized settings, versions, runtime dependencies and incomplete saves are handled, with evidence and conditions.

English | [日本語](RAADME-jp.md)

**Preserve the information you cannot afford to lose, so a lost or untrusted WordPress system is not your only route back to it.**

## 1. Why — Beyond restoring a backup

A backup can return a site to an earlier state after an accident or failure. After a compromise, a different question arises: **should the WordPress database and system state in that backup be restored as they are?** A successful restore does not, by itself, establish that the restored state is trustworthy.

The difficulty is not simply whether a backup exists. Valuable articles, documents, images and business records can be bound to the application, configuration and executable behaviour that managed them. If that system is lost or cannot be trusted, recovering the information can become dependent on recovering the system first.

Ozeki WordPress Resilience addresses that dependency: secure independent originals when information is created and committed, and retain an explicit basis for reconstruction. Ordinary backups remain useful. Ozeki Database Backup for S3 is a separate product, not a dependency.

## 2. Philosophy — Information assets before the system

**Losing a recovery resource can be irreversible. A reconstruction process can generally be attempted again.** Development therefore prioritizes preserving the information over making every recovery failure automatically repairable.

The architectural aim is to keep originals understandable and usable without the original WordPress or this recovery engine: full Markdown or HTML text, media files and readable structured data, with the attributes and relationships needed to interpret them stored separately. Each asset revision is a complete version, not a file-content delta. Preserving information and automatically applying it to a new system are separate decisions.

Reconstruction should use known asset types and explicit rules. Captured information outside those rules should not be discarded merely because the engine cannot safely apply it. Nor should a saved setting be imported blindly because it exists.

**This is a design discipline, not a claim of harmless data.** The administrator's trusted starting point and the accepted input at the saving boundary are assumptions. Separation, version identity and hashes do not remove malware or prove that submitted content is benign. The current implementation and its limits are described below; the architectural aim is broader than the current coverage.

## 3. Architecture — Originals, history, Checkpoints and reconstruction

1. **Establish a trusted initial snapshot.** The administrator judges the existing site suitable and pauses editing for capture. This supplies the starting resources for supported site state.
2. **Preserve independent originals.** Supported operations save complete asset versions in S3, with content and supporting metadata separated. Normal updates save the affected assets; they do not create a whole-site inventory each time.
3. **Confirm history.** S3 formal history records successful operations in order. For current history commits, the operation's originals and referenced media are retrieved by fixed Version IDs and checked before history is written. Stored originals or a successful WordPress write alone do not establish confirmation.
4. **Build independent Checkpoints.** A complete-site Checkpoint copies the required resources from the trusted S3 baseline and confirmed history. It is more than an inventory pointing to older ancestors. Keep the selected Checkpoint and all resources needed by its subsequent history.
5. **Reconstruct selectively on a prepared WordPress.** Choose a Checkpoint and an inclusive history end number. Reconstruct the supported state and apply recognized attributes/settings through adapters. Captured unknown information remains in S3; omitted items and reasons are reported. The old server, old database and local pending queue are not required recovery inputs.

### Baseline and Checkpoint: three principles

1. **The Baseline is the first independent recovery point.** Administrator-trusted initial capture reads the supported current WordPress state. Once saved, it is usable for recovery just like a complete Checkpoint.
2. **Normal Checkpoints use only preserved S3 assets and confirmed history.** They do not scan the live WordPress database or files for unrecorded changes. Local settings and pending-operation checks control execution; they do not supply additional recovery content.
3. **Recapturing current WordPress state creates a new Baseline.** Use the separate trusted initial-capture operation, not normal Checkpoint creation. Untracked changes are not silently incorporated.

Each complete point owns its resource set, not just links to older points. Creating the next point requires the selected S3 point plus subsequent history and referenced resources. Once confirmed, recovery at that new point requires only its own manifest and resources. Later recovery also requires the subsequent formal history and referenced assets through the selected end number; choosing the point's own `through` applies no subsequent history. Compatible destination software and supported application rules remain necessary.

The legacy Markdown asset-level snapshot and individual-text recovery path is separate; its snapshots are not whole-site recovery points.

Protected article bodies are saved to S3 before WordPress application. Comments, article detail/deletion operations and supported third-party adapters capture completed operation data instead. Their source change may already be visible while history is pending. Body and related operations can confirm separately; the product does not provide an atomic transaction across WordPress and S3.

If the source is lost before confirmation, that operation is excluded: an unconfirmed new article is absent; an unconfirmed update leaves its previous confirmed version. Site-wide reconstruction replaces supported destination state, so use a designated recovery environment. Individual text recovery is supplementary, not a substitute for site-wide reconstruction.

Saved publication state, including `publish`, is reproduced. Server preparation, network exposure and DNS remain administrator responsibilities. No permanently running second EC2 is required. Reconstruction is on demand, not replication.

## 4. Current Pre-release — What exists today

[GitHub Pre-release v0.3.1-pre.2](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/v0.3.1-pre.2) is a **trial distribution for technical WordPress maintainers**, not a stable release or a WordPress.org submission. Install its attached product ZIP, not GitHub's source archives. The plugin reports 0.3.1; identify the distribution by tag, full filename and [SHA-256 record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/prerelease-2-package.md).

**Current published Pre-release:** `ozeki-wordpress-resilience-0.3.1-pre.2.zip` packages the tested gfs-lock-read executable files with current documentation through PR #52. Published tag: v0.3.1-pre.2; the published pre.1 remains unchanged. See [release scope, evidence and limits](docs/prerelease-2.md). Use the exact filename and accompanying SHA-256, not display version 0.3.1 alone.

Fresh installation and update from the published Pre-release preserved settings, pending fixtures, history and results in isolated WordPress; this was extraction/activation testing, not browser upload.

<a id="supported-content-and-plugins"></a>

| Content / plugin | Implemented coverage |
|---|---|
| WordPress Posts and Pages | Standard publication/update, recorded body and attributes, Trash/restore/permanent deletion, featured images, category/tag assignments |
| Local images | Supported image originals and referenced files, attachment information and alt text |
| Core comments | Addition, editing, moderation, Trash/restore and deletion |
| Ozeki Markdown Documents | Full Markdown source, title/state and supported document relationships; math, Mermaid and code syntax preserved |
| Contact Form 7 / Flamingo | Supported form definitions and deletion; received inquiries, fields and subsequent state changes |
| WP-Members | Core subscriber accounts, approval, recognized fields/settings and viewing restrictions |
| TablePress | Core table data/IDs, recognized options, article references and add/update/delete operations |

Tested optional plugin versions include Contact Form 7 6.2.3, Flamingo 2.6.4, WP-Members 3.5.8.1 and TablePress 3.4.1. They are installed separately; compatibility with other versions is not implied.

Manual initial snapshots, complete Checkpoints, selected-history reconstruction, save/pending status and recovery results are implemented. Standard AWS SDK credentials are used; a Python worker, SSH credential helper, Docker or a Resilience-only editor is not a product requirement.

Existing evidence covers supported reconstruction, save failures/resume and installation/update. The latest representative trial confirms **actual S3 original PUTs → fixed-version GET/checks → actual history PUT**, for a normal WordPress API page save with a local image. Failure injection, real-S3 operation and ZIP installation are distinct evidence, not a claim that every plugin/browser/environment combination was tested. Detailed results are linked below.

## 5. Scope and Limitations — What this release does not promise

- **Original preservation is not sanitization.** No complete malware exclusion or unconditional recovery guarantee. Raw content remains raw content; known types and hashes are not proof of harmlessness.
- **The current baseline is not a clean-software installer.** It includes selected theme/plugin code and content-table records as files/JSON. It does not promise to fetch every component afresh from trusted distributions. Independent extraction of information is possible; recreating site behaviour still needs compatible WordPress, plugins and interpretation rules.
- **Supported scope is bounded.** Arbitrary plugins/extensions, all metadata, complete drafts/scheduling state and external/CDN resources are not covered. Theme/menu/template/runtime changes outside tracked operations require a new administrator-trusted baseline. Previously excluded information is not made preservable merely by the unknown-field rule.
- **Selective application can change appearance or behaviour.** Unknown captured fields remain stored but are not blindly imported. Current rules withhold widget settings, unrecognized theme settings and TablePress custom CSS/modules/commands, among other items. Supporting a plugin is not certification of every extension or setting.
- **Retention and access are conditions.** Use a versioned bucket, appropriate permissions, one writing WordPress per prefix and retain the required fixed versions. No promise survives arbitrary external deletion or lost access. Source text is limited to 5 MiB; supported image files to 32 MiB. Large-site throughput is not established.
- **Confirmation has a defined boundary.** Unconfirmed work is not recoverable after source loss. Old histories are not retroactively certified; the status page is not a current audit of all originals. Published pre.2 also retrieves every initial-snapshot/Checkpoint resource by fixed version before writing its manifest. The published v0.3.1-pre.1 does not include that change. Error diagnostics may be unavailable after DB failure or forced termination.
- **Operational automation remains limited.** Configured weekly occurrences, browser cleanup and scheduled automatic deletion have passed in the dedicated trial; see the [scoped acceptance record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/cleanup-browser-scheduled-acceptance.md). HTTP loopback triggering and repeated long-term schedules remain unverified; WP-Cron is not an exact-time guarantee. Retention preview is not permission to delete; legacy asset-only cleanup is not complete-site cleanup. No automatic recovery continuation, infrastructure provisioning, DNS switching or mail replay is promised.

Use the linked setup and adapter specifications for dependency versions, permissions and precise exclusions. Test-environment incidents, such as browser rendering or container memory constraints, are recorded separately from product defects and do not redefine the recovery goal.

## 6. Documentation — Setup, evidence and specifications

| Purpose | Documentation |
|---|---|
| Start using the product | [Setup and protection boundary](docs/start-here.md) · [Install / update](docs/install-update.md) |
| Reconstruct supported site state | [Site-wide recovery](docs/site-snapshot.md) · [History resume](docs/save-resume.md) |
| Understand stored resources and application rules | [Separated originals](docs/separated-assets.md) · [Recovery rules](docs/application-rules.md) · [History confirmation](docs/commit-verification.md) |
| Check adapter-specific scope | [Comments](docs/comments.md) · [Forms](docs/forms.md) · [Members](docs/members.md) · [TablePress](docs/tablepress.md) · [Native details](docs/native-details.md) |
| Find verification and historical detail | [Evidence index](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/product-evidence-index.md) · [Published package record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/prerelease-package-m1-031.md) |

This README describes published pre.2 and distinguishes the earlier pre.1 and candidate evidence. Published ZIPs remain unchanged; pre.2 includes snapshot verification, GFS scheduling and retention labels. The online user guide and AWS samples are later documentation, not additions to the released ZIP. Earlier research paths and accumulated test narratives remain accessible through the evidence index; they are not the standard product architecture.

[Distribution and interrupted-cleanup verification](docs/recovery-readiness.md): evidence boundaries and environment requirements.
