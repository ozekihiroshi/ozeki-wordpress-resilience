# Normal registration reconstruction: development status

[日本語](normal-reconstruction-status-20261129.ja.md)

See the subsequent [management, preservation and worker integration record](construction-management-20261129.md). The evidence below describes the earlier integration boundary.

This branch preserves the implementation and evidence accumulated on November 28–29, 2026. It is **not a release, a replacement of the production recovery screen, or a WordPress.org submission**. Existing release ZIPs/tags remain unchanged. This is the current entry point; earlier documents are dated experiment records, not cumulative guarantees.

## Principle and implementation

Preserve the material and the inputs, references and confirmed results needed to build the site again through WordPress and each supported plugin's ordinary registration/settings interfaces. The administrator prepares trusted software. Reconstruction neither installs nor initializes plugins, restores their executable code, assigns original database IDs, nor repairs internal state to imitate an expected result.

The initial save is necessary: it records the formal state already present, plus author identities and explicit source-time reference contracts. After that boundary, automatically captured operations are followed in recorded order. Source IDs identify dependencies; destination IDs, image URLs and CF7 hashes come from actual normal registrations. The follower does not discover missing references by reparsing destination content. Unknown or incomplete contracts and uncertain outcomes remain held.

The development observer records input before a handled operation and confirmation after the normal handler succeeds. Account credentials and nonces are not archived as reusable credentials; the form participants are recorded and fresh nonces are obtained normally. Member passwords are not restored; standard password reset was exercised.

`ConstructionInitialReferences`, `ConstructionContract`/`ConstructionPluginContract`, `ConstructionEmbeds`/`ConstructionBlocks`, `ConstructionFollow`, and `reconstruct-kit.py` form the current integrated path. `ConstructionTransfer` connects the initial save and operation stream through a versioned commit. Its tests use a local object-store substitute, not AWS.

The earlier `NativeReconstruction` and individual plugin plans are retained as development stages. `construction-record.py` and early integrated fixtures include explicitly authored recipes; their successes are **not evidence of automatic capture**. Use the later combined and third-site records below for that claim. The old production recovery engine has not been replaced on this branch.

## Evidence and scope

| Area | Ordinary path and evidence | Limit |
|---|---|---|
| WordPress content | Normal registration, actual new IDs, relationships, rendering/edit/save; source-time block references | Known contracts only; arbitrary blocks, complex menus and all lifecycle operations are not covered |
| Markdown Documents | Existing import and editor; original/thumbnail references; embedding and later edits | No plugin change; internal draft/revision replay is not the product target |
| TablePress | Existing JSON import and editor; later edits and new-ID embeds | Not every extension/option combination |
| CF7 / Flamingo | Normal form registration; public hash reference; captured CF7→Flamingo arguments passed to normal add(), without resubmitting the form | Original input must exist; subsequent receipt status/metadata changes require their own contracts |
| WP-Members | Normal page selection, field/settings/member forms; password reset, login and guest/member visibility | Passwords and privileged account rights are not imported; author/member overlaps and all field types are not exhaustively covered |
| ACF free | Normal definition import and field editor, retained values and later use | ACF Pro excluded; only supported field/reference rules |
| Images | Source-time size URLs and IDs, normal upload/edit/replacement/delete, typed block attributes | Standard tested REST routes; classic image-editor AJAX and third-party in-place replacement are not covered |

- [Latest third-site check](construction-roundtrip-20261129.md) and [machine-readable results](construction-roundtrip-20261129-results.json): A→B from an initial save plus 21 operations; B→C from B's own initial save plus four normal edits. C rendered, allowed ordinary resave, and passed additional member/ACF/form/image/receipt checks. Main warm test 105.716 seconds; B→C phase 43.224 seconds. Extra C-use checks are outside that main timer.
- [Combined check](construction-combined-20261129.md): baseline objects and later plugin/embedding/image operations in one sequence, about 57 seconds. Superseded for initial content references by the third-site change.
- [Image operation check](construction-media-contracts-20261129.md), [reference check](construction-reference-contracts-20261128.md), [plugin contract check](construction-plugin-contracts-20261128.md): focused earlier evidence.
- [Receipt input preservation](flamingo-input-preservation-20261128.md): input capture, successful registration, formal-history confirmation, interruption/retry and old-data treatment.

The third-site test exposed a real gap: daily block references were recorded, but capturing that reconstructed state as a new baseline did not preserve the equivalent contract. This was fixed at capture by adding baseline content contracts and using the same reference substitution code. No target-side inference or database repair was added. Quote-block support was retained explicitly when unifying the contracts. Future-dated fixture content and a negative test that injected no HTML were test problems, not product fixes; both are recorded in the detailed report.

## Compatibility and active code boundaries

The construction stream/anchor remain development experiment v5. Initial reference sidecar schema 2 adds content contracts to media references. Schema 1 media can be read, but absent content contracts cause a hold rather than inference. Existing saved objects are never rewritten.

There are also changes on the **normal preservation path**: `FormHistory` boots `ReceiptInputs`; `CommentHistory` supports stable receipt operation IDs and confirmation; `SiteSnapshot` carries/replays receipt input records and exposes normal-registration plan methods. Thus this branch must not be described as documentation-only or entirely dormant. These changes are not deployed. The new receipt history kind and snapshot format deliberately prevent unsupported older readers from treating new material as fully understood. See the receipt report for exact formats and unresolved-input behavior.

## Remaining work before release

1. Decide and document the supported operation/field matrix and how users resolve held or uncertain records. There is no completed general resolution UI.
2. Connect the isolated observer/coordinator to the real management-screen and preservation lifecycle. Production recovery still uses its existing engine; ordinary source capture is not yet complete for every UI/API route.
3. Preserve the same source-time contract for additional supported operations; no target-only fallback. Unknown blocks, references, non-admin edits, concurrency, interruption and restart of the entire coordinator are not broadly proven by this fixture.
4. Assess privacy, retention and storage growth of captured inputs, authorization and safe application at the final entry points, and transport failure behavior. The capture allowlist is not by itself a universal security guarantee. Keep prepared settings and report unapplied data.
5. Perform release packaging/Plugin Check, install/update and final end-to-end checks on the eventual exact ZIP only after scope and integration are ready. None of those release claims follow from these source-level tests.

The second-stage `outage_no_commit: false` in the raw results counts inherited A commits; it is not proof of a new commit during the simulated outage. No second-stage outage guarantee is claimed from that metric. The narrow test must use a before/after commit set when revisited.

Actions run offline contracts and existing regression/build checks; they do not recreate the dm WordPress sites or prove browser-JavaScript behavior. The host-bound integration drivers require cached official dependencies, a dedicated Docker daemon and the documented local helper layout. They are evidence/reproduction tools, not a user-facing installer.

No production site, existing originals/history, ZIP or tag is changed by this push. No merge to main, release, WordPress.org upload or review-email reply is included.
