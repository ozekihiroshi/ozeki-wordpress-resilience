# WordPress.org 0.3.1 candidate checks

Baseline: current main `b2968c7fd0fa45bc77a0f82dbfda8c1cbc6628f1`. Public name/slug and documentation updated; no features or architecture changes. Old root checkout's seven uncommitted files and the clean main worktree are preserved. The old release head remains in `archive/wordpress-org-020` and the existing public tag.

## Changes and checks

- Plugin metadata/readme, bilingual public README and onboarding now describe the current product. External Python/SSH kit requirements removed. Historical research plans are not release gates; CONTRIBUTING identifies the current package.
- Added direct-access guards to product includes. Standalone existing test fixtures explicitly define their WordPress context. Escaped admin output and the WP_Error message. Recovery activation uses the current installed plugin basename instead of the old directory literal.
- Syntax checked product and fixture PHP. Existing gfs-admin, recovery-result, save-status, application-rules and recovery-errors tests passed, including their escaping and failure assertions.
- Isolated WordPress 7.1.3 / PHP 8.3.35: native-only Baseline and recovery with in-memory S3 passed, saved publish state and the new active plugin path preserved. Existing site-snapshot checks also passed. No real site or AWS data was used.
- Final ZIP: old 0.3.1 directory deactivation → new directory install/activation preserved settings, synthetic body/related pending operations and prior results. Active reinstallation preserved them again. All 3,846 installed files matched ZIP paths and SHA-256. This is WP-CLI installation, not a new browser-upload test.
- All relative file links in current package Markdown resolve. Vendor bytes are reused from main's verified readiness ZIP; no dependency update.
- Official Plugin Check 2.1.0 (runtime CLI bootstrap): **0 errors, 103 warnings**. Full findings and validation are in evidence-public/wordpress-org-031-*.json and release assets. This is not WordPress.org approval.

## Remaining warnings

| Code group | Count | Disposition |
|---|---:|---|
| Direct database query | 30 | Transactions, advisory locks, full supported-state capture, freshness and write/readback verification. Parameters/table sources inspected; no new query introduced. |
| No caching | 28 | Fresh transaction/history/recovery state required; ordinary object-cache results cannot establish current persistence. |
| Meta key/value queries | 25 | Existing bounded-purpose content/identity queries; performance limitation, not a new release benchmark requirement. |
| InputNotSanitized | 11 | Nonce verified; Markdown original intentionally preserved with UTF-8/NUL/size checks; operation compared with literals; numbers cast/bounded; GFS normalized; snapshot refs JSON-decoded and validated by Store; sequence choices converted to integers. |
| MissingUnslash | 6 | Literal action/fingerprint comparisons and numeric inputs; no raw HTML/SQL use. Kept visible for review rather than suppressing the category. |
| error_log | 2 | Last-resort diagnostic when durable failure recording fails; no telemetry. |
| unexpected_markdown_file | 1 | RAADME-jp.md is the linked Japanese product guide; retained intentionally. |

## Scoped PHPCS annotations

Exceptions remain plain diagnostic data; output sinks escape HTML and REST encodes its response. Line-specific ExceptionNotEscaped annotations avoid changing stored messages. The WP_Error passed to wp_die has an explicitly escaped message and preserves REST error code handling.

Local filesystem operations are restricted to user-requested recovery: private 0700 staging/0600 rollback records, validated destination paths, same-filesystem replacement and rollback. WP_Filesystem's remote transports cannot preserve these OS semantics. PluginDirectoryWrite findings concern restored selected plugin files, not saving operational data inside this plugin. No category-wide ignores were added.

The private transaction helper is called only with literal START TRANSACTION and COMMIT; its line-specific annotation is not permission for arbitrary SQL.

## Existing evidence and limits

Main's recovery-readiness, optional-Markdown and sample-only IAM records remain the basis for existing behavior. This task does not restart long-duration scheduling, live cloud trials or feature development. Minimum WP/PHP versions are declarations; this packaging check does not establish every combination. Recovery may expose published content unless the destination is restricted. Network/DNS, dependencies and retention remain administrator responsibilities.
