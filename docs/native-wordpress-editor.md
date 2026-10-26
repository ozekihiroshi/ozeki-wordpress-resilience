# Native WordPress editing — implementation scope

> Release preparation (2026-10-26): [current distribution scope](releases/wordpress-org-preparation.md) supersedes earlier research gates and draft-only recovery claims. Recovery now preserves saved post status; network exposure is controlled by the target operator. Historical test results below describe their original builds.

The enrolled **dedicated environment** can use WordPress's standard block editor
for posts and pages. This change is not a production rollout or an automatic
conversion of an existing site. Administrators only; other editorial roles are
not enabled yet. The existing worker and initial site-material enrollment are
still required. Classic Editor and third-party Markdown editors are not integrated.

## Save path

1. Open Posts / Pages → Add New, or edit an enrolled post/page.
2. Write content, select a supported publication status and save/publish.
3. A bounded adapter converts static core blocks into independent material nodes.
   The full desired generation includes publication intent and request-derived Q.
4. The existing journal worker stores and verifies the immutable generation.
   Before confirmation, the public post content and status remain unchanged.
5. The same WordPress post is updated only after confirmation. A new editor may
   create an empty auto-draft shell first; it contains no submitted body and is
   not a published version. The confirmed projection adopts that shell.

Images use the same queue, through the media REST endpoint and the standard
media uploader. The uploaded temporary HTTP file is not registered as a WordPress
attachment until storage is confirmed. PNG/JPEG only, up to 4 MiB and 10,000 px
per dimension. Originals are retained; generated thumbnail sizes are not provided.

## Supported content and explicit exclusions

- Core paragraph, heading, list, quote, image and static classic/freeform HTML
  limited to the same allowlisted markup; emphasis and links are retained.
- Internal links and images refer to protected material IDs rather than the old
  WordPress host. The initial scope retains basic content, not arbitrary styling.
- Draft, pending, private and published status. Reconstructed targets always
  remain drafts; a source publication request never auto-publishes a recovery target.
- Custom categories/tags, excerpts, custom metadata, featured images, custom
  authors/dates, scheduled publication, comments/pingbacks, passwords, templates,
  forms, shortcodes, custom/dynamic blocks and third-party editor integration are
  not supported. Unsupported content/settings stop the save instead of being
  silently omitted. Comments and pingbacks must be closed.
- Internal page-anchor links are not yet supported and are rejected before queueing;
  the adapter must not silently drop the fragment. External link fragments are retained.
- Existing portable ASCII slug restrictions remain. A new item without a slug
  receives a stable generated slug; arbitrary localized slugs are not yet supported.
- Standard media registration is supported; full attachment metadata editing,
  cropping, replacement, deletion and bulk editorial operations are not included.

## Failure, concurrency and restart

The editor keeps the receipt it opened. Stale editors cannot overwrite a newer
generation. Concurrent differing requests cannot replace an existing pending
request. Failure leaves the public projection unchanged. Open **S3先行編集** to
inspect and resume the same journaled request. Do not submit a replacement request
when storage outcome is unknown; existing reconciliation rules still apply.

The block-editor operation and native multipart uploader poll asynchronously for
up to three minutes after acceptance. On timeout, the durable request survives.
Browser closure does not mean cancellation. Source application still needs the
browser or the explicit resume/apply operation. Autosave endpoints remain blocked;
the explicit Save/Publish operation is the protected commit point.

New block/status generations identify `portable-nodes-v2`; legacy v1 generations
remain readable. Published source projections are labeled `verified-source`;
isolated recovery targets retain `verified-private` and never auto-publish.

## Validation

Run `python3 -m unittest discover -s tests -p test_native_materials.py` for the
save-before-write rejection and generation/Q contract checks. Run
`python3 tools/run-site-editor-lab.py --allow-dedicated-lab --native --output NEW_PATH`
for a new internally networked WordPress/DB/browser with generated data. This
uses a filesystem S3 test double unless `--live-s3` is explicitly selected. A
passing double test must not be presented as a new real-S3 result. Existing sites,
Docker resources and production permissions must remain untouched.

### Recorded result (2026-10-23)

The final generated-data browser scenario passed 19 checks, including native
post/page publication, image REST and media-modal registration, reopening core
blocks, unchanged public content on failure, stale-editor rejection, and restart
from the same stored generation after interruption. The last browser run used the
HTML canonicalization fix. The exact editor-produced generation from the preceding
run was also rebuilt after removing its source WordPress; request-derived Q matched,
the target stayed private, and no external side-effect attempts were recorded.

The newly exposed product defect was a byte difference introduced by WordPress
KSES for self-closing image tags. The shared renderer now canonicalizes before
both source and recovery writes; comparison remains strict. A real WordPress KSES
fixture also verifies idempotence. This follows WordPress's documented
[attribute reconstruction behavior](https://developer.wordpress.org/reference/functions/wp_kses_attr/).

Docker startup/read-only timeouts and WSL user-session warnings are environment
issues. An additional link-coverage assertion in an intermediate follow-on script
was a test setup issue; the final editor scenario includes the link. Earlier failed
attempts remain on disk. These results use the filesystem S3 double, not new live-S3
evidence. See [machine-readable results](../evidence-public/native-editor-validation.json).

Update the plugin **and** external worker together for `portable-nodes-v2` support.
The native adapter requires PHP's DOM extension. Production enrollment, general
editor/plugin compatibility remain outside
this validation. No release or production rollout was performed.


### Live S3 validation (2026-10-23)

The standard editor scenario passed all 19 checks against the experimental S3
bucket: post/page creation, publication and update, native REST and media-modal
image registration, failure preserving published content, stale-parent rejection,
and restart from the same committed generation. The source WordPress and database
were then removed. The exact final editor generation was read through fixed S3
Version IDs, retention and SHA-256 checks and rebuilt into a fresh private
WordPress. Its logical result matched request-derived Q, including images and
internal links; no external side-effect attempts were recorded. The source DB
was not a reconstruction input. Recovery publication remains disabled.

The first live trial exposed a product defect: media-modal registration waited
only 12 seconds in one HTTP request, so a still-running S3 save appeared as a
failure. It is now asynchronous: acceptance does not claim an attachment exists;
the native uploader polls the existing state API, checks request identity, applies
only after storage completes, and passes the resulting attachment to WordPress.
Failures and bounded polling expiry preserve the request for explicit resumption;
the browser does not resend an uncertain upload. The media queue completes before
the next image begins. Three regression cases cover delayed success, failure, and
changed operation identity. The first failed trial and its 17 acknowledged PUTs
remain preserved; no uncertain PUT was found.

Environment: WSL user-session warnings and Docker startup delays were observed;
neither service was restarted. The trial reused a process-scoped IPv4 preference.
Bucket listing is not granted to the existing lab writer. Therefore namespace
emptiness was **not** established by listing: the trial used a new random prefix
and every PUT retained `If-None-Match: *`. No IAM or existing retention was changed.

Test infrastructure: the media assertion now allows 220 seconds and requires the
native uploader queue to drain, rather than a 40-second DB-only check. Saving
failure was injected before PUT, and interruption after generation commitment;
these are deterministic fault injections, not a claim to have caused an AWS outage.
The successful browser run needed no manual completion assistance.

See [live-S3 evidence](../evidence-public/native-editor-live-s3-validation.json).
The earlier filesystem-double evidence remains separate. Trial containers were
removed; immutable S3 trial objects and local journals were retained. This did not
publish a release or modify production.
