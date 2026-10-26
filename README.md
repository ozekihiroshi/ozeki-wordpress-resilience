# Ozeki Resilience

**Immutable assets, deterministic WordPress reconstruction.**

English | [日本語](RAADME-jp.md)

Version 0.2.0 is being prepared for WordPress.org submission. This repository
contains the WordPress plugin and its separately operated runtime. Installing the
plugin alone does not enable protection. See [setup](setup.txt) and the
[directory readme](readme.txt) for prerequisites and external-service disclosures.

## What it does

An explicitly enrolled administrator uses the standard block editor to save
supported posts, pages and PNG/JPEG images. The external worker commits immutable
materials and a complete generation to S3 before WordPress applies the change.
Fixed Version IDs, hashes, retention and request-derived expected content bind the
generation. Failed saves retain previous projected content; interrupted requests
can resume using their existing journal. Unknown storage outcomes require operator
reconciliation, not a blind resend.

Reconstruction retrieves the selected generation without the source WordPress DB,
applies it to a configured recovery WordPress and compares its logical result.
**Saved post status is restored, including `publish`.** The operator controls DNS,
TLS, target access and publication approval. On an accessible target, restored
published posts may immediately be public. This release does not automatically
isolate all recovery targets or guarantee zero external effects.

## Supported scope

- Administrator-only explicit enrollment on a dedicated environment; one writer host.
- Core paragraph, heading, list, quote and image blocks with basic links/emphasis.
- PNG/JPEG up to 4 MiB and 10,000 pixels per dimension; no PDF or automatic thumbnails.
- At most 1,000 assets per generation, 6 MiB canonical UTF-8 per asset, 8 MiB per
  stored object and 64 MiB decompressed closure. Conservative manifest admission
  can reject a combination below the individual limits.
- No Classic Editor/Markdown-plugin integration, custom/dynamic blocks, forms,
  taxonomy/custom fields, scheduling, arbitrary third-party write protection,
  internal page-anchor links, distributed writers or automatic existing-site migration.

The current external S3 adapter uses a dedicated SSH signing deployment. It is
not a generic AWS setup wizard. The filesystem adapter is only a test double.
An operator without a compatible signing/runtime environment cannot obtain S3
protection by installing this ZIP. See [setup.txt](setup.txt) for the actual boundary.

## Distribution and updates

`ozeki-resilience-0.2.0.zip` is the installable WordPress plugin.
`owr-development-kit-0.2.0.zip` is the matching external runtime/source kit,
including documentation, tests and retained historical tools; it is not a plugin.
Update both together. Preserve configuration, receipts, bridge files and journals
outside replaceable directories. Upgrades retain settings/history and do not
silently enroll sites or convert legacy three-page data.

The configured WordPress target path is the current recovery workflow. The optional
Docker target and content-snapshot viewer remain available as separate research
paths. They are not required for the configured target workflow.

## Trust and evidence

Integrity and retention protect accepted materials; they do not certify that
arbitrary content is malware-free. Keep storage permissions and journals protected.
The new path's `integrity` policy is separate from the retained independently signed
legacy path; old signatures do not automatically authorize new material schemas.

[Prior native-editor ZIP validation](docs/releases/native-editor-020-zip.md) and
[prior live-S3 evidence](evidence-public/native-editor-live-s3-validation.json)
describe their frozen builds. Their private-target and zero-side-effect findings
do not transfer to the configured target changes in this candidate. Current
[release scope](docs/releases/wordpress-org-preparation.md) supersedes old research
gates. Historical observation is closed and does not certify current-path uptime.

Ozeki Database Backup for S3 is independent: neither plugin requires the other.
That product restores DB/files; Resilience reconstructs supported materials.
[License](LICENSE) · [Contributing](CONTRIBUTING.md)
