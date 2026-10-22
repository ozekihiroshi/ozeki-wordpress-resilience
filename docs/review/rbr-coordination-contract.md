# S3-first coordination, protection and editor entry — contract v0.2

Design only, 2026-10-22. [Japanese](rbr-coordination-contract-jp.md). Refines [v0.1](rbr-storage-contract.md); this document supersedes its open decisions about commit coordination, retention extension and the explicit separate save workflow. No implementation, IAM change, test or deployment. Normal S3-first originals remain normal by premise. Existing Restore/signature approval contracts remain unchanged.

## Decisions

1. Use immutable numbered S3 generation slots with conditional creation, not a renewable distributed lease or an authoritative mutable latest pointer.
2. Standard writer has no PutObjectRetention permission. If a referenced version lacks sufficient protection, write a fresh protected copy of identical bytes. Retention extension is an optional later adapter, not required for initial operation.
3. Integrate the block editor's normal Update/Publish and media selection experience. A server-side coordinator runs before accepted WP writes; client UI alone is not the security or consistency boundary.
4. Existing WordPress/PHP/database plus S3 is sufficient as the architecture. No second EC2, Lambda, DynamoDB or daily approval is required. Host compatibility with the transaction requirements below is an installation prerequisite, not yet demonstrated.

## 1. Commit protocol

The chain starts at generation 1 for a new site identity. Key example: sites/{site_id}/commits/000000000001.json. Each slot contains the complete generation manifest, random generation_id and operation_id, payload digest, exact parent slot Version ID and hash, exact asset references, observed protection deadlines and commit-intent time. Slots and originals are create-only using PutObject with If-None-Match: *. Enforce conditional creation for those namespaces in bucket policy; deny deletion and delete-marker creation to the writer. Do not apply that policy to unrelated bucket contents.

To commit after slot N, validate all dependencies first and conditionally create slot N+1. The object itself is the commit record; do not upload a second independently authoritative commit marker. Concurrent candidates can prepare originals in parallel, but exactly one conditional creation wins the next slot. No multi-object transaction is claimed: unreferenced prepared originals are harmless incomplete work.

- Success: capture the slot's Version ID; record S3 committed, then apply to WP.
- Precondition failure: read the existing slot. Same operation/digest means recover the result; different operation means conflict. Never overwrite or jump to N+2 to evade it.
- 409, network failure or lost response: reconcile that exact slot; retry the same conditional operation with bounded backoff only when appropriate. Do not blindly send an unconditional PUT.
- An editor loaded against an older parent cannot silently publish over intervening work. Keep its draft; display the newer version and ask it to review and save again. Initial version does not auto-merge, even for different pages, to keep the whole-site snapshot rule simple.

The winner is selected without a timed S3 lock. A stopped old request cannot replace a filled slot. This does not protect against a malicious authorized writer producing fabricated new content; incident holds and independent recovery access remain distinct requirements.

Latest pointers/local cache are hints. Recovery enumerates/paginates the commit prefix, validates the contiguous chain from the enrolled baseline and exact parent references, and considers independent holds. Gaps, competing/unexpected versions, unreadable objects or missing provenance stop selection; never silently prefer the largest number. A held generation is not made eligible by being newest. Enrollment material is explicitly marked baseline, not backdated as an upload-time original.

Slot retention must cover dependencies and retained chain records: every prior commit record needed to interpret a retained generation is retained too. Initial no-deletion policy meets this without a compaction implementation. Future cleanup requires checkpoints or preserved ancestry before old commit records can be removed. A timestamp is informational, not chain ordering or a substitute for S3 Version ID.

## 2. Source WP application and stopped workers

S3 concurrency and WP application are separate problems. Initial site has one pending generation at a time for source application: a later protected save waits while an earlier S3-committed generation is unresolved. A fresh recovery site may reconstruct the selected latest eligible commit even if the old site's apply receipt is missing, with that uncertainty displayed.

Application uses a plugin-owned transactional state row keyed by site_id, InnoDB row lock, a unique operation/generation mapping, and the same database connection for the protected page/relationship mutations. Compare and update the applied sequence under that lock; never apply a lower sequence after a higher one. Keep S3 calls and image transfer outside the short transaction. Bound initial page mutations to the three selected pages; pre-stage media after S3 acceptance, with deterministic mappings and staged status, before their use by published pages.

The guarded apply path must forbid silent database reconnect/retry of old writes after transaction loss. Connection identity/transaction loss aborts the attempt; a new request reacquires the row, reads durable mappings and reconciles. Locks release when the connection ends; time passing alone never authorizes a competing request to bypass the guard. No TTL lease is used to prove a former worker is dead. Uncertain commit outcomes are reconciled against generation marker and page fingerprints before replay. Receipt failure is repaired without republishing pages.

This is a requirement for implementation, not a claim that arbitrary WP hooks are transactional. Transaction-control SQL, non-transactional tables, external side effects from third-party save hooks, filesystem changes and object-cache behaviour are outside a generic SQL rollback guarantee. The supported apply path must separate staging/finalization, invalidate caches after commit and expose unresolved finalization. If this host/plugin combination cannot provide the guarded path, protected mode remains unavailable; do not silently downgrade to a lease-only algorithm. Incompatible environments are not required to buy another EC2.

## 3. Retention: choose copy renewal, not broad extension authority

Initial dedicated bucket/configuration proposal: versioning, Object Lock governance default 36 days, no age-based lifecycle deletion for protected namespaces. This is a new installation proposal only: do not change the existing 35-day experimental/production bucket. Product promise remains at least 35 days for a new committed generation; the extra day is processing allowance, not a signature extension.

Set an operation deadline T, at most one hour after its preparation, and require all referenced exact versions to have retain-until >= T + 35 days. Commit must complete before T. Re-read retention if necessary; if the operation expires, reconcile any unknown slot result before renewing the attempt and recalculate protection. Server-derived S3 timestamps/deadlines must be used to detect clock skew; ambiguous timing blocks a completion claim. Verify the committed slot's actual retention too. A gap discovered after commit is protection-error and blocks WP apply; it cannot be hidden by labelling the manifest healthy. Late/unknown requests remain visible rather than forcing a rollback of immutable data.

For an old image/reference:

1. If its observed retention covers the deadline, reuse the fixed version.
2. Otherwise retrieve that exact version, verify hash/bytes and re-upload under a new unique storage-copy key with default bucket retention. Use bounded streaming/temp staging; no additional EC2. No CopyObject requirement in the initial adapter.
3. Record the original logical asset/revision/provenance and the new storage Version ID; verify new retention before commit. The latest manifest reuses this copy on subsequent saves while its protection suffices.

The standard writer may PutObject (conditionally), GetObjectVersion, GetObjectRetention and narrowly scoped discovery/read access needed for reconciliation; inspect required bucket settings. ListBucket is prefix constrained. It cannot delete versions or markers, change retention, bypass governance, set legal holds, change bucket policy/lifecycle/default retention or access another site's prefix. Explicit administrative setup must ensure other policies do not grant those powers. Require the configured default retention and prohibit caller-selected retention overrides for the standard writer. Exact policy JSON and validation are implementation work, not delivered or applied here.

A separate recovery reader and storage administrator remain available without the source WP. Cleanup credentials never reside in normal WP. Broader credential theft/cost exhaustion is not solved by Object Lock; show capacity and bound upload sizes. Optional future extension needs a separately reviewed adapter; remaining-retention-days conditions alone are not treated as a proof of extend-only semantics.

Tradeoff: a frequently edited site may eventually store extra copies of unchanged images, but users do not operate a renewal workflow or maintain a signing/extension service. Copies occur on relevant save operations, not daily. No edits means no renewal job and no automatic deletion. After the lock expires, storage persists under the no-deletion policy; do not advertise perpetual locked protection against administrators.

## 4. Editor and media entry

Initial supported UI is the WordPress block editor for the three enrolled pages. Keep familiar Update/Publish and upload/select actions; show saving to S3, applying, saved, pending or failed. No second confirmation for ordinary saves. Existing WordPress publication confirmation remains; reconstruction publication is separately approved.

A plugin-owned coordinator endpoint receives an authenticated operation_id, base generation, supported body/relations and intended draft/published status. Check nonce/authentication, edit capability for each affected object, enrollment and payload limits server-side. Client editor integration routes final writes here. On the server, rest_pre_dispatch rejects mutation requests to enrolled core page routes that have not passed the coordinator; do not recursively dispatch untrusted core requests. Only the internal guarded apply service performs their writes. rest_pre_insert_page can validate prepared data, but save_post (after write) and wp_insert_post_data (a data filter) are not the primary pre-save barrier.

Revision/autosave content may remain explicitly unprotected and must not modify the published page or shared live metadata. Protect changes to title/body/slug, required-role deletion/trash, featured image, alternative text, navigation and relevant relations—not body text alone. Unenrolled pages are outside protection and not silently blocked. UI hides/disables unsupported Quick Edit/Bulk Edit/trash for enrolled assets, and corresponding server entry paths reject them. Classic editor/XML-RPC/direct WP-CLI/import/custom plugin writes are initially unsupported; known interfaces are blocked for enrolled objects where possible, and drift is surfaced before the next protected save. Direct SQL or arbitrary in-process plugin code cannot be sandboxed by a normal WP plugin; do not claim universal interception. Protection status identifies this supported boundary.

For an image selected in the protected editor, retain a private temporary upload buffer, inspect the JPEG/PNG, save exact bytes to S3 and verify its receipt before moving/registering it as an accepted WP attachment or generating thumbnails. Its separate original acceptance need not create a complete site generation until a page uses it. Use public WP media APIs after the barrier; do not call the private _wp_handle_upload function directly. Core upload/sideload filters provide validation/rejection hooks, not proof all media routes have passed S3. Coordinate both binary and multipart paths explicitly; reject bypasses in the protected media workflow. Uploads on unrelated pages remain out of scope.

An image from the existing library must be explicitly enrolled as a current baseline original before protected use; the UI can do this in the same save flow after the administrator has accepted the baseline policy. Never relabel it as an original captured at its historical upload time. Media changes shared with unprotected pages require either protected metadata routing or a separate protected asset; do not silently use an externally mutable reference.

A timed-out request can return pending with an operation handle; the editor polls/resumes bounded work while open. Closing the browser preserves durable S3 progress; reopening the editor/admin resumes it. Site traffic or WP-Cron is not promised as a reliable autonomous completion service. While pending, the old published content remains until guarded application starts; intermediate staging is not presented as new published content. Unknown states request reconciliation, not an extra upload click.

## 5. Operator effort and release boundary

One-time: choose the three pages, approve initial baseline, configure S3 credentials/protection using a generated checklist/template, save independent recovery access. Normal use: Update/Publish as before. Human action only for editing conflicts, unsupported content, authentication/configuration errors, unresolved failures, incident declaration and eventual reconstruction publication. No daily signatures, retention extensions or external-host maintenance.

New design decisions do not mean implemented support. Before acceptance, tests will need to establish conditional-slot races/unknown outcomes, transaction-loss fencing, all enrolled save/upload entry paths and no-retention-write permissions. This document does not execute those tests or create a release claim. Initial narrow host/editor support must be described honestly; do not expand to every plugin combination before delivering the small end-to-end path.

## References and evidence boundary

The service/WordPress mechanisms below are documented; their combination above is our proposed design and has not been tested.

- [AWS conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html): conditional creation/update and competing-write responses.
- [AWS Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html): per-version protection and default bucket retention.
- [WP REST pre-dispatch](https://developer.wordpress.org/reference/hooks/rest_pre_dispatch/): server-side dispatch interception.
- [WP REST pre-insert](https://developer.wordpress.org/reference/hooks/rest_pre_insert_this-post_type/): prepared-object validation hook.
- [WP upload prefilter](https://developer.wordpress.org/reference/hooks/wp_handle_upload_prefilter/): upload validation/rejection hook.
