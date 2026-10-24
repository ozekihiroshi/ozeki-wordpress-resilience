# TablePress standard editor and interactive recovery acceptance — 2026-10-24

PR #25 adapter was reused unchanged (TableHistory.php SHA-256 b26773066f3d985bbd0c806510f763dab39c0af33b78f3bdcabdd011ae43e776 on source, destination and reviewed source). Existing community/dm containers, isolated TablePress integration databases and S3 prefix were reused. No new infrastructure, IAM changes or credential helper.

## Browser operations and S3 evidence

Chrome, TablePress 3.4.1 standard Add New / Edit / All Tables screens:
- Added table 4, 13 rows (one header plus twelve records), three columns, Japanese content.
- Pasted tab-separated trial content into the standard grid; enabled existing visitor features with five rows per page; saved.
- Updated the first data row to `復旧確認01：ブラウザ更新済み`; saved successfully.
- Added disposable trial table 5 and deleted it using the standard confirmation dialog.
- Actual S3 formal records 10, 11, 12 captured table 4 addition/content/update; 13 and 14 captured table 5 addition/deletion. All originals were read and hashed; no pending history remained.

## Recovery and browser results

The existing Checkpoint through 8 plus subsequent S3 formal history through 14 reconstructed the existing isolated dm recovery database. Source DB, local queue and expected-result JSON were not reconstruction inputs (expected JSON was assertion-only).

Exact table cells, title/description, options, visibility and ID matched. Table 5 was absent. Restored shortcode output included the updated cell. CLI recovery/verification mail attempts: zero.

A token-gated test-only renderer reads the restored DB without changing any article:
- Japanese search `ブラウザ更新済み`: one matching record out of twelve.
- Number-column ascending then descending: descending first page 12, 11, 10, 09, 08.
- Next page: 07 through 03, showing 6–10 of 12.
- Last page: 02 and 01, showing 11–12 of 12; Next disabled.
Screenshots are retained locally as ui-search.png, ui-sort.png and ui-pagination.png.

## Safety and issue classification

Existing live dm content/configuration/Cron/formal-history hashes match the preceding final-ZIP baseline. Changes were limited to existing isolated trial databases and trial display/setup files. Source existing articles were not edited. Both test web bootstraps disable WP-Cron and intercept mail. No formal release or scheduled execution.

Test infrastructure corrections: standard-admin access required matching HTTPS proxy handling; the isolated display initially used a fictitious site URL, causing jQuery loading failure. Explicit trial WP_HOME/WP_SITEURL resolved it without product changes. The existing live probe still emits the duplicate DISABLE_WP_CRON configuration warning. No new product defect or dm OOM was observed.

Automatic approval review rejected a proposed shortcode addition to the existing trial article. That mutation was removed before execution. A separate renderer displays the recovered table instead; no article replacement or additional stored article was used.

The standard editor uses ordinary WordPress authentication in `/owr-tablepress-lab/`, backed by the already-existing isolated DB. Browser login details remain local and are not included in this report. Core PHP/admin/includes files were copied from the existing installation; the product does not depend on this test arrangement.

## Scope

This extends the prior API acceptance to standard browser add/save/update/delete and recovered search/sort/pagination. It does not claim premium modules, imports, concurrent edits, arbitrary JavaScript extensions or all browsers. Frozen final ZIP remains unchanged; this is additional acceptance evidence, not a new release.