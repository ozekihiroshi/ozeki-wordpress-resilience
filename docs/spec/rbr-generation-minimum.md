# Minimum S3-first generation implementation

Prototype, 2026-10-22. [日本語](rbr-generation-minimum-jp.md). Implements the storage boundary of [coordination v0.2](../review/rbr-coordination-contract.md); it is not yet the WordPress editor integration or a released recovery product.

## What runs

- `src/RbrObjectStore.php` reuses unchanged `VersionedAssetStore` conditional upload, pinned download and hash verification. New checks enforce dedicated 36-day default governance, observed fixed-version protection, site scope and bounded storage.
- `src/RbrGenerationCoordinator.php` persists an immutable operation intent, stores selected originals, validates their small typed package and commits the next immutable numbered slot. Retries reconcile already stored bytes and committed results, including with missing original local files. Source WP is never written: result has `wp_state: not_applied`.
- Short-protected references are retrieved by fixed Version ID and re-uploaded under an operation-specific copy key. Logical asset/revision/hash/provenance survive; default protection is checked. No retention-write, legal-hold or delete API is called.
- Conditional-slot collision cannot overwrite a winner. Old complete generations remain when preparation/PUT/copy fails. A late commit or invalid retention produces an error even if the immutable object exists; never delete it to retry.
- The server Date is compared against local time; LastModified detects a late commit. These checks are not a trusted-time service or a global security proof.

Initial input is deliberately narrower than the whole design: exactly three page roles (company/services/contact), plain-text paragraphs/title/slug, one or more JPEG/PNG images, typed link/image/navigation edges and a role Profile. No editor HTML conversion, dynamic blocks, layout, headings, anchor conversion or WordPress importer is added here. Unsupported structured fields/relations are rejected; text is data, not executed/rendered. Image metadata/type/dimensions are inspected, original bytes preserved; this is not full image decoding/sanitization or malware certification. Maximum 16 assets, 8 MiB each, 64 MiB total; maximum chain length 1000. These are prototype bounds, not production sizing.

The three-page fixture is independently generated and contains no real customer data. This component is in the development kit only; it is not bootstrapped from the installable admin plugin. Legacy approvals/Restore/shared backup-core are unchanged.

## Offline execution (no AWS access)

From the repository with Composer dependencies and PHP 8.1+ including GD and pcntl:

```sh
php tests/test-rbr-generation.php
```

The test creates a private temporary tree and an atomic filesystem-backed S3 test double, then removes it. Two actual forked PHP processes compete for the same slot. Other failures include partial upload, response loss, denied discovery, invalid hash, short-retained image, failed/lost copy, expired intent, clock skew, late commit and unsupported relations. The double does not contact AWS, read credentials, emulate IAM enforcement or establish S3 Object Lock guarantees.

[Recorded evidence](../../evidence-public/rbr-generation-minimum.json): 21 new checks passed. Thirteen PHP/test-distribution invocations passed in the recorded run (including the new suite). Source hashes bind the tested code. Existing `test-versioned-transfer.php` still passes with its original 35-day behaviour. No ZIP freeze or public release was performed.

## Optional real S3 lab entry — NOT executed in this acceptance

`tools/rbr-save-lab.php` binds the same component to the AWS SDK. It permits only explicitly configured `owr-rbr-lab-*` bucket names, environment `synthetic-lab`, the expected owner, no custom endpoint and no inline credentials. The bucket must already have versioning and a 36-day default governance configuration. It does not create a bucket, change settings, edit IAM or delete anything. It fails on the existing 35-day setup rather than weakening the requirement. IAM conditional-create enforcement, separate credentials and no-deletion/lifecycle policy remain installation prerequisites not verified by the offline tests.

Private config shape (example values, not a deployment):

```json
{"environment":"synthetic-lab","bucket":"owr-rbr-lab-example","region":"ap-northeast-1","owner":"123456789012"}
```

Generate a new private synthetic package:

```sh
php tools/rbr-create-fixture.php --output=/private/new-rbr-fixture
```

Only after arranging a dedicated lab and credentials, a deliberate live call is:

```sh
php tools/rbr-save-lab.php --config=/private/lab.json --job=/private/new-rbr-fixture/job.json --execute-lab > /private/result.json
```

Never regenerate the job to recover an uncertain save: keep its operation ID, deadline and content immutable and rerun that same job for reconciliation. An expired uncommitted job requires inspecting the slot before starting a new operation; a committed result is reconciled even after its deadline. Capture stderr/exit code separately; an empty result file is not success. The CLI reports last confirmed stage and error type without SDK request details/secrets. On successful completion, a subsequent synthetic no-content-change generation can be prepared using `rbr-create-fixture.php --output=/private/new-next-fixture --from-result=/private/result.json`. It uses fixed prior refs and a new operation; do not run it to hide a failed/unknown operation.

## Boundaries and remaining work

- Real AWS version/retention/conditional-create/IAM behaviour is **unverified in this run**; no cloud requests occurred. No claim of a live S3 end-to-end pass.
- No WP REST/editor/upload interception, transactional WP apply, public UI, reconstruction or automatic publication yet.
- No independent incident hold gate, global discovery selector, cleanup or recovery reader UI yet. Caller supplies the parent fixed reference; the coordinator validates its ancestry. Do not present this as the full recovery-selection policy.
- Concurrent jobs can prepare extra originals and operation records; they are not automatically deleted. Production bucket policy must enforce create-only semantics; conditional headers alone do not defend against unrelated clients.
- Local/source loss before upload still loses unuploaded bytes. Resume discovers persisted originals; it cannot invent absent inputs.
- No automatically created external EC2, scheduler or production changes. No extension of old signature approval conditions.

## Issue classification

Product implementation: adding observed server timestamps initially made first/retry receipt array ordering differ; normalized the receipt and reran the suite. No residual failure in the recorded checks. Test infrastructure: atomic filesystem model intentionally substitutes for S3 and does not prove IAM/retention enforcement. Environment: unprivileged WSL access was denied by tool permissions; approved execution ran normally. This was not a plugin runtime failure. Actual host compatibility outside this CLI environment remains unmeasured.
