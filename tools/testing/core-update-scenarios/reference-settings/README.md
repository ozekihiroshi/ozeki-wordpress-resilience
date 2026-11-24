# Reference-setting round trip

Run `run.py refs STAGE` only in the dedicated disposable dm Docker environment. The fixture requires a synthetic `owr-hypothesis-` URL. Use a fresh stage directory, the runner's immutable seed assets and current source overlay. Never run on production or enable `/lab/live` in the SDK transport.

The scenario changes and clears category/privacy references, creates new targets, checks WordPress refusal to delete the active default category, then switches category and deletes targets. It saves an article, checks a fresh Baseline, edits the recovered site, creates a new article using its default category and restores again into the other disposable site.

Repository runner asserts state equality. Evidence, compatibility and limitations are recorded in `docs/review/core-updates-20261124/REFERENCE-SETTINGS-FIX.ja.md`.
