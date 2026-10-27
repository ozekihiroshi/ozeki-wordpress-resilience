# Pre-setup checks — current implementation review

[日本語](setup-preflight-review-ja.md) · [Setup guide](user-guide.md)

October 28, 2026. Source reviewed: 2cf014c (0.3.1 series). Based on reading code and existing documentation; no feature changes or execution tests. This is an assessment, not an approved feature specification or delivery commitment.

## Current state

Conditions are checked during configuration, initial capture, ordinary saving, recovery and other operations. There is no unified pre-setup checklist that reports all conditions and guides users to enable protection after passing. Saving settings and successfully saving or recovering content are separate checks.

| Item | Existing check and when it runs | Work needed for a pre-setup check |
|---|---|---|
| WordPress/PHP versions | Plugin header declares minimums 6.4/8.1. Recovery compares the recorded WordPress release line and patch | Show installed and required versions; distinguish WordPress minimum-version checks from a product readiness result |
| PHP extensions and capacity | Capture/recovery use ZipArchive. WordPress/PHP handle ZIP uploads | Report extension availability and upload/POST limits first. Separate observable limits from web-server, time and capacity checks requiring administrator input |
| Database | Protected-operation lock checks InnoDB for posts/postmeta/options. Recovery checks target tables; member recovery checks membership tables | List required table engines before protection starts, sharing existing checks without destructive operations |
| Writable paths | Recovery creates private staging outside the web root and checks writability and installation paths | Report staging, uploads and relevant theme paths first. Limit any necessary write probe to dedicated test files |
| Storage input | Configuration validates bucket/region/prefix/owner formats. Empty owner is currently accepted | Field-specific guidance and missing-owner notice; distinguish valid input from working connectivity |
| AWS credentials and permissions in web PHP | SDK authenticates actual listing/write/read requests; failures appear as errors. Supplied owner is included in AWS requests | Role-specific checks in the same web runtime; report connectivity, listing, writing and fixed-version reading separately |
| Versioning and saved content | Store::put requires a VersionId in the write response. Initial capture retrieves and checks fixed versions | Separate preliminary checks from checks after a real write. Define dedicated probe resources and their retention under no-delete policies |
| Object Lock and retention | Checked during requested locked writes, retention extension and re-reading. Retention 0 requests no lock | Treat as optional and mark unused features accordingly. Do not alter existing locks as a preflight test |
| Integrations | Capture checks Markdown content and activation, among other dependencies. Form, member and TablePress recovery paths check their conditions | List used integrations and required versions. Explain excluded data without treating every unsupported plugin as a reason to block setup |
| Pending work and destination | Capture and other operations detect pending work. Recovery checks protection off, no pending body history, a different source URL and replacement consent | Select source/destination role first and show the relevant readiness items |
| Scheduling | Normalizes settings and registers/displays scheduled work | Explain execution opportunities and recent execution; a scheduled event alone does not prove it will run |
| Other sites using the prefix | Local DB locks and conditional S3 writes exist; there is no exhaustive detection of other sites | Dedicated-prefix guidance. Automated ownership coordination would need separate design |

## Separate automatic checks from administrator decisions

Trust in the initial state, which changes to adopt after an attack, authority to store data, data handling, public exposure and DNS decisions are not part of an automatic environment pass. Present them as separate administrator confirmations.

## Outline if a setup flow is added later

Proposed sequence: environment → storage settings → actual save/read confirmation → initial capture → protection. Each item would show ready / action needed / unchecked / not used. Action-needed results should identify the responsible role and next step. The recovery-destination path should remain read-only, without write or deletion probes.

Readiness describes conditions at the time checked. Changes to settings or credentials require rechecking, so recording the time and configuration checked is also additional work. Existing runtime checks remain in place.

## Source references

- [Plugin header](../ozeki-wordpress-resilience.php): declared minimum versions.
- [Plugin.php](../src/Plugin.php): action, store, lock, scheduleCheckpoints and UI.
- [Store.php](../src/Store.php): args, put, get, ensureRetention and history.
- [SiteSnapshot.php](../src/SiteSnapshot.php): capture, save and restore.
- [FormHistory.php](../src/FormHistory.php), [MemberHistory.php](../src/MemberHistory.php), [TableHistory.php](../src/TableHistory.php): integration conditions.
