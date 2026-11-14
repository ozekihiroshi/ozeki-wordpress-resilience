Prepared-software recovery contract / 復旧先の準備済みソフトウェア契約

Run only on a disposable Docker test host, never inside a live WordPress site.
python3 run.py creates three isolated WordPress sites with a private internal
Docker network and dedicated database/volumes. No ports or AWS credentials are
provided. It removes only its own containers, volumes and network in finally.
Synthetic accounts and content are not production data. Mail is suppressed.

Stage approved local archives alongside this script:
  wp.phar, candidate.zip (unchanged submitted package with dependencies),
  wordpress-7.1.4.tar.gz, wp-members.zip, contact-form-7.zip, flamingo.zip,
  tablepress.zip, advanced-custom-fields.zip, ozeki-markdown-documents.zip.
Build product-src.tar from the source under review, containing src/ and tests/.
The source overlay is applied BEFORE test setup, never by recovery.
Required existing Docker images: mariadb:11.8, wordpress:php8.3-apache.

The administrator-equivalent fixture installs/activates software separately.
After setup WP-Members initialization is instrumented to throw if called.
Recovery must not change installed plugin files or active_plugins and must not
newly include an install.php/uninstall.php file. Prepared WP-Members runtime
settings and destination schema versions are compared, not regenerated.

Checks: missing preparation refuses before destination content changes;
member login, anonymous restriction, profile editing, field choices/deletion;
Markdown HTTP display; ACF definition/value reads; CF7 form rendering;
Flamingo effective receipt fields and resave; TablePress rendering and resave;
first recovery and second generation recovery, including confirmed history.
Object hashes must stay unchanged during each recovery.

Storage is a local file-backed AWS SDK handler, NOT real S3. WordPress and the
plugins are real software; UI coverage is limited to the requests stated above.
This is not an exhaustive all-version, all-field or public-release acceptance test.
Logs/results remain next to the runner. Failed attempts must not be relabeled PASS.

既定では実S3を使用しません。復旧先に事前導入したソフトウェアを使う境界と、
代表データの利用・再保存・再復旧を検証します。本番への導入・公開は別判断です。

Optional real-S3 mode (authorized experimental EC2 host only):
  OWR_LIVE_S3=1 /path/to/isolated-boto3-venv/bin/python run.py
live.py uses the existing host role against a new random prefix in the existing
experimental bucket. Containers remain on an internal network with dummy SDK
credentials; a file IPC handler forwards only scoped reads and create-only puts.
No delete or software-install operation is forwarded. All versions in the test
prefix are compared before and after recovery; existing prefixes are not queried
or mutated. Test originals are retained after completion. The identity/bucket
constants in live.py are specific to the authorized test infrastructure.
