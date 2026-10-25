# Ozeki WordPress Resilience

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

Protected article bodies are saved to S3 before WordPress application. Comments, article detail/deletion operations and supported third-party adapters capture completed operation data instead. Their source change may already be visible while history is pending. Body and related operations can confirm separately; the product does not provide an atomic transaction across WordPress and S3.

If the source is lost before confirmation, that operation is excluded: an unconfirmed new article is absent; an unconfirmed update leaves its previous confirmed version. Site-wide reconstruction replaces supported destination state, so use a designated recovery environment. Individual text recovery is supplementary, not a substitute for site-wide reconstruction.

Saved publication state, including `publish`, is reproduced. Server preparation, network exposure and DNS remain administrator responsibilities. No permanently running second EC2 is required. Reconstruction is on demand, not replication.

## 4. Current Pre-release — What exists today

[GitHub Pre-release v0.3.1-pre.1](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/v0.3.1-pre.1) is a **trial distribution for technical WordPress maintainers**, not a stable release or a WordPress.org submission. Install its attached product ZIP, not GitHub's source archives. The plugin reports 0.3.1; identify the distribution by tag, full filename and [SHA-256 record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/prerelease-package-m1-031.md).

**Unpublished distribution candidate:** `ozeki-wordpress-resilience-0.3.1-gfs.zip` includes fixed-version verification before snapshot confirmation and weekly/monthly/yearly GFS settings. Coincident schedules create one independent full point; each retention label is recorded and any active label retains it. Actual S3 writes/readback verified these properties in a dedicated test prefix. The existing role cannot list all versions: complete deletion eligibility and actual deletion remain unverified, not a demonstrated product defect. A separate real-time weekly-slot test subsequently confirmed an unchanged independent set, fixed-version verification before confirmation and the next reservation through the standard wp-cron.php entry point. HTTP page-triggered execution, later weekly/monthly/yearly runs and GFS browser operation remain unverified. See [GFS scope and verification](docs/gfs-checkpoints.md). The published Pre-release ZIP remains unchanged. Identify the candidate by filename and SHA-256; version 0.3.1 alone is insufficient.

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
- **Confirmation has a defined boundary.** Unconfirmed work is not recoverable after source loss. Old histories are not retroactively certified; the status page is not a current audit of all originals. The new GFS candidate also retrieves every initial-snapshot/Checkpoint resource by fixed version before writing its manifest. The published v0.3.1-pre.1 does not include that change. Error diagnostics may be unavailable after DB failure or forced termination.
- **Operational automation remains limited.** One configured weekly occurrence has passed through the standard wp-cron.php entry point after real-time waiting. HTTP loopback triggering, repeated long-term schedules and complete-site deletion acceptance remain unverified; WP-Cron is not an exact-time guarantee. Retention preview is not permission to delete; legacy asset-only cleanup is not complete-site cleanup. No automatic recovery continuation, infrastructure provisioning, DNS switching or mail replay is promised.

Use the linked setup and adapter specifications for dependency versions, permissions and precise exclusions. Test-environment incidents, such as browser rendering or container memory constraints, are recorded separately from product defects and do not redefine the recovery goal.

## 6. Documentation — Setup, evidence and specifications

| Purpose | Documentation |
|---|---|
| Start using the product | [Setup and protection boundary](docs/start-here.md) · [Install / update](docs/install-update.md) |
| Reconstruct supported site state | [Site-wide recovery](docs/site-snapshot.md) · [History resume](docs/save-resume.md) |
| Understand stored resources and application rules | [Separated originals](docs/separated-assets.md) · [Recovery rules](docs/application-rules.md) · [History confirmation](docs/commit-verification.md) |
| Check adapter-specific scope | [Comments](docs/comments.md) · [Forms](docs/forms.md) · [Members](docs/members.md) · [TablePress](docs/tablepress.md) · [Native details](docs/native-details.md) |
| Find verification and historical detail | [Evidence index](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/product-evidence-index.md) · [Published package record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/prerelease-package-m1-031.md) |

This README describes both the published Pre-release and the separate unpublished candidate. Published ZIPs remain unchanged; the candidate adds snapshot verification, GFS scheduling and retention labels while retaining existing read compatibility. Earlier research paths and accumulated test narratives remain accessible through the evidence index; they are not the standard product architecture.
