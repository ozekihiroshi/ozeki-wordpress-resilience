# Isolated navigation regression scenarios

Synthetic data only. The PHP fixtures reject sites outside the `http://owr-hypothesis-` URL prefix. Never run these scripts on a production WordPress installation.

The runners reproduce the dm test infrastructure recorded in `docs/review/core-updates-20261124/NAVIGATION-FIX.ja.md`. They require the private Docker daemon, immutable rc.21 seed ZIP/core/WP-CLI, and the current source overlay at the paths in each runner. Use a fresh stage name for each run. Do not reuse an existing objects directory.

The SDK transport is file-backed unless `/lab/live` exists. Do not create that file or attach production credentials. Containers use an internal network, disable email and automatic cron, and are removed in `finally`.

Run `sticky-run.py sticky STAGE`, `menu-run.py menu STAGE`, and `permalink-run.py permalink STAGE` sequentially. Comparisons include daily changes, article saves, fresh Baseline controls, and a new write namespace for save/recovery after recovery. The menu scenario additionally deletes the whole menu. The archived exploratory runners logged comparisons; these repository runners also assert that the comparisons pass.

These are API and server-render checks, not browser or live-S3 tests. See the review record for evidence and limitations.
