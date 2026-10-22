# Minimum reconstruction-definition validator and planner

2026-10-22, experimental development-kit component. [日本語](rbr-planner-minimum-jp.md). Implements the planning boundary of [definition contract v1](rbr-reconstruction-definition-v1.md). No WordPress insertion, environment provisioning, AWS access or publication is performed.

## Implemented boundary

`src/RbrReconstructionPlanner.php` accepts D and a reader for declared fixed references. The offline CLI only supplies objects from an explicit content-addressed local cache. It checks versioned locators, length/SHA-256, supported schemas/fields and dependency availability for A/R/E/C/Q and E's package artifacts. It reuses the existing `RbrGenerationCoordinator::encode` serializer under the explicitly named `owr-json-v1` wire contract. Duplicate JSON keys, alternate/noncanonical encodings, floats and unsupported object keys are rejected rather than interpreted ambiguously.

Selected A is checked independently of the prior storage success: three unique roles, unique slugs and identities, matching Profile, exact image references, required business text and valid relations. Paragraph-boundary positions, duplicate edges/navigation positions and image declarations are checked. Unsupported formats and missing informative-image descriptions stop planning. Inputs are never rewritten.

The rules produce nine instructions for the one-image fixture:

1. Register the image by stable asset identity and fixed source bytes.
2. Create three draft page shells, in company/services/contact order.
3. Populate each of the three pages with plain-text paragraphs, image/link boundary entries and related navigation.
4. Configure the authenticated company-page preview entry and global navigation.
5. Verify required scope with publication/external side effects disabled.

These are instructions in JSON, **not executed operations**. No destination URL, numeric WP ID, clock or random value is used to decide their contents. Plan output binds D/A/R/E/C/Q, the loaded planner bundle hash and its comparison/serializer contract. It always returns `execution_authorized: false` and explicitly marks runtime compatibility and logical-site output as unverified.

The actual loaded planning source bundle (`RbrReconstructionPlanner.php` plus its serializer dependency) must match E's engine artifact hash. `tools/rbr-planner-build.php` identifies that source outside the planning call. This is a local build binding under the assumption that the installed code remains unchanged during a run, not code signing or an independent trust root.

## Deliberately separate validation from a reconstruction pass

E package bytes are read and verified, not executed, unpacked or certified compatible. The fixture pins non-executable synthetic artifacts for WordPress/theme/PHP/DB and comparator; the planning engine bundle is actual source. Its mode is `synthetic-plan-only`. These are real fixed test bytes, not real installable WordPress packages. A `pinned-runtime` descriptor also does not receive execution authorization from this planner.

Q is independently authored fixture data. Its structure and scope are checked and its exact artifact is bound, but it does not generate the page instructions. A well-formed incorrect expected title does not alter P's page operations; a later actual-state comparison must detect that error. This run does not assert `C(W1) = C(W2) = Q`: no W was created and no comparator was executed. It establishes byte-identical **P** from identical inputs and rejects invalid input contracts.

A's parent chain, creation/retention observations and copy provenance remain provenance rather than implicit content inputs. The selected full A snapshot provides content without replaying older generations. Retention, independent incident holds, publisher permission and remote locator existence are not verified by the offline cache reader and remain separate recovery admission requirements.

## Run the isolated synthetic example

Composer dependencies, PHP 8.1+ and GD are needed to generate the fixture through the existing storage component. The planner CLI itself does not initialize the AWS SDK or WordPress.

```sh
php tools/rbr-create-plan-fixture.php --output=/private/new-plan-fixture
php tools/rbr-plan.php --definition=/private/new-plan-fixture/definition.json --objects=/private/new-plan-fixture/cache --output=/private/plan-one.json
php tools/rbr-plan.php --definition=/private/new-plan-fixture/definition.json --objects=/private/new-plan-fixture/cache --output=/private/plan-two.json
php tests/test-rbr-planner.php
```

Use fresh output paths. Objects are stored as `<sha256>.blob`; the CLI rejects missing/symlinked objects, changed bytes and existing output files. Each resolved input is bounded to 8 MiB, JSON to 2 MiB, declared closure to 64 MiB, A to 16 assets and relation lists to 1000 entries. This is a prototype limit. The fixture script creates synthetic storage receipts via the existing local atomic S3 double; none are AWS storage evidence.

The definition/rules/environment/expected fixture shapes are explicit in `tests/support/RbrPlannerFixture.php`. The generator writes `SYNTHETIC-ONLY.txt`. It must not be presented as a ready-to-run disaster recovery kit.

## Evidence

[Final evidence](../../evidence-public/rbr-planner-minimum.json) records 20 passing checks, source hashes and two separate CLI process results. Fourteen PHP/distribution test invocations passed, including the existing generation and fixed-version transfer suites. A dedicated retained fixture also produced the same plan digest twice: `a60b49faa162752950c086cb3b9f414421cc17938f2412a58c1af5f9c96b6f56` (specific to that generated definition).

Checks cover declared source independence after original input-file removal, unchanged input bytes, ambient-cache ordering irrelevance, missing/corrupt references, null versions, unknown schema/fields, duplicate JSON keys, latest package selection rejection, wrong loaded engine, duplicate role/slug, unresolved/out-of-range/duplicate relations, undeclared image meaning, missing required contact, comparison/expected dependency coverage and CLI overwrite refusal. See the exact test names in evidence for the assertions actually run; no future runtime checks are counted here.

No new unresolved failures occurred in final checks. Test-infrastructure limitation: local reader and non-executable E artifacts establish contract handling, not live S3/IAM or runtime compatibility. Product gaps: fresh WordPress executor, actual-state extractor/comparator, side-effect containment integration, guarded editor/apply and independent incident admission remain unimplemented. There is no production change, new EC2, ZIP release, commit or push in this step.

Implementation follow-up: [private WordPress execution and comparison](rbr-wordpress-reconstruction-minimum.md).
