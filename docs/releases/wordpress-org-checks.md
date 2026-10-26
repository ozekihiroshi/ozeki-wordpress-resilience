# WordPress.org review checks — 0.2.0

Date: 2026-10-26 (JST). Scope: directory preparation only, with the pre-existing
seven working changes preserved. No new AWS requests, production-site changes,
72-hour observation or architecture work were performed.

## Results before archive freeze

- Plugin Check 2.1.0 on a dedicated WordPress 7.1.3 installation: **0 errors,
  61 warnings**, with both the normal static entry and the `cli.php` runtime entry.
  The checker is not an approval decision. Findings are retained in
  `evidence-public/wordpress-org-plugin-check.json`.
- All 12 PHP files in the plugin allowlist passed PHP 8.3 syntax checks.
- Existing Python tests: distribution 8, reconstruction worker 17, native
  materials 6, material contract 15; all 46 passed.
- Existing PHP reconstruction-request contracts passed; native guards 5,
  rendering 2 and link fragments 4 passed. Existing asynchronous-media JavaScript
  checks passed (delayed success, failure and changed operation identity).
- Actual dedicated WordPress: activation passed; script assets and configuration
  were enqueued; screens no longer emitted direct script tags; recovery exposure
  wording was present; anonymous state access was refused and admin access worked.
- Configured-target CLI, using generated materials and a filesystem S3 double:
  wrong target URL refused, stored `publish` state restored, and replay of the
  same generation preserved IDs. This establishes the current status behavior,
  not new live-S3 coverage or safe exposure on an arbitrary host.

The PHP minimum remains 8.1; this local pass used PHP 8.3. Prior CI covers the
existing 8.1/8.3 baseline. `Requires at least: 6.8` is the declared compatibility
floor; the dedicated installation used 7.1.3. No new full version matrix was run.

## Warning disposition

| Group | Count | Review |
| --- | ---: | --- |
| Direct DB calls / uncached DB access | 30 | Named locks, transactions, exact-parent/material comparisons, transactional-engine checks and compare-and-swap option writes require fresh reads. SQL identifiers are WordPress table names; variable values use preparation. Replacing these with cached results would change existing guarantees. |
| Slow metadata lookup | 2 | Bounded material-ID lookup; performance advice, not an observed release defect. |
| Input sanitization / unslashing | 11 | Request method/action values are compared to fixed literals; read-only test IDs are type/format/membership checked; uploaded binary files are checked by permission, nonce, upload origin, size and PNG/JPEG decoding in the dedicated upload method. Binary data must not be passed through a text sanitizer. |
| Nonce recommendations | 12 | Read-only view selectors/notices do not write state. Upload dispatch calls the handler that verifies the media nonce and administrator permission. State-changing admin forms verify nonces; REST routes use WordPress authentication and capability callbacks. |
| Short prefix / namespace | 6 | Existing `Owr` and `owr_` identifiers are product-specific but shorter than the checker's preferred prefix. No generic global identifiers were introduced. No compatibility-breaking renaming was undertaken. |
| Restricted product name / slug | 0 remaining | The original name produced 3 warnings. The owner-approved `Ozeki Resilience` / `ozeki-resilience` distribution resolves them; the GitHub repository name and stored option keys are unchanged. |

## File operations retained deliberately

The initial checker also flagged native filesystem calls used by the private
WordPress/worker IPC queue. Those sites now have specific PHPCS annotations and
reasons. OS file locks, exclusive creation, exact permission bits and atomic
same-filesystem rename are required by the existing durable queue contract.
Switching to FTP-backed WP_Filesystem would not preserve it. These annotations
are limited to the flagged filesystem operations, not blanket security disables;
reviewers can inspect the retained calls. The code does not use them to install
plugins or fetch executable code. The operator must restrict the bridge directory.

Actual fixes include output escaping, direct HTTP access guards, standard script
enqueueing, scoped/dismissible editor notices, metadata and accurate disclosures.
The source-status and configured-target implementation came from the original
working changes and was not reverted.

## Environment and harness notes

Docker's default address pool was exhausted. Only a new internal review network
was created in a checked-unused subnet, with no public port. Existing containers
and networks were untouched. WSL lacked Node, so the existing Node image ran the
three JavaScript cases with networking disabled. The first PHP REST smoke request
used a null synthetic body; setting it to the empty string sent by HTTP fixed the
harness. These are not product failures. The intentional wrong-target test emits
a PHP exception, as expected. No success is claimed for that rejected request.

## Before submission

The owner confirmed contributor `ozekihiroshi` and the `ozeki-resilience` slug. Make the exact matching operator kit/source revision available to the
reviewer; the local branch and ZIP alone do not publish it to GitHub. The supplied
S3 adapter's dedicated SSH/environment dependency is explicitly disclosed in
`readme.txt` and `setup.txt`; reviewer acceptance of that integration is not assumed.
No submission has been sent. Archive hashes and final archive-install checks are
recorded beside the frozen ZIPs to avoid self-referential kit hashes.
