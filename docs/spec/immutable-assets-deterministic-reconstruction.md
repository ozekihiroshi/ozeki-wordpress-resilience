# Immutable Assets, Deterministic Reconstruction

Design principle adopted 2026-10-22. [日本語](immutable-assets-deterministic-reconstruction-jp.md).

> Ozeki WordPress Resilience regenerates the business-relevant logical state of a WordPress site from independently stored immutable information assets, version-fixed reconstruction rules and an explicit execution-environment definition. The original WordPress database and server are not required reconstruction inputs. Repeatable logical results from identical declared inputs are an acceptance requirement.

This is the target architecture, not a claim that the current prototype already reconstructs WordPress. Normal S3-first originals remain normal by the agreed registration premise. No malware-free detection prerequisite is added. No always-on second EC2 is required.

## Function and effect boundary

W = F(A, R, E), with logical equivalence evaluated by a versioned comparator C.

- A: an immutable selected site-generation manifest and all referenced originals and relations. Stable asset identities, exact storage references, hashes and required business roles form a closed dependency set. Formats may include Markdown in future; current storage input is typed JSON/plain text and JPEG/PNG. PDF and Markdown support are not implied by this principle.
- R: immutable rules including conversion, ID mapping, link rewriting, required information, supported alternatives, omission policy and normalization/comparison version. Pin rule content hashes, not just a mutable version label.
- E: WordPress, theme, allowed plugins, reconstruction engine/build F, PHP/extensions, database/schema/charset/collation and relevant locale/timezone/configuration definitions. Pin executable artifact digests as well as versions and record where exact artifacts can be obtained. No silent latest-version substitution if an artifact is unavailable.
- W: the business-relevant site state, compared through stable asset IDs, content, media and declared behaviours. It is not the exact SQL dump, database IDs or every byte of the runtime.

Keep a pure planning boundary P = plan(A,R,E): it must not read the old DB, wall clock, ambient network, host files or mutable latest configuration. The effectful executor applies P to a newly prepared target. Therefore the whole running WordPress installation is not literally a pure function; determinism is an explicit contract on its logical output. Record F/build and comparator identities so hidden implementation changes cannot masquerade as identical inputs.

Deployment bindings B (destination URL, local paths, newly issued secrets, generated operational timestamps) are supplied explicitly to the executor and recorded separately. They must not change protected business semantics. If a binding changes content/behaviour, it belongs in R/E and changes the input identity; it cannot be dismissed as an environment difference. Secrets never belong in public manifests. External-service credentials are unnecessary while reconstruction side effects are blocked.

## Four disciplines

1. Append revisions; never overwrite accepted originals. A retention copy may change the locator but preserves logical asset/revision/content identity and provenance.
2. Version rules, supported alternatives and comparison logic. Rule changes create a distinct reconstruction identity.
3. Pin the engine and environment dependency closure. Version pinning does not authorize indefinitely deploying vulnerable software: an upgrade creates a new E, a new identity and a reviewed/tested reconstruction result.
4. Isolate reconstruction from email, external APIs, payments and scheduled jobs. Enforce at the runtime/network boundary as well as application configuration; do not rely on WP-Cron disablement alone. Acquire pinned packages in a separate preparation phase, then execute against the declared local inputs. Enable selected external functions only after explicit publication/activation decisions.

The WordPress database is a mutable projection for everyday operation. Protected editor changes must become new immutable S3 input revisions before accepted projection changes. This does not eliminate the database or claim protection for unsupported write paths.

## Logical equality contract for the first three pages

| Compared exactly or semantically as declared | Normalization allowed |
|---|---|
| Required company/services/contact roles and their stable asset mapping | Database numeric IDs map to asset IDs; map must be complete and unambiguous |
| Page titles, plain-text paragraphs, order, published/draft state and required contact values | Operational creation timestamps may be excluded; business publication dates must be preserved or supplied explicitly |
| Image asset identity, source-byte hashes, placement, captions/alt text where supported | New storage paths/attachment IDs map to the same asset; required derivative dimensions/appearance remain checks |
| Link/anchor targets, relation types, navigation order and resolved destination | Replace only the declared destination origin/path prefix; do not strip arbitrary URLs, paths, queries or fragments |
| Declared required functions and absence of prohibited side effects | No normalization of broken links, omitted pages or failed required behaviours |

The comparison contract is approved before looking at test differences. Do not broaden normalization merely to make a failing pair pass. Record the original observation and the normalized representation. For the current minimal storage format only paragraphs and typed relations are supported; broader rendering equality is future scope.

## New core acceptance experiment (planned, not executed)

1. Freeze a small synthetic A/R/E and an independent expected business-state fixture. Hash all inputs and declare omissions/required functions in advance.
2. Make the old WordPress and its DB/files unavailable. Prepare two empty target environments independently; neither may use results/caches from the other.
3. Execute reconstruction twice with identical A/R/E. Vary only permitted deployment bindings deliberately (different target URL and DB IDs) to test correct remapping.
4. Extract actual states W1/W2. Check C(W1) = C(W2) **and** both equal the independent expected business state. Two equally wrong outputs must fail.
5. Verify complete ID mapping, required page/media coverage, resolved links, prohibited email/API/payment/Cron effects, and absence of old-source access. Unexpected omissions or undeclared inputs fail.
6. Retain input/build/comparator hashes, environment and binding records (without secrets), outputs/diffs and omissions. Publication remains separate; this is not a production deployment or a malware proof.

The repetition serves this precise contract, not a new multi-day soak period. Existing S3 collision/retry/retention tests remain prerequisite storage tests; they are not replaced or counted as reconstruction determinism evidence. Future failure-resume tests verify the same planned state, not a second source extraction.

## Mapping to current implementation and next boundary

| Area | Current status |
|---|---|
| Immutable A originals and fixed version/hash references | Minimum PHP storage coordinator implemented, offline tests only; real AWS/IAM still unverified |
| Site generation and relationship packaging | Minimal typed three-page package implemented; not all WP content formats |
| R artifact/version and rule closure | Design only; current Profile assigns page roles and is not a complete R |
| E/engine lock and retrievable executable closure | Design only; existing lab images do not constitute a general reusable E contract |
| Pure plan builder and fresh WP executor | Not implemented |
| Logical-state extractor, comparator and two-target experiment | Not implemented/not run |
| Guarded editor save / WP projection update | Not implemented |
| Side-effect controls | Prior isolated-lab mechanisms are candidates for reuse; no complete new executor integration proven |

Next design/implementation unit: a closed reconstruction descriptor binding the existing A generation to immutable R and E artifacts, plus an explicit logical comparison contract. Then build one bounded plan/executor for the three pages and an image, and perform the above single-purpose two-target experiment. Do not extend notification/monitoring infrastructure to satisfy this principle.

Backup for S3 remains an independent backup/restore product. Legacy recovery evidence and approvals retain their scope; no code transfer or automatic reinterpretation is authorized by this document.

Concrete follow-up: [reconstruction definition and logical-state contract v1](rbr-reconstruction-definition-v1.md), design only.
