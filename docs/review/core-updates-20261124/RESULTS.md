# Daily-update correction results

2026-11-24. Verified on the isolated working branch; not merged or deployed.

The initial-save and daily-history contracts now agree for article passwords and
authors, native taxonomy changes/deletions, parent-post trash/comment transitions,
and the explicitly listed basic options. Completed core changes use the existing
durable queue and confirmation mechanism. New article-detail records do not
reapply their own stale taxonomy copies.

Synthetic WordPress comparisons passed for:

- Password setting/removal, private/trash states, and anonymous password
  requirements after resaving and a second recovery.
- Author changes, excerpts, discussion settings, parent pages and ordering.
- Category/tag names, slugs, descriptions, ancestors, moves and deletions.
- Parent-post trash/untrash/deletion and comment approval states.
- Front-page selection, site title, timezone and reading-page size.

Each group was resaved after recovery and restored to a separate newly prepared
WordPress. Existing fixture objects retained their hashes. A deliberately failed
formal-history PUT remained pending; resume confirmed the frozen original without
rewriting it.

An additional defect appeared during actual untrash on the restored site:
comments returned correctly, but the post slug retained `__trashed`. Preserving
and applying WordPress's `_wp_desired_post_slug` fixed the normal untrash operation;
untrash, resave and second recovery then passed. No initialization workaround was
added.

Small offline checks cover required-field loss, explicit password removal,
structured-author equality, stale taxonomy reapplication, shared terms belonging
to another taxonomy, and the option allowlist. Relevant existing queue,
application, nonce/editor, attachment, recovery-point and no-installation checks
also passed. Principal contract/application checks passed on PHP 8.1 and 8.3.
New offline checks are added to the existing Actions workflow; no push or GitHub
Actions run has occurred at this stage.

Legacy originals remain readable. The unchanged rc.21 reader rejected new
original, complete-snapshot and independent-index formats. Upgrade both sites and
create a fresh trusted initial save from the healthy source. Older article tails
that omitted password changes require that new initial save before replacement;
missing values are not guessed.

The integration checks used disposable WordPress 7.1.4/PHP 8.3 containers on dm,
synthetic data, an internal-only network and a file-backed S3 SDK test transport.
They do not constitute browser or real-S3 integration checks. Those bounded
integration checks and final diff review precede a merge decision.

Production, existing S3 originals/history, the submitted rc.21 ZIP/tag and research
working changes were untouched. No new ZIP, submission or reviewer email was made.
See [machine-readable summary](verification-summary.json) and
[reusable scenarios](../../../tools/testing/core-update-scenarios/README.md).
