# Distribution and interrupted cleanup verification

[日本語](recovery-readiness-ja.md)

2026-10-26. Work: existing-feature verification and packaging/evidence. State: verified with the boundaries below; no product-code change or release publication.

## Interrupted cleanup and recovery

An unused child prefix under the existing dedicated deletion-validation scope was checked for objects, old versions and delete markers before use. Existing community/dm containers were reused with separate fixture database prefixes and content directories. SDK authentication used the existing EC2 roles. Mail, automatic updates and WordPress Cron were disabled for this fixture.

The fixture contained a Baseline, history 1, an independent Checkpoint through 1 and subsequent history 2. The product preview found 33 versions: 16 candidates and 17 retained resources. One obsolete history version was actually deleted from S3. A test wrapper failed the second DeleteObject call **before transmission**. The product returned `ok:false`, recorded the first successful deletion and the failed/uncertain candidate with its reason, and issued no later deletion calls. There were 32 versions and no delete markers afterwards. All 17 retained resource hashes still matched.

The existing dm recovery role then reconstructed the retained Checkpoint plus history 2 in the separate fixture. Body, title, published state, image hash and rebased links matched. No source database or ancestor resources were used. This confirms real deletion followed by injected interruption and recovery; it is **not** a real AWS outage, ambiguous server-side timeout, browser interruption or automatic-resume test. No resume or rollback feature was added.

## Operational conditions

Use the previously verified server invocation of standard `wp-cron.php` as the reference deployment trigger. Its due-event dispatch, unchanged-content independent Checkpoint, next reservation, scheduled cleanup and failure-injected cleanup suppression were already verified in [scheduled acceptance](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/cleanup-browser-scheduled-acceptance.md). This work did not enable a new production schedule or repeat that test. HTTP loopback and year-long natural expiry remain outside that evidence.

The source role could list all versions and inspect locks in the dedicated scope. The bucket reported Object Lock enabled without a default retention rule. The initial retention-setting attempt was denied because its Allow covered a different prefix. The administrator subsequently added a temporary inline policy granting only `s3:PutObjectRetention` on the dedicated child prefix; the existing source policy and dm permissions were unchanged.

At 2026-10-26 13:13:40 JST, a dedicated obsolete fixture version received GOVERNANCE retention until 2026-10-27 13:13:37 JST. Exact-mode/deadline readback passed. The product excluded that version and its retired Checkpoint group from deletion candidates: 13 candidates before, zero after, 15 blocked entries. All 32 version identities remained unchanged and the selected object's bytes matched. There was one PutObjectRetention call, no PutObject and no DeleteObject. This verifies active retention and candidate exclusion, not Legal Hold ON, locked-delete rejection, or natural expiry.

The dm role's successful recovery used 18 GetObject calls and one ListObjectsV2. Version inventory, lock administration and IAM inspection probes must not be treated as prerequisites for that recovery path. Read-only inspection of both roles was subsequently possible through a temporary source inspection policy. The complete IAM examples were not deployed and verified as the sole effective grant set; this remains distinct from the successful existing-role tests.

Temporary-policy withdrawal is not yet confirmed: a fresh IAM response at 2026-10-26 13:15:46 JST and a reloaded console still listed both `OwrTemporaryRetentionTest` and `OwrTemporaryIamInspection`, despite the reported removal. This is an observed environment state, not a diagnosis of the administrator's actions. No IAM mutation was performed by this verification. Withdrawal confirmation and the previously required complete-template acceptance remain merge prerequisites unless the user explicitly changes that acceptance scope.

## Distribution scope

The next documentation-only ZIP includes the current bilingual guides and FAQ. Its executable files and vendor dependencies must match the previously verified optional-Markdown candidate byte for byte. Installation/update evidence is inherited from that candidate, not newly executed. Published pre.1/pre.2 ZIPs remain unchanged. The candidate is not a new release.
