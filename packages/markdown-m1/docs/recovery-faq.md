# Frequently asked questions about reconstruction

Install WordPress, themes and required plugins separately from trusted distributors before recovery, and activate the required plugins. Resilience restores information assets and their supported relationships; it does not install or activate software from S3. It keeps the destination theme selection. Unknown settings are reported without being applied.

[日本語](recovery-faq-ja.md) · [User guide](user-guide.md) · [Recovery specification](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/site-snapshot.md)

Ozeki Resilience reconstructs a supported state from protected originals, a Baseline/Checkpoint and confirmed history. It is not a generic importer that merges arbitrary records into another live site. These answers distinguish **design**, **existing evidence** and **conditions**; first read [the purpose and verification boundaries](../README.md#keep-a-path-to-recovery-after-an-attack) for restarting service without reusing an attacked environment. No additional tests were performed to write this FAQ.

The primary subject is **complete-site recovery onto a dedicated destination**. The legacy individual-Markdown recovery path is a different operation and does not inherit the complete-site relationship guarantees. For this 0.3.1 submission candidate, native-only sites do not require Markdown Documents; see the user guide for conditions when Markdown content exists.

## 1. Can automatic numbering change IDs and break relationships?

**Design.** Complete-site recovery replaces the supported content tables and inserts the saved rows with their original IDs. Post IDs and term IDs are not newly assigned according to import order. This preserves the ID basis of relationships such as post-to-category, featured-image and parent references within the reconstructed data. Users are handled separately: source authors and supported members are mapped to destination users, and the supported author/comment-user references are adjusted.

**Existing evidence.** Recovery tests compared featured-image IDs and bytes, category/tag IDs, and deletion results. WP-Members tests covered supported member login and access restrictions. See [native relationship evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/native-details-final-m1-031.md) and [membership evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/members-m1-031.md).

**Conditions.** Use a clean, dedicated recovery destination and agree to content replacement. This is not a merge with an unrelated site's posts. Arbitrary custom fields are not universally interpreted or remapped: recognized attributes follow the adapter rules; captured unknown information remains in S3 and is reported as not applied. Keeping IDs does not repair an already broken source relationship, nor does existing evidence cover every possible reference combination. See [application rules](application-rules.md).

## 2. Can a different URL or Japanese text break serialized settings?

**Design.** Recognized serialized attributes are decoded as values, transformed where required, then serialized again. URL relocation does not directly edit the encoded string while leaving its byte-length fields unchanged. PHP computes the new lengths. JSON is decoded/encoded with errors surfaced. The separated-original format reconstructs submitted fields and retains noncanonical original serialization when needed. Object-valued settings are not automatically instantiated and applied as portable configuration.

**Existing evidence.** Existing separation tests include Japanese submitted fields and line breaks, lossless reassembly and unknown-field preservation. Application-rule tests cover recognized nested CF7 attributes. See [separation evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/separated-assets-m1.md) and the [separation implementation](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/src/AssetFormat.php).

**Conditions.** This avoids the usual raw search-and-replace length error; it is not a promise to repair malformed source data or understand arbitrary plugin encodings. Invalid recognized serialization is rejected. Unknown captured fields remain in S3 rather than being blindly applied. Every combination of emoji, encodings, nested values and URL shapes has not been demonstrated. A reported serialization failure should be investigated, not bypassed by editing the protected original.

## 3. What if WordPress or plugin versions differ?
Prepare the recorded WordPress release line and the required plugin versions. New Baselines record software names and versions for reinstallation. Existing saved assets remain readable, but their archived software is not used for recovery. Missing/inactive dependencies or mismatched recorded versions stop recovery with preparation instructions.

## 4. How do I prepare themes and custom behaviour?
Install themes and plugins from trusted distributors and select the destination theme yourself. PHP, JavaScript and CSS from S3 are not installed. Supported presentation settings are applied; settings for another theme and unknown settings are withheld. Prepare server configuration, external services and connection details separately.

## 5. What if WordPress saves but S3 history does not confirm?

**Design.** WordPress and S3 do not form one atomic transaction. Supported body saves place originals in S3 before WordPress application; comments and some adapter/detail operations capture completed-operation data. Newly saved resources are retrieved by fixed version and checked before formal history is written. Pending/error state is distinguished from confirmed history. Complete-site Checkpoints use confirmed S3 history and reject gaps; an unconfirmed live change is not silently added from the live database.

**Existing evidence.** Earlier failure-injection and resume tests verified pending/error reporting and later confirmation. Original verification failures stop confirmation. These bounded tests are not evidence of every real AWS outage or every process-termination instant. See [save/resume evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/save-resume-acceptance.md) and [original-verification evidence](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/save-verification-final-m1-031.md).

**Conditions.** A settings checkbox or a visible WordPress edit alone is not confirmation of protection. Inspect the last confirmed history and pending/error information. After resolving the cause, use the documented resume operation for queued work; pre-queue failures require saving again. If the source is lost before formal confirmation, that operation is outside the recovery boundary. Recovery itself stops on failure; neither automatic continuation nor unconditional rollback is promised. See [save recovery steps](save-resume.md).

## When a recovery fails

Keep the selected Checkpoint, requested history end, product/plugin versions and the recorded error. Inspect the failed/latest attempt and its details; do not substitute an older success result. Preserve S3 resources, identify the cause, prepare the destination and decide whether to retry. Redact credentials and private originals from support reports. Environment preparation issues and unsupported scope should not be confused with lost required resources or false success reporting.
