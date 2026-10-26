# Distribution and interrupted cleanup verification

[日本語](recovery-readiness-ja.md)

2026-10-26. Work: existing-feature verification and packaging/evidence. State: verified with the boundaries below; no product-code change or release publication.

## Interrupted cleanup and recovery

An unused child prefix under the existing dedicated deletion-validation scope was checked for objects, old versions and delete markers before use. Existing community/dm containers were reused with separate fixture database prefixes and content directories. SDK authentication used the existing EC2 roles. Mail, automatic updates and WordPress Cron were disabled for this fixture.

The fixture contained a Baseline, history 1, an independent Checkpoint through 1 and subsequent history 2. The product preview found 33 versions: 16 candidates and 17 retained resources. One obsolete history version was actually deleted from S3. A test wrapper failed the second DeleteObject call **before transmission**. The product returned `ok:false`, recorded the first successful deletion and the failed/uncertain candidate with its reason, and issued no later deletion calls. There were 32 versions and no delete markers afterwards. All 17 retained resource hashes still matched.

The existing dm recovery role then reconstructed the retained Checkpoint plus history 2 in the separate fixture. Body, title, published state, image hash and rebased links matched. No source database or ancestor resources were used. This confirms real deletion followed by injected interruption and recovery; it is **not** a real AWS outage, ambiguous server-side timeout, browser interruption or automatic-resume test. No resume or rollback feature was added.

## Operational conditions

Use the previously verified server invocation of standard `wp-cron.php` as the reference deployment trigger. Its due-event dispatch, unchanged-content independent Checkpoint, next reservation, scheduled cleanup and failure-injected cleanup suppression were already verified in [scheduled acceptance](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/cleanup-browser-scheduled-acceptance.md). This work did not enable a new production schedule or repeat that test. HTTP loopback and year-long natural expiry remain outside that evidence.

The source role could list all versions and inspect locks in the dedicated scope. The bucket reported Object Lock enabled without a default retention rule. The new fixture had no retention or Legal Hold blocks. Attempting to set a future retention deadline on one new fixture version returned `AccessDenied` because the role lacked `s3:PutObjectRetention` for this prefix. No active-lock acceptance is claimed. The subsequent cleanup preview succeeded with its unchanged reviewed plan.

The dm role could list current objects and read exact recovery versions, but not list all versions. Recovery succeeded; cleanup on that role is not certified or required. IAM policy-listing calls were denied on both roles, so this is not proof that the complete IAM examples alone provide the effective grants. IAM and bucket conditions are environment requirements; they must not be bypassed by weakening product checks. No IAM changes were made.

## Distribution scope

The next documentation-only ZIP includes the current bilingual guides and FAQ. Its executable files and vendor dependencies must match the previously verified optional-Markdown candidate byte for byte. Installation/update evidence is inherited from that candidate, not newly executed. Published pre.1/pre.2 ZIPs remain unchanged. The candidate is not a new release.
