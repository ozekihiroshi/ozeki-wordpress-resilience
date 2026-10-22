# Protected three-page save API (prototype)

This opt-in development component connects an authenticated save request to the existing `RbrGenerationCoordinator`, then projects the exact committed originals into three enrolled WordPress pages. It is not loaded by the normal administration-plugin bootstrap. It does not change reconstruction approval, signing, revocation or expiry rules.

## Flow and ownership

POST `/owr-rbr/v1/save` accepts exactly `operation_id`, `expected_sequence`, and `pages` containing company/services/contact objects (`title`, `slug`, plain-text `paragraphs`). All three pages must be editable by the authenticated user, who must have publish_pages. Normal REST cookie authentication requires its WordPress nonce. Client-supplied file paths, S3 references, job deadlines and page IDs are not accepted.

A dedicated InnoDB state row binds each operation to an immutable input digest and job. Only one unresolved operation may exist. Reserve the operation before S3 work, release the DB transaction, and use the existing immutable original/generation coordinator. After confirmation, retrieve the exact fixed originals and render them, then lock the state and all three page rows on one dedicated mysqli connection. Validate sequence, pending owner and previous page fingerprint before updating the three rows and applied generation in one transaction. The dedicated connection never reconnects or automatically replays a query.

S3 failure leaves public rows unchanged. A crash after S3 commit is reconciled by the same operation/job. A crash inside the DB transaction rolls back page changes. If a response is lost after DB commit, replay returns the recorded result. An old completed operation may return its historical receipt but cannot reapply it over a newer generation. A different operation cannot pass an unresolved save. Unknown or expired operations are not discarded automatically.

## Deliberate limits

- Existing three published root fixed pages only; no creation/deletion, scheduling, post/status/type changes, ordinary posts, Markdown or arbitrary blocks. Only title/slug/plain paragraphs are editable.
- Images and relationships are pre-enrolled fixed assets. The source media file must match the S3 bytes. Upload interception, attachment creation and changing relationships are not included.
- Projection uses narrow prepared SQL updates, not arbitrary WordPress save hooks. This avoids assuming hooks/files/external effects are rolled back by InnoDB. Revisions, plugin save hooks, SEO integrations and persistent object caching are unsupported. Same-operation recovery is not a general-purpose DB migration.
- Dedicated provisioning must create an InnoDB `{posts_table}_owr_projection` table with `id INT PRIMARY KEY, state LONGTEXT NOT NULL`, insert row 1 with `{}`, then explicitly enroll through the service. Trusted page IDs, media mapping, seed assets, private workspace and store must be supplied. The public API cannot enroll/reset these.
- Core REST mutations for enrolled page IDs are rejected, including autosave/revision subroutes. Unrelated pages retain their normal REST flow. The editor button integration, admin-ajax, Classic/XML-RPC/WP-CLI/direct SQL and arbitrary plugin writes are not comprehensively intercepted. Protected-row drift is rejected on the next save. Do not claim complete authoring protection.
- One site and at most 100 operations in this prototype journal. Terminal/expired unresolved-operation recovery, cleanup/compaction and operational status UI remain future work. Do not manually clear a pending operation to bypass reconciliation.
- No external-cache support; no live-site adoption wizard. The source HTTP display uses WordPress's ordinary DB content after projection. The DB is not the reconstruction original.

## Earlier offline acceptance scope

The dedicated lab uses real WordPress, its HTTP REST API and MariaDB, and the existing persistent filesystem S3 contract double. Fault injection includes a failed S3 commit, a PHP process exit after S3 commit, and a process exit during the page transaction. It proves the new API/projection boundary; it is not a new real-AWS end-to-end test. Prior live coordinator evidence remains separate. No production services, AWS permissions, live bucket objects, public ports, approval renewals or automatic publication are changed.

## Real S3 save/projection acceptance (2026-10-23)

The same opt-in API now has a dedicated real-S3 acceptance run: 25 checks passed with actual HTTP WordPress, MariaDB, the existing scoped SSH S3 broker, immutable versions and per-object GOVERNANCE retention. This is a test connection, not a production connector or editor integration. No runtime API/coordinator changes were needed.

The fresh experimental prefix was confirmed empty before writes. A deliberately injected 503 **before** commit PUT left all public page rows unchanged; retry used the same operation. PHP termination after S3 commit resumed the exact Version ID, and termination inside the DB transaction rolled back all page updates before resuming. A competing request, stale sequence and changed payload were rejected; replay of an old completed operation did not overwrite newer content. Four committed generations remained, and the new text was visible over private WordPress HTTP. Every recorded transport request has a terminal response; no blind resubmission was used.

WordPress and MariaDB have no external network or published ports. A private Unix socket connects the test WordPress to a host-side broker restricted to this new experimental prefix; existing SSH roles keep credentials outside WordPress. New objects use the existing explicit 36-day retention mode; bucket policy/defaults and previous retention are untouched. Dedicated containers are removed, evidence and retained S3 versions remain. Test interruption and storage failure are injected, not reported as infrastructure outages or discovered plugin defects.

See [live evidence](../../evidence-public/rbr-wordpress-save-s3.json). Earlier offline evidence remains separately labelled. This does not add normal editor/upload interception, post/Markdown support, pending-operation abandonment or production activation. The current API is synchronous, and the experiment broker makes individual SSH round trips; this is not an editor-response-time acceptance test. Reconstruction signature/expiry checks are unchanged; this run tests authoring projection, not another reconstruction run.

Follow-up: the opt-in bounded editor is now available; see [editor contract](rbr-wordpress-editor.md). The earlier editor-button gap does not describe this narrow replacement screen; generic editor/upload integration remains unsupported.
