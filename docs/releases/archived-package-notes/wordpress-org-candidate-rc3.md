# Historical rc.3 preparation note / 過去のrc.3準備記録

Not current installation guidance. [Current distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md). Original text preserved below.

# WordPress.org candidate 0.3.3 (rc.3)

This candidate adds ACF free basic-field preservation and recovery to 0.3.2. **0.3.3 rc.3 is prepared but not submitted.** The existing WordPress.org application has requested changes to 0.3.2 rc.1, accepted on October 28, 2026. No version is yet approved or published in the Plugin Directory. Earlier submitted ZIPs and tags remain unchanged.

Public name: **Ozeki Resilience**. Directory: `ozeki-resilience`. Version: **0.3.3**. Contributor: **ozekihiroshi**. Existing option and history keys are retained. No external runtime kit is required.

## Build

The product source is exclusively `packages/markdown-m1/`. Install the locked Composer dependencies (`composer install --no-dev --prefer-dist --optimize-autoloader`), then from the repository root:

```sh
python3 packages/markdown-m1/tools/build.py packages/markdown-m1/vendor dist/ozeki-resilience-0.3.3.zip
```

Use a new output filename. This review-response candidate updates AWS SDK to 3.401.5 and its locked dependencies. Earlier submitted ZIPs remain unchanged. The published manifest records every product-file hash. The ZIP includes AWS SDK dependencies and licenses, not repository research tools.

## Candidate checks

See the repository's `docs/releases/wordpress-org-review-20261028.md` and release assets for the exact ZIP hash, official Plugin Check results and isolated installation/update checks. Existing recovery evidence remains in [recovery readiness](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/02ec4e8/packages/markdown-m1/docs/recovery-readiness.md); it is not represented as a new cloud trial.

## Review notes

AWS credentials use the standard SDK credential chain and a user-controlled S3 bucket. Read `readme.txt` for service/data disclosures and [the guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/02ec4e8/packages/markdown-m1/docs/user-guide.md) for setup. Recovery can restore selected theme/plugin files from the administrator's trusted capture; this is a user-initiated recovery workflow, not a developer-hosted update channel.

Historical research assets and previous releases remain available but are not additional setup requirements.

The previous submitted 0.3.2 rc.1 source is `54663f9f8376ec9c90d67fa573997dbbce8421e4`; its ZIP and tag are unchanged. See the [0.3.3 preparation record](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-review-20261028.md). The ACF integration scope and prior evidence are described in [ACF free](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/02ec4e8/packages/markdown-m1/docs/acf-free.md).

PHP classes use `OzekiResilience\M1`; existing stored identifiers and hooks remain compatible. Recovery-policy and legacy-identifier questions are recorded in the repository review response. This is not a claim that all review findings have been cleared.
