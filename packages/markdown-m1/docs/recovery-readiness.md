# Distribution and interrupted cleanup verification

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

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

The earlier dm recovery used 18 GetObject calls and one ListObjectsV2. Refused inventory/lock/IAM diagnostics were not failures of that recovery path. Both earlier temporary policies (`OwrTemporaryRetentionTest` and `OwrTemporaryIamInspection`) were subsequently removed and their absence confirmed in the refreshed console. The existing write-policy remained unchanged.

## Complete IAM samples as the only grants

On 2026-10-26, two separately authorized temporary IAM roles were created with only the guide's [source-with-cleanup](aws-examples/source-with-cleanup.json) and [recovery-read-only](aws-examples/recovery-read-only.json) inline policies, respectively. Only the bucket and prefix placeholders were replaced; the applied JSON matched each sample. No managed policy or permissions boundary was attached. The source and dm EC2 roles were unchanged. Each test process used the AWS SDK's standard STS AssumeRole with its corresponding existing EC2 role; STS confirmed the temporary role identity. No static key or authentication helper was installed, and failures could not fall back to the existing broad S3 grants. The bucket had no resource policy granting additional access.

The unused `operational/` child prefix was checked for all versions and delete markers from both hosts before writing. Existing isolated containers were reused with separate DB prefixes and content directories. Real S3 operations succeeded:

- Two initial snapshots, an independent Checkpoint through history 1, and histories 1/2 produced 46 fixed versions. Recorded GETs with VersionId preceded all five manifest/history writes for newly saved resources; the product's byte/hash verification completed. The product source files on both hosts matched the reviewed code.
- One obsolete fixture version received GOVERNANCE retention until **2026-10-27 13:41:15 JST**. Mode/deadline readback matched. The product excluded its complete 13-version snapshot group; 16 other obsolete versions remained eligible and 17 recovery-chain versions were retained.
- The product deleted exactly those 16 reviewed fixed versions. There were 30 versions afterwards, zero delete markers, all 13 protected-group versions remained, and all 17 recovery-resource hashes matched.
- The read-only sample role on dm restored the retained Checkpoint and history 2: body, title, published state, image hash, rebased links and ending sequence matched. It used 18 GetObject calls and one ListObjectsV2, without source DB or deleted ancestors. This was a direct product-method test, not another browser or scheduled-cleanup test.

The two temporary roles and their inline policies were removed after the test; the refreshed role list showed no matching roles. Existing source/dm policies were not edited. Fifteen-minute STS sessions stayed in process memory only; their recorded latest expiration was 2026-10-26 13:56:59 JST, distinct from role deletion. The protected fixture resources remain in the dedicated trial scope.

This closes the **source-with-cleanup + recovery-read-only sample-only acceptance** for the tested SSE-S3 bucket and operations. It does not prove every Action is absolutely minimal, apply the source-no-delete variant, or cover SSE-KMS, cross-account access, organization restrictions, Legal Hold ON, locked-delete rejection or natural expiry. These are deployment/verification boundaries, not product fixes. No existing S3 assets, live content or published ZIPs were modified.

## Distribution scope

The next documentation-only ZIP includes the current bilingual guides and FAQ. Its executable files and vendor dependencies must match the previously verified optional-Markdown candidate byte for byte. Installation/update evidence is inherited from that candidate, not newly executed. Published pre.1/pre.2 ZIPs remain unchanged. The candidate is not a new release.
