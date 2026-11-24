# Completed-operation fixes — 2026-11-24

Additional changes on `codex/update-preservation-contract`, starting at `629c245`. No main merge, push, release ZIP, submission, reviewer email or production deployment was performed.

## Changes and results

- **Publication:** Preserve moves to scheduled/draft state. Capture completed scheduled publication without requiring an interactive editor identity. Body, status and anonymous publication queries match after recovery.
- **Authorship:** Preserve display definitions and article assignments independently of body edits. Update existing inert recovery authors without changing prepared privileged accounts. Renames and deletion/reassignment match on fresh and reused destinations.
- **Comments:** Capture completed trash/spam operations with their previous approval state and timestamp, including removal of transition metadata. Do not certify the intermediate status row. Both approval directions, including stale Baseline metadata, match.
- **Attachment deletion:** Retain completed deletion evidence, remove related thumbnail references and attachment comments, and distinguish known deletions from unexplained missing originals. Remaining body links no longer block an ordinary edit after a known deletion. A fresh destination does not receive the deleted file.

If a previously recovered file still exists at a reused destination, recovery reports it before replacing content. It does not indiscriminately delete prepared files; a clean uploads location must be prepared and checked again.

Round-trip verification exposed one additional related cause: an article already present in Baseline did not inherit the daily record's protection identity. A recovered draft therefore stopped being tracked. Replay now carries that identity regardless of whether the article was already in Baseline. Editing the recovered draft and recovering its next history restores the edit without publishing it.

## Verification

Disposable, internal-network-only WordPress 7.1.4 / PHP 8.3 containers on dm; synthetic data; file-backed S3 transport. Every group completed recovery, standard-API use, editing, recapture and recovery to another fresh WordPress. Existing test objects retained their hashes.

A forced comment-history write failure retained one pending operation and no confirmed history. Resume produced one confirmed operation and cleared the queue, preserving the prior approval state. Attachment caption/alt updates and comment-child reassignment after deletion remained correct.

PHP 8.1 offline checks covered completed state, scheduled capture, protected identity, attachment deletion/pending state, core contracts/formats, comments, missing attachment originals, native details, editor saves, failure diagnostics and application rules. The unchanged rc.21 reader rejected the new original, Baseline and independent index formats. PHP lint: 34 files, zero failures. `git diff --check` passed.

A test-runner staging-directory error was corrected and the affected scenarios rerun. The older attachment mock was updated to distinguish deletion start from completion. Intermediate failed runs remain recorded separately from passing results. Test containers, volumes and networks were removed.

## Prerelease compatibility

Per the user's decision, saved-data compatibility between prerelease candidates is **not guaranteed**. The contract is now `owr-core-updates-2`; the unpublished version-1 contract is not silently reinterpreted. No complex legacy migration mechanism was added.

Use the same supported build on a healthy source and prepared destination, resolve pending saves, and create and verify a fresh trusted Baseline. Existing originals/history remain unchanged. Missing historical approval or deletion evidence is not invented. README, readme.txt and update guidance carry this policy in English and Japanese where applicable.

## Limits and preserved assets

This is standard-API verification with simulated S3, not real-S3/IAM, browser, Plugin Check, release packaging or GitHub Actions completion. Final diff review and representative real-S3 verification remain before integration/release decisions.

Production, existing S3 originals/history and the research checkout's seven modified files were untouched. rc.21 ZIP SHA256 remains `ec0b5cbedd7855054d87ef5656ffcfbde25335c25d4e939b0291d73acf0874de`; tag object remains `515f13f167e80cd7da4c3a1c129aad35452cb6de`.

See `followup-verification.json`, `followup-source-hashes.json` and `tools/testing/core-update-scenarios/followup/`. Detailed synthetic logs remain in `D:/workspace/wp-rescue/release-readiness/completed-operations-fix-20261124/`.
