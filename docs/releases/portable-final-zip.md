# Portable extraction and preview — final ZIP acceptance

Experimental prototype 0.1.0-dev.1. No production changes, automatic publication, tag or formal release.

- `ozeki-wordpress-resilience-0.1.0-dev.1.zip`: SHA-256 `0537301b4f85b52cbd363c2b5909806b367c5a3d9bc40933325b31f88af51cfb` (35162 bytes).
- `owr-development-kit-0.1.0-dev.1.zip`: SHA-256 `6a3e83cc4ceaadbc5d189c94b2a41be6a3c2bbfee71ada267d255267010f04c8` (14820141 bytes).

The WordPress plugin is byte-identical to the previous candidate. Actual WordPress Plugin_Upgrader fresh installation, activation and same-version overwrite passed, including browser checks and retention of settings, cron, configuration, requests and external reports through deactivate/reactivate. This is not a schema migration.

The development kit was extracted into a new directory and every file matched its manifest. Its own code passed 21 unit tests and generated corporate-site extraction checks, then created a three-page preview with one valid normalized image after the source containers were removed. Eight offline Chromium checks passed, including actual image decoding, original fragment-target position, missing/unsupported notices and mobile layout. Previously extracted material remained byte-identical and was usable by the new kit. Neither extraction nor preview is installed as a WordPress admin operation.

Keep private materials outside versioned code directories. Upgrade the CLI kit by extracting to a new directory, checking hashes and explicitly selecting that version. Existing output is not overwritten. Human review of company/contact information and unsupported features remains necessary. This test does not certify arbitrary themes or uninfected content.

Environment, test infrastructure and product limits are separate in the [result](../../evidence-public/portable-final-zip.json). The first packaging candidate remains preserved; final-v2 only corrects stale Japanese documentation before acceptance. The report and result were written after the ZIP freeze and are not retroactively included in the ZIP. Existing broader prototype functionality is included but was not fully re-certified by these scoped tests.
