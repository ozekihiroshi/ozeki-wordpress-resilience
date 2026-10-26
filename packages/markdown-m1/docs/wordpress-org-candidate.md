# WordPress.org candidate 0.3.1

The submission candidate is based on main commit `b2968c7fd0fa45bc77a0f82dbfda8c1cbc6628f1`. The earlier 0.2.0 submission candidate was based on the wrong product generation and is superseded. Its source/tag/artifacts remain historical; they are not this submission's evidence or runtime dependencies.

Public name: **Ozeki Resilience**. Directory: `ozeki-resilience`. Version: **0.3.1**. Contributor: **ozekihiroshi**. Main PHP filename and existing option/queue keys remain unchanged.

## Build

From the repository root, install the dependencies locked in `packages/markdown-m1/composer.lock` into that package using Composer (`composer install --no-dev --prefer-dist --optimize-autoloader`). Then run:

```sh
python3 packages/markdown-m1/tools/build.py packages/markdown-m1/vendor dist/ozeki-resilience-0.3.1.zip
```

Use a new output filename. The WordPress.org build contains this package and its vendor libraries, not the legacy root plugin or Python/SSH tools. AWS SDK libraries and dependency licenses are included. This candidate reuses byte-identical vendor files from the checked-in recovery-readiness ZIP; no dependency upgrade is included.

## Evidence boundaries

Existing behavior evidence is recorded in [recovery readiness](recovery-readiness.md), [optional Markdown verification](optional-markdown-verification.md), [Checkpoint verification](site-checkpoint-verification.md), and the linked per-feature records. These describe their frozen builds. Historical research goals and unperformed long-term trials are not new submission requirements.

The submission preparation checks are limited to packaging, PHP syntax, Plugin Check, affected output, activation and preservation when changing plugin directory. Their final results and exact ZIP hash are recorded in the repository's `docs/releases/wordpress-org-submission.md` and release assets. They do not imply new AWS end-to-end acceptance or every plugin/version combination.

## Review notes

The current code uses the AWS SDK credential chain and a user-controlled S3 bucket. There is no external worker kit. Read `readme.txt` for data/service disclosures and the user guide for setup. Recovery can restore selected theme/plugin files from the administrator's own captured backup, alongside content. It is a user-initiated backup/recovery workflow, not a developer-hosted code-update channel. Restored code is not guaranteed malware-free.

The repository root contains retained historical implementation and research tools. The current product source is exclusively `packages/markdown-m1/`. Existing pre.1/pre.2 and 0.2.0 release archives are not overwritten.
