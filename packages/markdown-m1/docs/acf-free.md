# ACF free basic fields — 0.3.3

Candidate rc.11 update (not in submitted rc.10): while protection is enabled, database field/group additions, changes, trash/restoration and deletions are saved as independent definition history, including when there are no posts or pages. Check formal-history confirmation after the operation. New definition history and its Baselines/Checkpoints require this updated recovery implementation; it continues to read existing originals. Older implementations reject these new recovery points.

This integration captures completed ACF saves on published or already-protected posts and pages. Values, complete field definitions and field-key references are separate JSON originals; unknown settings and raw metadata remain in the stored original. Confirmation uses the existing fixed-version readback/hash verification and pending-history queue. A WordPress field save is not confirmation in S3; queued failures remain pending for explicit history resumption (see the capture-failure boundary below). Body history and ACF field history are separate confirmed operations.

Automatic application is limited to database-defined groups with post/page post-type location rules and these field types: text, textarea, number, range, email, url, select, checkbox, radio, button_group, true_false, date_picker, date_time_picker, time_picker and color_picker. Recognized values, choices and field keys are reconstructed through complete-site recovery; unrecognized types/settings are retained in originals and listed as not applied. The destination must have the recorded free ACF version active. Baseline and later history share these rules; Checkpoints consume S3 assets/history only.

ACF PRO is not supported or planned. Media/post/user/taxonomy reference fields, nested fields, custom post types, options/user/term/comment fields and PHP/Local JSON definitions are outside this integration. Create a new trusted Baseline when adding ACF or changing its version. Submitted rc.10 also requires a new Baseline after standalone definition changes. Recovery uses the recorded ACF version and the field types listed above. Other field types need their own recovery rules. This integration starts with the 0.3.3 candidate.

Deleting a definition does not delete earlier originals. Recovery uses the latest confirmed definitions and withholds values whose definitions no longer apply. A later article record cannot restore a definition that was removed by independent definition history.

Values that do not match their field type (such as an array in a text field) remain in the original and are withheld from the destination, with a reason in the not-applied report. Recovery continues for other valid values and articles.

## Verification records

[Research trial and integration boundaries](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/acf-free-verification.md). This integration is not available in 0.3.2. Check [current distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

Preparation distinguishes ACF free, PRO and unused ACF. For the free version, it requests a new initial save when a capture including the current version cannot be confirmed. ACF PRO fields are outside protection; article protection can continue. Stored definitions with inactive ACF free are also shown as outside protection with a next action.
