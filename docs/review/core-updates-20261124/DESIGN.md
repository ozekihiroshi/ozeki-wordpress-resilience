# Daily core updates: bounded correction

Work in progress on `codex/update-preservation-contract`, based on main `4053e1d`.
No release, production deployment or WordPress.org submission is part of this change.

## Cause and scope

The complete initial save already included these fields, but daily history did not
share the same fields and completed-operation hooks. A successful body save was
therefore insufficient evidence that related information had been preserved.

| Information | Correction |
|---|---|
| Article password and author | Share explicit fields between capture and replay; include the author description without importing credentials or privileges. Missing passwords are different from an explicit empty password. Check actual saved fields before confirmation and on retry. |
| Categories and tags | Record completed native taxonomy state, including unused terms, ancestors, deletion and assignments. New native article-detail records no longer apply their own copies of taxonomy definitions. |
| Comments when a parent article is trashed/restored | Record the completed comment states and WordPress's existing parent-post trash metadata, including the original slug needed by untrash. Reuse comment replay validation. |
| Basic settings | Record only `blogname`, `show_on_front`, `page_on_front`, `page_for_posts`, `timezone_string`, `gmt_offset`, `posts_per_page`. Preserve destination software/operational settings using the existing application rules. |

The existing durable shared queue, writer lock, fixed-version readback and formal
sequence remain authoritative. A failed capture remains pending; a failed S3
confirmation retains its frozen payload. Resume is available in the existing UI.
Core-state captures are coalesced to the completed request state and identical
confirmed states are not recorded repeatedly.

## Compatibility and deployment

Upgrade the healthy source and prepared recovery destination together. Resolve
pending operations, pause editing and create a new trusted initial save on the
source. This is the migration boundary; do not infer missing past changes.
Do not deploy this work until verification and review are complete.

New original, complete snapshot and independent-index format identifiers require
an updated reader. Existing objects and frozen legacy queue entries are not
rewritten or relabelled. Old original parsing remains available.

A complete old baseline can contain its actual password state. However, older
article history after that baseline omitted password changes. If such history is
selected, restoration stops **before replacing destination content**, with an
instruction to create a new initial save from the healthy source. Individual
restoration of those incomplete article records also requires the new contract.
No inferred-password or persistent manual-publication migration system is added.

## Verification

Re-use the synthetic fixtures that exposed each defect. Compare actual WordPress
records and anonymous password requirements after each operation, then use a
separate prepared WordPress for a second recovery after resaving. Existing
fixture objects must retain their hashes.

Check old-format readability and execute the unchanged rc.21 reader against new
originals, complete snapshots and independent indexes. Keep the submitted ZIP
unchanged. Test the shared queue's existing failure/retry boundaries and add
small contract checks for missing fields, stale taxonomy application and the
option allowlist. Results are recorded separately; this document alone is not a
claim that verification has passed.
