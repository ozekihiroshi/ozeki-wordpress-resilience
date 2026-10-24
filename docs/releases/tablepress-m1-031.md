# TablePress 0.3.1 candidate — ZIP acceptance

This candidate connects TablePress tables, IDs, display settings and confirmed
operations to S3 history and whole-site recovery. The package's English README and
Japanese RAADME-jp describe post-success capture, pending history, supported scope
and exclusions. This is a local candidate, not a formal release.

## Frozen artifact

- File: `ozeki-wordpress-resilience-0.3.1-tablepress-final.zip`
- SHA-256: `ca1f2717ad3a01b55a9c18b84242a0de2adc5a7fc24f89894f441ce151ea9ebd`
- 7,369,379 bytes; 3,809 files.
- Vendor libraries are byte-identical to the reviewed WP-Members final candidate.
- All packaged product files match the reviewed working-tree sources. Trial scripts,
  test credentials, test-only web view, TablePress itself and other optional plugins
  are not bundled. Existing candidates remain unchanged.

## Installation and update

On existing dm Docker, independent `owrtzip_20261024_fresh_` and
`owrtzip_20261024_upgrade_` WordPress namespaces were used. Fresh installation loads
this ZIP; update starts with the WP-Members final candidate from PR #24. Both use
normal WordPress activation/boot, with ZIP extraction and replacement of plugin
files. Browser Plugin_Upgrader behavior was not part of this run.

Both cases preserve S3 settings, identity, prior result records, TablePress table
cells/IDs/global settings, comments, CF7 forms, Flamingo receipts, WP-Members member
attributes/password hashes, and frozen pending records/error messages. Existing
scheduled entries remain; Resilience Checkpoint execution is disabled. Test-only
pending records contain synthetic payloads and must never be resumed.

Actual S3 formal history remains at 9 records, SHA-256
`9ccd7d7155c0c73b3bb704fdf9830cc91c77075b473aba9f1475e57fedd1afe5`.
The default AWS SDK EC2 role provider was used. No S3 writes or IAM changes occurred.

## Recovery using the final ZIP

Both installations restore the existing TablePress S3 Checkpoint through sequence 8
and following history 9. Assertions pass for exact cells, per-table options,
row/column visibility, IDs, deletion, global CSS text, published article states and
embedded table HTML. The source DB and local history queue are not recovery inputs.
All 3,809 installed ZIP entries match before and after recovery.

The final ZIP's extracted code also passes M1 checkpoint, comment, form, membership,
TablePress replay/defaults/queue-identity and cleanup contracts, plus PHP syntax
checks. Those local storage contracts use their declared in-memory doubles; the
integration recovery above reads actual S3.

The existing live dm site's content-table hashes, S3 configuration, result records,
Cron and 48-record history compare unchanged before installation and after recovery.
No existing content or accounts were replaced. Mail transport is suppressed in the
trial bootstrap; verification and recovery record zero mail attempts. Core install
notification attempts, if any, are intercepted rather than delivered.

## Product corrections versus test infrastructure

The earlier implementation fixed valid empty TablePress destinations being rejected
when registry/options remained in memory, and separated table asset identities from
global settings identities. Both corrections are in this ZIP. No additional product
defect was discovered by final packaging acceptance.

The live read-only probe reports a duplicate `DISABLE_WP_CRON` definition from the
existing container configuration. This is a test-bootstrap/configuration warning;
it does not change the true value, and both live-state comparisons pass. There was
no new OOM failure or required environment change. Earlier option JSON assertions
and Windows Python-launcher problems remain separately documented in the adapter
contract; they are not newly discovered product failures.

## Remaining scope

TablePress 3.4.1 free/core, normal PHP API lifecycle and shortcode rendering are
covered. The earlier implementation trial also inspected both recovered articles
in a browser; this ZIP run verifies article HTML, not browser editing. Interactive
search/sort/pagination, premium modules, external imports and concurrent same-table
writes are not acceptance claims. Only formally confirmed operations are recoverable;
source changes may already be visible while S3 history is pending. A TablePress
version change requires a new trusted baseline.

See [adapter contract](../../packages/markdown-m1/docs/tablepress.md) and
[machine-readable validation](../../evidence-public/tablepress-zip-validation.json).
No scheduling, mail sending, formal release or live plugin deployment was performed.

## Final PR review

Reviewed successful-operation capture, settings/table identity separation, registry
replay and deletions, metadata allowlists, baseline dependency inclusion, version
preflight, pending-history reuse, CSS fallback, and English/Japanese scope parity.
No blocking finding was identified within the stated scope. The frozen ZIP and
packaged source bytes remain unchanged. Git's staged whitespace check reports one
cosmetic trailing blank line in the packaged TablePress contract; it is retained to
preserve exact correspondence with the already-tested ZIP, not treated as a test
failure or a behavior change.
