# Protected WordPress editor (opt-in prototype)

The existing three-page save API now has an editing UI. In a dedicated deployment that explicitly calls `Owr\RbrWordPressEditor::boot($ids)` alongside `RbrWordPressSaveApi::boot($factory, $ids)`, WordPress's normal **Edit** link for an enrolled page opens a bounded replacement screen. The normal administration plugin bootstrap and ZIP still do not enable this component. This is not Gutenberg or a general editor integration.

## What the operator does

1. Open an enrolled company, services or contact page from Pages → Edit. Change title, slug or plain-text paragraphs; existing images and relationships are preserved. Other enrolled pages are carried forward in the same immutable site-generation request.
2. Click **S3へ保存して反映**. This is an explicit update of already published test pages, not automatic publication. The screen is locked while confirmation is pending. WordPress public content changes only after S3 confirmation and atomic DB projection.
3. If unresolved, use **同じ保存を再開**. The server stores the full frozen request before S3 work, so reloading or reopening the editor can recover that exact request without relying on browser storage. Do not create a replacement operation or clear the journal. Reopening on another enrolled page still resumes the complete three-page request.
4. On conflict, the screen retains the attempted edits and refuses overwrite. **最新状態を読み直す** explicitly reloads current state, with a warning before discarding dirty edits. Review and re-enter the change against the current generation.

The UI distinguishes loading/unavailable, editable, saving, incomplete, S3-confirmed but not projected, conflict/drift, invalid input and applied states. Network failure is not reported as definite failure: the same request reconciles an unknown result. The applied operation ID distinguishes a lost successful response from a competing edit. Completion is shown only after the save response and successful state refresh. No automatic retry, signing, expiry extension or public activation is added.

## Boundaries and implementation

`GET /owr-rbr/v1/editor` reads the local journal only, sends no-store, and requires cookie/nonce authentication and edit permission for all three pages plus publish_pages. It exposes editable values, applied sequence and pending frozen input, not paths or credentials. Source drift blocks editing. `POST /save` is reused; it records submitted input and a stored checkpoint before the existing post-S3 fault boundary, and updates editable state in the same transaction as the three page rows.

Protected `post.php` GET edit requests redirect to this screen; direct classic form mutations return 409. Existing core REST mutation rejection remains. Unrelated pages retain their normal editor. This does not claim interception of every plugin, XML-RPC, admin-ajax, bulk action or direct SQL path; those remain deployment restrictions and drift detection boundaries.

Fresh enrollment accepts existing plain `<p>text</p>` paragraphs only; it refuses richer HTML instead of dropping it. Images/relationships remain the fixed enrolled assets. New media, ordinary posts, Markdown, arbitrary blocks, revisions/save hooks, persistent object caches, pending-operation abandonment and journal compaction are not implemented. Existing pre-editor journals without editable source state fail closed in the UI; no automatic enrollment/reset or migration is provided. Authorization, signature, revocation and retention requirements remain unchanged.

## Verification

Real Chromium/WordPress HTTP/MariaDB with the persistent S3 double exercises the screen, failure preservation, frozen-request recovery after reload, conflicting and stale editors, post-S3 interruption/resume, permissions, nonce and direct form bypass rejection. See [evidence](../../evidence-public/rbr-wordpress-editor.json) and [applied screen](../../evidence-public/rbr-editor-applied.png). Previous actual-S3 API evidence is separate; this UI trial is not another live-S3 or production-editor qualification.

Reproduce with `tools/run-rbr-wordpress-editor-lab.py --output NEW_PRIVATE_DIRECTORY --vendor-cache LOCAL_COMPOSER_VENDOR`. Linux/WSL, pinned local WordPress/MariaDB images and the locally installed Chrome/ChromeDriver image are required. Containers share an isolated network namespace with no public ports and are removed afterwards. Private browser logs can contain test cookies; publish only the curated evidence/screenshots. No production environment or S3 objects are changed.

## Real S3 browser boundary

`tools/run-rbr-wordpress-editor-s3-lab.py` reuses the editor browser scenarios and the scoped S3 transport from the API lab. It requires a new private output directory, a matching local Composer vendor cache, and a fresh `--case api-...` prefix. A successful read-only exact-prefix empty check is required before writes. The WordPress/browser network has no external route or published ports; the test-only Unix socket broker performs scoped S3 calls with the existing separated roles. This is a laboratory transport, not a production credential deployment or latency qualification.

The live scenario creates three generations: failure before commit and same-request retry; a winning edit and stale-editor refusal; then process interruption after S3 commit and exact-version resume. Existing offline browser evidence covers additional response-loss/UI-only cases without repeating cloud writes. The injected 503 is not an observed AWS outage. Originals saved before a failed commit remain retained; neither the journal nor S3 objects are deleted. Existing signature approvals and retention conditions are unchanged.

Live acceptance: [browser + real S3 evidence](../../evidence-public/rbr-wordpress-editor-s3.json).
