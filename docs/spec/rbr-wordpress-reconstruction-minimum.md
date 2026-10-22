# Private WordPress reconstruction from a pinned plan

Prototype development-kit implementation; not a release, editor integration, public site or production deployment entry. This extends [the planner](rbr-planner-minimum.md) for a bounded generated company/services/contact site. It preserves existing approval conditions. No legacy Restore approval is reinterpreted and P still says `execution_authorized: false`; a separate explicit disposable-lab invocation authorizes only the experiment.

## Inputs and runtime binding

The existing S3-first fixture/coordinator supplies immutable A through the local S3 contract double. The same fixed A/R/E/C/Q and P are used for both targets. S3 locator metadata is preserved, but this experiment makes no AWS calls and does not validate live S3 delivery or retention.

E replaces non-executable placeholder WordPress/PHP/database artifacts with bounded local OCI identity descriptors. Docker resolves available images to full immutable image IDs before planning, then launches those IDs, verifies the actual image and internal-only network, and checks the absence of a default route and host port bindings. The local cached image and its layers supply the runtime closure. Human-readable actual runtime versions are recorded separately. This is a local reproducibility proof, **not** proof that an OCI image has been archived to S3 or will remain available on a replacement machine. It is not a recommendation to deploy the tested versions to production.

The dedicated `rbr-lab` theme is saved by exact source bytes as E's theme artifact. F's source bundle binds the planner, storage serializer, WP apply/observe entry points, lab runner and comparator. C independently pins the actual comparator source. Environment setup and the mail/HTTP guard are explicit parts of that runner, not hidden old-server inputs. Both blank targets initialize fresh credentials/configuration, database and uploads; they mount only code and declared cached inputs, never an old WordPress/DB/configuration. Each run has a different origin and post-ID range. There is no always-on second EC2.

## Application and observation

`tools/rbr-wordpress-apply.php` is a dedicated CLI-only entry requiring the disposable target marker and fixed lab paths. It recomputes P from D/closed bytes and rejects a changed P or synthetic-only E before applying. It checks the empty posts scope, records started/applied/failed state, registers original JPEG/PNG bytes, creates draft page shells, writes escaped plain paragraphs, image references and links, and installs the declared landing/global/related navigation. Existing targets and repeat application are refused. An interrupted target must be discarded and rebuilt; resumable reconciliation is **not implemented**. This is intentionally not a general installer for arbitrary WP hosts.

`tools/rbr-wordpress-observe.php` reads actual post rows, metadata, original media bytes, mappings and runtime state. `tools/rbr-compare.py` independently parses the served private theme HTML, checks it against actual DB content, resolves links through the checked target origin and actual ID map, checks page titles/paragraph order/global and related navigation, hashes HTTP-served image bytes, and compares logical content to independently authored Q. Q never generates the operations. Exactly the declared reconstructed pages/images must exist. Anonymous page access is denied; the authenticated landing page resolves to company. Operational IDs/origins are allowed to differ only after these checks.

The target's WordPress HTTP and mail hooks block and count attempts; Cron execution is disabled. The isolated Docker network supplies only the disposable WP and DB, with no external default route or published ports. WordPress installation's notification attempt is blocked and recorded separately from the reconstruction window; it is not claimed to be zero. During apply/observe, the required count is zero. Explicit harness HTTP requests go only to the test target. The lab does not claim that arbitrary hostile PHP can be safely executed, nor measure browser pixels or all possible network system calls.

## Running the bounded experiment

Requires WSL/Linux, Docker with the chosen images already cached, PHP/GD and the existing development dependencies. The tool resolves the cached `wordpress:php8.3-apache` and `mariadb:11.8` tags once to immutable IDs and records them; another run on differently cached tags creates a different E/D. It never pulls images.

```sh
python3 tools/rbr-reconstruct-lab.py --allow-disposable-lab \
  --output /a/new/private/lab-result-directory
```

Output must be new. It retains D/P/Q, fixed object cache, actual DB observations, served HTML/media, normalized logical state, receipts, route evidence and result/failure records. Disposable containers and the internal network are removed in `finally`. No public activation follows success. Review the machine-readable evidence in [rbr-wordpress-reconstruction.json](../../evidence-public/rbr-wordpress-reconstruction.json).

## Acceptance and limits

Two fresh targets must each equal Q and each other. Negative controls modify the actual target: one contact character, paragraph order, link destination, and removal of the image. Each must fail content comparison or the required served-asset check. Duplicate application must be rejected. Existing planner and storage tests remain separate regression evidence.

The initial fixture covers three plain-text pages, one decorative PNG and contiguous related-navigation positions. General block layouts, forms, informative-image descriptions, sparse navigation-position roundtripping, arbitrary plugins/themes, public activation, production authorization, interrupted-run resume and portable OCI archiving are not claimed. The admin plugin ZIP has no new reconstruction UI. Independent security admission/revocation remains separate from logical equivalence: matching Q grants no approval to publish.

## Problems distinguished

- Environment: Docker automatic address pools were exhausted before any WP operation. The runner now selects a non-overlapping dedicated internal /28 instead of altering existing networks.
- Test infrastructure: initial-copy readiness, generated PHP quoting, missing WP_INSTALLING, option string-to-integer observation and the Docker DB_COLLATE configuration path were corrected. Failed runs are not successful reconstruction evidence.
- Implementation: an apply helper initially collided with WordPress's `checked()` function; renamed to `rbr_checked()`. Final acceptance uses the corrected implementation.

English is primary; [Japanese summary](rbr-wordpress-reconstruction-minimum-jp.md).
