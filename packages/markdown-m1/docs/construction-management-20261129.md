# Construction recording and management integration — 2026-11-29

[日本語](construction-management-20261129.ja.md)

Development-only, not a release. Production, preserved originals/history, ZIPs,
tags, WordPress.org submission and review email are unchanged.

## Implementation stages 1–5

| Stage | Implemented | Boundary |
|---|---|---|
| 1. Scope / acceptance | Source-time contract remains authoritative; recognized endpoints and fields have an independent application check. A complete record is not permission to execute arbitrary instructions. | The observer supports the existing enumerated administrator REST/forms. Other observed formal changes produce a preservation-gap indication, not invented input. |
| 2. Durable recording | New local option namespace stores each immutable input and completion separately. Interrupted head writes, missing/tampered records, unresolved outcomes and competing writers are rejected. First gap survives later requests. | Existing experiment-v5 options are not migrated. Wire schemas and stored originals are unchanged. One operation remains limited to 8 MiB; reads still assemble the journal, so large-history acceptance is outstanding. |
| 3. Management / preservation | Isolated tools page creates the baseline through SiteSnapshot, appends through ConstructionTransfer and acknowledges only after read-back. Storage identity and confirmed prefix are checked. Protection-enabled saves schedule one event-driven transfer. | No periodic backup, retention or deletion was enabled. Protection-off and recovery-role sites schedule no transfer. Failed delivery stays pending. |
| 4. Normal-registration job | Destination management queues an immutable selection; a prepared local worker claims it and uses the existing normal-form/API coordinator. Results come from actual registration, not a supplied map. | Worker requires Python and WP-CLI outside the web process. The UI does not launch a shell. Registration is reported as pending usage checks. An uncertain claim cannot be restarted automatically. This is not yet a standalone WordPress-only recovery UI. |
| 5. Shipping guards | CI includes persistence/management, application-boundary and worker static tests alongside prior review guards. The install/initialization scan now includes PHP tools. | Static guards and small fixtures are not a full safety proof. The dedicated real-WordPress management trial is reproducible on dm but is not yet a portable GitHub-hosted integration job. |

## Operational scope

The existing source contracts cover bounded normal WordPress post/page and media
REST operations, Markdown import/post editing, TablePress import/save, CF7 form
save and Flamingo receipt input, WP-Members settings/fields/member forms, and ACF
import/post editing. The exact field/route limits remain in ConstructionContract
and ConstructionPluginContract, not inferred from a plugin being installed.

Unrecorded changes are detected through selected post, metadata, taxonomy,
member and settings notifications. This is **not** a claim that arbitrary SQL,
every third-party hook or every non-administrator editing path is observable.
Non-observed changes still require explicit coverage work. A detected gap blocks
a complete preservation claim and cannot be cleared merely by retrying.

Initial setup before the first baseline is distinct from an interruption after
preservation starts. A capture marker covers changes DURING that first baseline;
after confirmation, the confirmed baseline activates the gap guard. Ordinary
unpublished auto-drafts are not treated as lost formal publications. A prepared
recovery destination is not a protected source; a new baseline is required for
its later source use.

## Activation and execution

Both `OWR_CONSTRUCTION_ISOLATED` and `OWR_CONSTRUCTION_PERSISTENT` must be explicitly
true. Existing installations do not activate this path. The old recovery engine
has not been removed or automatically replaced. The tools page requires
`manage_options`; every mutation checks a WordPress nonce. It provides English
or Japanese state labels using the current user's locale.

The source needs its separately authorized storage configuration. The destination
uses recovery-role read access and a confirmed commit reference. No software is
installed, activated or initialized by reconstruction. The local worker prompts
for the prepared destination operator's password, binds HTTP identity to the
queued operator, and invokes only normal registration plus the bounded local
bridge. No credentials are stored in the journal or shell command line.

The optional local runner is an administrator-supplied argv file for an already
prepared container. It is never supplied by the archived material. Worker
evidence is mode 0700/0600 and outside the WordPress root; uncertain evidence is
retained for review rather than automatically deleted. Interrupted jobs require
explicit investigation; a reset/reconciliation UI has not been provided.

## Confirmation evidence

- `tests/construction-management.php`: real Store with a memory transport;
  baseline/daily confirmation, outage without boundary advancement, idempotent
  retry, original-object preservation, destination change refusal, sticky gap,
  single-event scheduling, protection-off/recovery refusal and language labels.
- `tests/construction-persistence.php`: immutable input/result, no silent legacy
  conversion, missing/orphan/tampered records, lock ownership and gap retention.
- `tests/construction-safety.php`: preserve raw structured/Markdown values;
  hold unsafe CF7 HTML/settings, arbitrary archived REST entry points and
  privilege-transfer requests. Its HTML stub is not a substitute for WordPress.
- `tests/construction-shipping.py`: no shell/installer use in the normal worker,
  admin checks remain present, normal scalar table data unchanged, and existing
  review guards remain wired into Actions.
- `tests/construction-management/run.py`: dedicated internal Docker network,
  synthetic WordPress sites, file-backed substitute for S3 transport. Actual
  authenticated management requests create a baseline, record two normal page
  saves, confirm their history, queue a destination job, run normal registration,
  view/edit the result and refuse a second job execution. Invalid nonce and
  Japanese management rendering are checked. No ports or production mounts.

The first management integration passed in 36.235 seconds; the subsequent run
including invalid nonce and Japanese rendering passed in 37.915 seconds. The
[final run](construction-management-20261129-results.json) passed in 40.086 seconds.
These are narrow
integration timings, not production performance promises.

Development corrections: the CLI bridge initially loaded a second physical copy
of a class already loaded by the fixture; it now respects the loaded class.
An unrecorded taxonomy event for an auto-draft initially prevented the baseline;
the observer now distinguishes formal content and the initial-capture boundary.
No destination values or stored originals were patched to make either test pass.

## Remaining acceptance work

1. Repeat the full supported-plugin scenario through this management/job path;
   earlier all-plugin round trips used the preceding isolated entry points.
2. Verify adverse concurrent requests, process termination, gap resolution and
   transfer retry using real WordPress processes, not only option-store fixtures.
3. Confirm safe rendering and later editing on the new path for the past review
   examples. Existing old-path tests alone do not establish their resolution here.
4. Decide the operator/deployment requirement for the external worker before a
   user-facing release; do not present it as a WordPress-only one-click solution.
5. Establish a fresh-data transition procedure, large-history limits and private
   evidence retention policy before enabling the feature outside isolation.

Thus all five stages have implementation touchpoints and a connected narrow
example, but **public-release acceptance and universal operation coverage are not
complete**. No claim is made that the architecture change automatically resolves
every past WordPress.org review concern.
