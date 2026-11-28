# Recorded block attributes and image operations

Date: 2026-11-29 JST. Development experiment only; not a release or production migration.

## Capture and replay boundary

The source records the ordinary request before execution, its typed references, and the ordinary registration/deletion result after success. The follower consumes that sequence without a fixture-provided recipe or identity map. Initial author identities come from the existing baseline sidecar and actual normal registrations. Subsequent IDs and image URLs come from the corresponding destination registration results.

`ConstructionBlocks` classifies known core block attributes at capture time. Image IDs, gallery ID arrays and image URLs are references; width, column count and text are not IDs. Recorded JSON paths and byte spans identify substitutions. Replay does not discover references by parsing destination content. WordPress's block attribute serializer writes the prepared request.

Normal media metadata edits, `/wp/v2/media/{id}/edit`, replacement by a new upload and page edit, and explicit permanent deletion have separate contracts. Core's image edit API creates a NEW attachment: the source target and the returned identity are therefore distinct. Rotation/cropping parameters are recorded as input and passed to that same normal API. No direct file modification or database repair is performed by the follower.

Deletion records the successful `deleted` result and the previous attachment identity. Existing result IDs/URLs remain available as historical references, marked deleted. If a user saves a page still containing a deleted image, the source records that state. Replay preserves the dangling reference, as normal WordPress does; it does not resurrect, substitute, or remove the image on its own. A mismatched live/deleted state is rejected.

The development contract, journal option and anchor advance to experiment version 5. Existing records are not migrated or rewritten. Older experiment records do not silently receive inferred block or lifecycle contracts. This does not change production S3 preservation formats.

## Isolated evidence

Fixture: `tests/construction-follow/run-media.py` and `media-operations.py`. Dedicated internal Docker network on dm; synthetic data; no S3, public ports or production requests. Source and destination use normal authenticated HTTP APIs. No source operation recipe is passed to replay.

Sixteen observed operations completed in the same order:

1. Upload image; edit metadata; publish a nested gallery/image page.
2. Rotate the image (new attachment), crop it (another new attachment), then edit page references.
3. Upload a replacement, replace page references, edit its metadata.
4. Remove images from the page; delete the original and two intermediate attachments.
5. Reinsert the replacement; delete it while referenced; resave the page with that recorded deleted reference.

Checks included different destination IDs and an already-present same-name file; unchanged display numbers; exact prepared-versus-stored block content; rendered Japanese paragraph; source/destination edited-image dimensions and decoded pixel hashes; normal 404 after deletion; unchanged prepared destination file. Expected pixel signatures are test oracles only and never enter replay inputs.

An initial whole-file hash comparison failed. The repeated check compares decoded pixels and dimensions instead, which passed for the original, rotated, cropped and replacement images. Binary file identity is not claimed; the precise non-pixel byte difference was not investigated. This changed the test assertion, not reconstruction inputs or image output.

The warm run completed in 37.983 seconds, including 35.260 seconds for source actions and replay. Cold environment preparation took 40.662 seconds. Contract checks: 601 existing sequence checks, 17 plugin contracts, 14 reference checks, 9 new block/media checks, and 4 form participant checks. PHP contract process: 0.131 seconds. Unknown block/attribute semantics and lifecycle mismatch are explicitly checked for rejection.

## Limits and next integration boundary

This proves the captured core REST routes and listed fixtures, not every editor or plugin upload route. Classic admin-AJAX image editing, media trash/restore, third-party in-place file replacement, arbitrary plugin blocks, custom attributes and dynamic block bindings are not claimed. Known block attribute schemas currently cover image, gallery, paragraph, heading, group, columns, column and shortcode; unclassified inputs remain incomplete instead of being reconstructed by guesswork.

Browser JavaScript/editor validation was not exercised. Rendering and HTTP registration/resave were exercised. Production enablement, formal S3 history integration, and release readiness remain separate work. No plugin source was changed to make reconstruction succeed.

Production, existing originals/history, ZIPs and tags remain untouched. No application upload, review email, merge or push was performed.
