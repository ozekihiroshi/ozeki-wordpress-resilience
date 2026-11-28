# Source-captured plugin operations and embedding contracts (development experiment)

Date: 2026-11-28. This is an isolated development result, not a release-readiness declaration.

## What changed

The experimental journal now records version 3 in a separate option key. Existing v1/v2 journals, submitted packages, S3 originals and formal histories are not rewritten. Missing old contracts are not inferred. The public plugin boot path still does not enable this observer.

Before the normal handler, the observer records the operation input, actor, field definitions needed to interpret values, typed references, and the names (not secret values) of the form nonce controls actually submitted. After the handler, it records its normal response, returned identities, redirect and relevant completion hooks. Sequence and predecessor numbers plus input/contract/completion hashes bind these records together.

The follower does not sort operations by plugin type. It binds only recorded references to the identities returned by previous normal registrations. It does not interpret arbitrary numeric-looking strings as IDs. Source inputs remain unchanged. The destination request necessarily uses new identities and fresh destination credentials.

| Normal operation | Source-time contract | Completion evidence |
| --- | --- | --- |
| WordPress page/post registration and update | Author, parent and term references; exact supported embedding ID spans | REST response ID |
| Markdown import and editor save | Uploaded bytes/name; source text, owner and editor form participants | Normal document post result, excluding revisions |
| TablePress JSON add and editor save | Table identifier distinct from post ID; structured cell/option values | Normal import success redirect; `tablepress_event_saved_table` |
| CF7 registration and update | Normal REST input; form tags remain CF7 definitions, not WordPress shortcodes | REST response ID |
| Flamingo inbound registration | Actual CF7-to-Flamingo input and form reference | Normal inbound ID and saved receipt result |
| WP-Members settings, fields, account/profile | Page references, member field types, stable field keys, account identity, executor vs content owner | Ordinary option/user effects |
| ACF JSON import and values | Definition input; source field type distinguishes text from references | Complete set of normal import hooks; normal owner save |

For supported numeric Markdown/CF7 and TablePress embeds, the source records the literal identifier, its byte position and reference type. Replay substitutes those recorded spans, right to left. It does not search for shortcode syntax to rediscover meaning.

## A gap found during this work

The first normal-form dispatcher fetched all destination editor nonce fields. An ACF-only source save had not submitted the WP-Members restriction nonce, but the destination editor displayed it. Adding that extra nonce activated an additional handler and cleared a restriction. This was an error in the new development dispatcher, not evidence of a submitted ZIP regression.

The fix was to capture the original form participant names at source. Replay refreshes exactly those tokens. It does not restore the restriction afterwards. A fast regression verifies that an extra available member/Markdown nonce is not submitted; the real combined operation test checks the restriction after ACF saving.

Another source contract gap was `field_arr` during WP-Members field editing. WP-Members 3.5.8.3's normal field form emits the `meta_key` there. It is recorded as a stable definition key; it is not treated as an internal database index. A rename remains incomplete rather than guessed.

Two test-helper issues were also corrected: ACF ordinary import legitimately supplies omitted defaults, so supplied input must not be confused with the full exported output; Markdown export returns bytes plus headers, so the byte comparison must select the byte result. No saved content was repaired to satisfy those checks.

## Verification and boundaries

The test uses two disposable WordPress sites on dm, an internal Docker network without published ports, local synthetic data, and no S3. The source performs real normal HTTP actions. The destination receives the automatically observed journal and the focused initial author material, not the source test recipe or a supplied source-to-target ID table. The author map comes from normal user registration results. Pre-existing destination pages/table shift the new allocations.

The representative sequence includes page registration, member page settings, table/document/form creation, typed embeds, access settings, ACF import/value saving, table editing, publication, member definition/account/profile creation, definition/form editing and a real CF7 receipt. Destination receipt registration does not send CF7 feedback again. Checks compare embeds, document bytes, table contents, ACF definitions and text values, member page references, profile value and restriction, and normal page resaving.

The fast PHP cases vary identities and reject sequence changes, missing references, tampered results and incomplete capture. The additional Python regression checks exact form participant handling. Assertion counts are not counts of independent real plugin scenarios.

Final result: **19 observed operations followed in their original sequence, passed**. Real operation and comparison phase: **22.984 seconds**; full reused-environment run: **29.420 seconds**, including 0.217 seconds to reset the dedicated synthetic database. PHP contract process: 0.121 seconds (601 earlier identity/order assertions plus 17 plugin-contract assertions); the four form-participant checks also passed. These timings are development test costs, not production performance estimates.

Actual returned identity examples: document 11 → 18, table "1" → "2", form 13 → 20, material page 14 → 21, member 2 → 3, receipt 22 → 28. WP-Members' edited label was verified as `Company updated`. All 2,703 files in the six plugin ZIPs matched their installed source and destination copies. The dedicated containers, volumes and network were removed with no cleanup errors.

Evidence: [final results](construction-plugin-contracts-20261128-results.json). The remote raw journal contains only synthetic fixture data and was not published.

Not established by this experiment:

- Arbitrary plugin operations, unknown/custom fields, arbitrary block attributes or executable settings.
- Markdown image/URL references, CF7 hash-form aliases, reference-bearing table cells, CF7 file attachments, ACF ID-dependent locations and unclassified member field types. These are recorded as incomplete where encountered; they must not be filled in by replay.
- A complete initial SiteSnapshot-to-formal-history production pipeline. This focused test seeds the author from initial material and follows subsequent observed operations. Existing broader baseline experiments are separate evidence.
- Durable whole-replay interruption/resume, complete browser/JavaScript use, new S3 roundtrips or production readiness.

No third-party code, installation or initialization step is part of replay. Plugins are normally installed and prepared before the experiment. Passwords are not recovered; ordinary new-account credentials/reset policy still applies.

No production content, originals, existing history, ZIPs or tags were changed. Submission and email remain on hold. No merge, push or new ZIP was performed in this task.
