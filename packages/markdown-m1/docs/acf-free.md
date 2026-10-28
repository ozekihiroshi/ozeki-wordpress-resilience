# ACF free basic fields — integration candidate

The research adapter captures completed ACF saves on published or already-protected posts and pages. Values, complete field definitions and field-key references are separate JSON originals; unknown settings and raw metadata remain in the stored original. Confirmation uses the existing fixed-version readback/hash verification and pending-history queue. A WordPress field save is not confirmation in S3; queued failures remain pending for explicit history resumption (see the capture-failure boundary below). Body history and ACF field history are separate confirmed operations.

Automatic application is limited to database-defined groups with post/page post-type location rules and these field types: text, textarea, number, range, email, url, select, checkbox, radio, button_group, true_false, date_picker, date_time_picker, time_picker and color_picker. Recognized values, choices and field keys are reconstructed through complete-site recovery; unrecognized types/settings are retained in originals and listed as not applied. The destination must have the recorded free ACF version active. Baseline and later history share these rules; Checkpoints consume S3 assets/history only.

ACF PRO is not supported or planned. Media/post/user/taxonomy reference fields, nested fields, custom post types, options/user/term/comment fields, PHP/Local JSON definitions, and definition-only edits without a subsequent protected post/page field save are outside this first adapter's acceptance scope. Use a new trusted Baseline for standalone definition changes. No cross-version conversion or automatic sanitization guarantee is added. Existing published ZIPs do not include this research change.

## Verification records

[Research trial and integration boundaries](acf-free-verification.md). This integration is not in submitted 0.3.2 rc.1 or published ZIPs.
