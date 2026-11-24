# Completed-operation regression fixtures

Synthetic WordPress API scenarios for publication, author accounts, comment transitions and attachment deletion. These scripts refuse to run unless `home_url()` starts with the disposable test-host prefix `http://owr-hypothesis-`. They are not production administration scripts.

Each fixture uses `/lab` for IDs and recovery references and the existing isolated file-backed SDK transport. The runner prepares private `/tmp/recovery-work`, disables mail, Cron and external HTTP, installs the unchanged rc.21 ZIP then overlays the working source, and removes its own containers/volumes/network in `finally`.

Use the matching isolated runner archived with the verification records. Do not run these files on community or connect their transport to production S3. See `docs/review/core-updates-20261124/FOLLOWUP-RESULTS.md` for actual runs and limitations.

Required assertions:

- Publication: all body/status/public-query comparisons match; execute the scheduled transition only after its real due time, with user ID 0.
- Authors: rename and reassignment match before another article edit; both fresh and reused destinations match, with no imported capabilities.
- Comments: both ordinary and stale-Baseline approval transitions match; forced history failure remains pending and resumes correctly.
- Media: fresh recovery removes the attachment and related state; reused uploads containing a deleted file are rejected before replacement; the next ordinary article save succeeds after a known deletion.
- All groups: `cycle-save` edits and recaptures at a separate prefix; `cycle-restore` to another fresh destination matches supported values and relationships, and all prior object hashes remain unchanged.
