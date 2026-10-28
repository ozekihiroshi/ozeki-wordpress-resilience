# TablePress preservation and recovery

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

## Product contract

TablePress free/core is optional. Install it separately and create a trusted initial
site snapshot with it active. The snapshot bundles its recorded software and captures
`tablepress_table` posts, table options/visibility, `tablepress_tables` (ID registry)
and `tablepress_plugin_options` (global display settings). User editor preferences
and derived render caches are not recovery assets.

Successful TablePress add/save/delete callbacks create an independent complete
`source.json` (`owr-table-1`) with the table post, cells, options, visibility and ID.
Deletion is an explicit tombstone. ID changes remove the old mapping and retain the
new one; Resilience does not rewrite shortcodes that TablePress itself leaves
unchanged. Settings changes have their own complete JSON record. Copy and delete-all
hooks are connected, but were not included in the live acceptance below.

`TableHistory` reuses `CommentHistory`'s durable queue, conditional S3 originals,
formal history ordering and Resume history action. Only confirmed S3 history enters
recovery. A failed PUT remains queued and can resume from its frozen payload.
The TablePress operation may already be visible on the source before history
confirmation; this is completed-operation capture, not a pre-save gate. Loss of the
source before confirmation can lose the unconfirmed change. Concurrent same-table
operations and termination before capture are outside this contract. Each operation
is limited by the existing 5 MiB JSON record bound; larger operations cannot become
confirmed history. A WordPress deletion does not erase retained S3 originals.

Whole-site recovery overlays table records and registry changes onto the snapshot,
then restores article shortcodes with the same IDs. Individual Markdown restoration
does not process table history. A history TablePress version inconsistent with the
snapshot's bundled version is rejected before destination writes. Take a new trusted
baseline after upgrading TablePress. CSS text is preserved, while generated-file CSS
caching switches to TablePress's native inline mode on the destination, avoiding a
missing or stale generated CSS file. No additional service or authentication helper
is required by the product.

## Measured acceptance — 2026-10-24

- TablePress 3.4.1; PHP 8.3.36; source WP 7.1.2, destination WP 7.1.3.
- Existing community `wp-rescue` and dm `owr-m1-wordpress` containers. Independent
  `owrtpi_20261024_fresh_` / `owrtpi_20261024_upgrade_` tables and content directories.
  AWS SDK standard EC2 role credentials; existing lab bucket, separate TablePress
  trial prefix. No IAM change or new infrastructure.
- Japanese 5-by-3 baseline table embedded in a substantial test page; update cells
  and alternating-row setting; inject an S3-handler failure; verify no additional
  formal history; resume exactly once, including a repeated resume.
- Add a second table; rename its ID to `recovery-table`; create/delete another table;
  change global custom CSS; create a normal published article embedding the second
  table. Checkpoint through sequence 8.
- Update a second-table cell and hide a row after that Checkpoint (sequence 9).
- On dm, restore exclusively from the S3 manifest and subsequent formal history.
  Source DB, local operation queues and expected-result files are not recovery
  inputs. Independent expected-result files are used only by the assertions.
- Both table IDs, exact cells/options/visibility, custom CSS, deletion, published
  page/post states and embedded shortcode rendering PASS. Mail attempts: 0.
- Browser inspection on `wp-backup.ceri.link/owr-tablepress-trial/` confirmed both
  recovered articles, Japanese cells, hidden row, updated content and custom border.
  This is a token-gated **test-only view of the isolated recovered WordPress DB**,
  not a replacement of the existing site's posts or a new product preview feature.
- Local TablePress replay/default-setting regression tests and existing M1
  checkpoint/comment/form/member/cleanup contracts pass. Existing contracts use
  their declared in-memory storage doubles; the integration above uses actual S3.

Table operations used the normal TablePress PHP APIs, not editing-screen clicks.
JavaScript sorting/search/pagination, premium modules, external imports, linked
remote media and arbitrary third-party extensions are not verified here.

## Failure classification

**Product defect fixed:** a new TablePress installation may keep its empty registry
or default options in memory without persisting WordPress options. The first restore
attempt rejected this valid empty destination during its pre-write backup read.
Capture now reads the plugin's public default getters when the option is absent;
the same Checkpoint then restored successfully. A regression test covers this case.
The failure happened before destination content replacement.

**Environment/tooling:** Windows' Python launcher was unavailable; the existing WSL
Python was used for local file preparation. No server, IAM or container resource
change was needed. No new dm OOM failure was observed.

**Test infrastructure:** initial prior assessment treated TablePress option storage
as an array; it is JSON text. This was an assertion correction, not a product fix.
The current run uses separate namespaces and a small test-only web view. These are
not product runtime dependencies. Earlier ZIPs remain unchanged. The TablePress candidate packages this adapter;
formal release and scheduled execution remain deferred. Packaging acceptance is
recorded separately from the preceding source integration trial.

Final code review also separated table asset IDs from global settings asset IDs (a table may itself be named 'settings'). A local queue-capture regression confirms separate identities. Real-S3 acceptance preceded this naming-only adjustment; restored data and sequence remain unchanged.

