# Unsupported-plugin coexistence regression

Run only on an isolated Docker host. No production credentials or production S3 objects are used. `run.py` creates an internal network, a temporary MariaDB database and four WordPress sites. Mail is suppressed by the SDK transport fixture. Original objects are kept in a local directory, outside the temporary database.

Prepare a separate working directory containing:

- `run.py`, `fixture.php`, `extra.php` from this directory;
- current product `src/`, `tests/file-scope.php`, `tests/recovery-preparation.php`;
- `tests/transport.php`, named `transport.php`, and WP-CLI as `wp.phar`;
- the unchanged rc.14 ZIP as `candidate.zip` (the legacy reader/writer fixture);
- official plugin ZIPs named `advanced-custom-fields.zip`, `contact-form-7.zip`, `flamingo.zip`, `ozeki-markdown-documents.zip`, `tablepress.zip`, `wp-members.zip`, `download-monitor.zip`, `ozeki-database-backup-for-s3.zip`.

Run `python3 -u run.py` with Docker available. The baseline is deliberately captured with the unchanged rc.14 code and default English before current source is installed. The source fixture then edits supported data. Recovery is tested both with and without unsupported plugins installed; the mixed target edits and saves again, followed by recovery to a third target. Assert original object hashes remain unchanged, supported values match, private PDF is absent and its HTTP response is 403/404, and unsupported post types/meta do not get applied. A 33 MiB unsupported file must no longer prevent capture. A 33 MiB supported file must still fail explicitly. A directory guard must prevent registered files from being included as public media.

`results/summary.json` exists only after all assertions pass. `resources.json` lists exactly the Docker containers, volumes and network created by this run; remove those after collecting evidence. Keep `lab-*/objects`, the baseline references and result files. Do not treat this as a real-S3 integration test or as validation of every third-party access-control mechanism. A fresh recovery target is required; this test does not remove files exposed by an earlier, older recovery implementation.

Observed initial failure and final execution details are in `docs/coexistence-boundary-verification.md` (relative to the product package).
