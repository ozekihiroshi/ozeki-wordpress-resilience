# Basic settings round trip

Synthetic, isolated WordPress test. Run `run.py options STAGE` only with the dedicated dm Docker daemon and fixture/overlay paths declared by the runner. Use a fresh stage directory. Never run the PHP probe on production; it requires an `owr-hypothesis-` URL.

The transport uses local files. Do not create `/lab/live` or provide production credentials. Internal networks, blocked external HTTP, disabled email/cron and disposable databases keep the test separate from production.

The scenario checks nine setting changes, article saving, a fresh Baseline control, then edits and saves the recovered site into a different namespace and restores again. Repository runner assertions enforce equality; archived execution also records all comparisons. Evidence and limitations are in `docs/review/core-updates-20261124/BASIC-SETTINGS-FIX.ja.md`.
