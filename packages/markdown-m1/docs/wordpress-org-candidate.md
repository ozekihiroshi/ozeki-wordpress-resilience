# WordPress.org candidate 0.3.2 (rc.1)

This candidate adds setup readiness, explicit storage-access confirmation and Japanese/English administration screens to the previously submitted 0.3.1 product. It is prepared for updating the existing application and has not been sent. The submitted 0.3.1 rc.2 ZIP and tag remain unchanged.

Public name: **Ozeki Resilience**. Directory: `ozeki-resilience`. Version: **0.3.2**. Contributor: **ozekihiroshi**. Existing option and history keys are retained. No external runtime kit is required.

## Build

The product source is exclusively `packages/markdown-m1/`. Install the locked Composer dependencies (`composer install --no-dev --prefer-dist --optimize-autoloader`), then from the repository root:

```sh
python3 packages/markdown-m1/tools/build.py packages/markdown-m1/vendor dist/ozeki-resilience-0.3.2.zip
```

Use a new output filename. This candidate preserves the submitted rc.2 vendor bytes, without dependency upgrades. The published manifest records every product-file hash. The ZIP includes AWS SDK dependencies and licenses, not repository research tools.

## Candidate checks

See the repository's `docs/releases/wordpress-org-032-candidate.md` and release assets for the exact ZIP hash, official Plugin Check results and isolated installation/update checks. Existing recovery evidence remains in [recovery readiness](recovery-readiness.md); it is not represented as a new cloud trial.

## Review notes

AWS credentials use the standard SDK credential chain and a user-controlled S3 bucket. Read `readme.txt` for service/data disclosures and [the guide](user-guide.md) for setup. Recovery can restore selected theme/plugin files from the administrator's trusted capture; this is a user-initiated recovery workflow, not a developer-hosted update channel.

Historical research assets and previous releases remain available but are not additional setup requirements.
