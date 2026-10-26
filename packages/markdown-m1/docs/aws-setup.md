# AWS setup — one site, one prefix, complete policies

[日本語](aws-setup-ja.md) · [Return to user guide](user-guide.md)

## 1. Supported example and worksheet

This example is one AWS account, a general-purpose S3 bucket in the standard `aws` partition, SSE-S3 encryption, and WordPress on EC2 using its instance role. No access key is stored in WordPress. These templates cover the product's prefix operations, not provisioning permissions or unrestricted console browsing. Cross-account access, customer-managed KMS keys and non-EC2 hosting require separate administrator design; these files do not pretend to cover them.

| Value | Example / replacement |
|---|---|
| Bucket | Replace **every** `replace-with-your-bucket` in the JSON with your actual bucket name (no `s3://`) |
| Prefix | Replace **every** `sites/example-site/` with your site's dedicated prefix, including the trailing `/` |
| Region | Record the bucket's region, for example `ap-northeast-1`; enter it in the plugin |
| Owner | Record your bucket owner's 12-digit account ID; enter it in `owner` |
| Saving role | Record the actual role attached to the source EC2 instance |
| Recovery role | Record the different read-only identity used by the destination |

The bucket/prefix are fictional placeholders, not the development lab. Do not use a role with broad existing S3 grants and assume these Allow statements restrict those other grants. These files are a complete **product-specific identity policy**, not an account-wide permission boundary. Explicit denies apply only to this prefix. Other policies, bucket policies, organization controls and permission boundaries still participate in authorization.

## 2. Prepare the bucket

An AWS administrator performs these steps with provisioning privileges, not with the restricted product role.

1. In S3, select a bucket approved for this site's recovery assets, or create one in your chosen region. Use a dedicated prefix; keep Block Public Access enabled and ACLs disabled (Bucket owner enforced). This data does not need public access.
2. Under **Properties → Bucket Versioning → Edit**, enable versioning. Record the region and owner. Do not suspend versioning after use. [AWS versioning instructions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/manage-versioning-examples.html).
3. For this example use default encryption **SSE-S3**. Do not substitute SSE-KMS without also designing its key policy, read/write permissions and key availability at recovery time.
4. Review **Management → Lifecycle rules**. No rule may expire current/noncurrent versions or move needed resources into a restore-required archive independently of the product's retained chains. Do not delete originals by their age: an old image may still be required by a recent point. The product's cleanup is aware of those relationships; S3 age-based expiry is not.
5. Decide whether to use optional Object Lock before starting. The simple example requests no lock (`retention_days=0`). If you choose locks, the bucket must support Object Lock and the configured days must suit your retention plan. Defaults/existing locks can delay deletion after product expiry; changing the plugin to zero does not shorten them. The product never bypasses retention/Legal Hold. Enabling Object Lock is a lasting bucket choice, not a harmless toggle. [AWS Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html).

Versioning alone is not protection against authorized fixed-version deletion. Conversely, expiration of a lock does not itself delete a resource. GFS retention and the detailed-history window decide product eligibility; AWS lock state and IAM decide whether a deletion is possible.

## 3. Set up standard EC2 authentication

The AWS SDK PHP default chain can obtain temporary credentials from the EC2 instance profile. Other configured providers can take precedence; check the identity actually used by PHP, not only an interactive shell. [AWS credential-chain documentation](https://docs.aws.amazon.com/sdk-for-php/v3/developer-guide/guide_credentials_default_chain.html).

In **EC2 → Instances**, select the intended instance, then **Actions → Security → Modify IAM role**. If it already has an operational role, retain that role and edit only its dedicated Resilience policy as described below; do not replace the role and lose its other responsibilities. For a new role, use IAM's **AWS service → EC2** trusted entity and attach the selected product policy. Never attach the source writer role to the recovery host merely for convenience. [AWS role attachment](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/attach-iam-role.html).

The web PHP process must reach the standard instance metadata service. For containers, metadata reachability/response hop limits may differ from the host. Have the server administrator check that configuration; do not disable IMDSv2 or introduce a credential relay as a workaround. Non-EC2 environments may support standard SDK providers, but this guide does not certify an untested hosting setup. The plugin has no key-entry form.

## 4. Choose and install one complete policy

Download a complete file, replace the worksheet values throughout, and paste the **whole JSON**. Do not append fragments or attach both source variants.

| Complete file | Purpose |
|---|---|
| [source-no-delete.json](aws-examples/source-no-delete.json) | Saving, readback, Checkpoint creation and full retention preview; explicit fixed-version deletion deny. Start here. |
| [source-with-cleanup.json](aws-examples/source-with-cleanup.json) | Same operations plus fixed-version deletion in the exact site prefix. Use only when enabling policy-based cleanup. |
| [recovery-read-only.json](aws-examples/recovery-read-only.json) | Listing, original/fixed-version reading and lock inspection; explicit object mutation deny. Use on the destination. |

Both source variants allow PutObjectRetention for optional locks; neither permits Legal Hold changes or retention bypass. The cleanup variant still denies unversioned DeleteObject, so it does not create deletion markers as a substitute for removing reviewed versions. ListBucket/ListBucketVersions are restricted by `s3:prefix` on the bucket ARN; object actions use the site-object ARN. There is no IAM action called HeadObject: the relevant GetObject/GetObjectVersion permission supplies it. [AWS S3 operation permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html).

Console procedure:

1. Open **IAM → Roles → the recorded source or destination role → Permissions**. Verify the role really belongs to that host.
2. If a dedicated Resilience policy exists, open it and choose **Edit → JSON**. Replace its entire document with the chosen, substituted file. For a managed policy save the new version as default; for an inline policy save the edit. Do not create a second policy at every change.
3. If this is the first setup and no dedicated policy exists, add **one** product-specific inline policy using the full JSON. Later changes replace that same policy. Do not overwrite a shared policy containing unrelated service permissions; first have its owner separate the product-specific scope.
4. Review the exact bucket, prefix and actions before saving. No `s3:*`, all-bucket ARN, IAM management action, or bypass is needed.
5. To enable cleanup later, replace **source-no-delete** with **source-with-cleanup** in the same policy. Any separate explicit Deny covering the prefix still wins: an Allow cannot cancel it. Do not remove a broader shared Deny blindly; have the administrator resolve the scope. The recovery role stays read-only.

These samples do not set S3 Lifecycle, change bucket configuration or grant EC2/IAM administration. They do not modify bucket policies. Full S3 console navigation may need extra user-console permissions; do not broaden the product's role just to browse the console root.

## 5. Verify from the product, not only the shell

Return to [installation and Baseline](user-guide.md#3-create-the-first-baseline). After saving settings, a successful complete initial snapshot demonstrates that the product runtime can write and fixed-version read the captured set. A confirmed normal edit checks history; a preview checks full-version/lock-reading access without deletion. Later confirm a restore with the separate read-only destination. Do not claim any of these checks succeeded merely because a policy was saved or `aws sts get-caller-identity` works in another session.

If AccessDenied appears, record the operation and exact scope. Check the runtime identity, policy substitutions, explicit Deny, bucket/KMS conditions and environment credentials. Never use AdministratorAccess as the product's error workaround. A lock with an unexpired date/Legal Hold is a blocked deletion condition, not a request to bypass it. Unknown/network errors are not treated as “no lock.”

The templates were statically checked against the current calls and AWS documentation (2026-10-26); they were not newly applied to AWS. See [remaining confirmations](remaining-confirmations.md). Keep the worksheet and a read-only recovery setup record outside the source server, but never put credentials in this documentation or a support request.
