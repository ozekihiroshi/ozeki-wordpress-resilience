# Reconstruction definition and logical-state contract v1

Status: proposed specification, 2026-10-22. [日本語](rbr-reconstruction-definition-v1-jp.md). Implements no code and claims no experiment. Refines [Immutable Assets, Deterministic Reconstruction](immutable-assets-deterministic-reconstruction.md) against the actual minimal A format described in [storage implementation](rbr-generation-minimum.md).

## 1. Closed reconstruction definition D

D binds one existing A to independently immutable R and E. Do not edit the old generation manifest to attach rules later. Store a new definition artifact; an alternative R or E produces another definition for the same A.

| Field | Required content |
|---|---|
| schema | `owr-rbr-definition-v1` |
| site_id | Same independent identity as A |
| assets_ref | A manifest fixed Version ID, key, bucket, byte count and SHA-256; no latest alias |
| rules_ref | Exact immutable R artifact reference and digest |
| environment_ref | Exact immutable E artifact reference and digest |
| comparison_ref | Versioned comparison/extraction contract C and implementation/build digest when available |
| required_scope | Exactly company/services/contact roles, included images and declared business expectations; no silent subset |
| expected_ref | Independently prepared expected logical-state artifact Q with immutable reference and digest |

Every reference uses the existing fixed-locator/size/hash discipline. SHA-256 of the exact saved UTF-8 D bytes is `definition_digest`; exclude any self-hash field. Transport/path copies retain their byte hash; substituting a different storage reference creates a different D even if logical content is identical. Asset/revision/hash identity still explains semantic equivalence across retention copies; do not confuse that with bit-identical definition identity.

Rules, environment packages, comparison tools and Q must remain available for the lifetime of a retained definition. Apply reference-aware protection to this entire closure, not only A's page/image files. Optional human-readable labels/timestamps are descriptive and cannot resolve dependencies. No secrets, credentials or executable hooks in declarative D/R/Profile.

For execution, artifact availability and compatibility are binary checks. No unknown fields or versions are ignored; no fallback to installed defaults/latest packages. A specification may name a required artifact slot without supplying actual versions/hashes yet, but then D is **unbound/not executable**. This turn does not select or build executable packages and does not invent digest values.

The adapter must validate A from bytes, including unique identities, exactly three page roles, unique nonempty slugs, image identities and all referenced relations. Current storage validation alone is insufficient for this stricter reconstruction contract. An existing A that fails it is reported unchanged; a corrected A must be a new generation. Missing data is not guessed.

## 2. Fixed R: `corporate-pages-text-v1`

R is declarative, interpreted only by an allowlisted engine. Initial semantics:

- Three ordinary WP pages, role order company -> services -> contact; company is the designated landing role. Preserve each source title and slug exactly; reject slug collisions instead of adding suffixes.
- Page body is an ordered array of plain-text paragraphs. Treat text as text, escaping at output; do not execute HTML, shortcodes or auto-embeds. No Markdown conversion in v1.
- Relationships `image` and `link` use `position` as a **paragraph boundary**, 0 before paragraph 0 and N after the final paragraph when there are N paragraphs. Require 0 <= position <= N. This gives a defined meaning to existing data without claiming inline character/anchor preservation.
- At a shared boundary, image entries precede link entries; within a type, targets sort by stable asset ID. Duplicate `(from,type,position,to)` edges are rejected. Input edge-array order is not an implicit priority.
- Each internal link label is the exact target title; its target is a stable page ID resolved on the new site. No fragments/query/external URLs exist in this minimal edge contract. Content needing those features is unsupported, not silently downgraded.
- `navigation` edges form a per-source-page related-pages list after the body, ordered by position; duplicate positions for one source are rejected. This is separate from the global three-role navigation. There is no page hierarchy in the current A schema, so all three pages have no parent.
- Global navigation uses company/services/contact in role order with source titles as labels. No additional navigation page is synthesized. The pinned clean theme must implement this contract; it cannot discover arbitrary old menus.
- JPEG/PNG original byte hashes, dimensions and media types are preserved. Register one attachment per included image asset; use the original for required content. Optional regenerated thumbnails are not the reference original and must not silently replace it.
- Existing A has no alt/caption fields. Initial R accepts an explicit per-image declaration that the image is decorative, uses empty alt and no caption, and reports that limitation. It cannot apply this to informative images automatically. Informative-image text is an unmet requirement until a new asset schema/revision carries it. This declaration is a one-time binding decision, not a new daily approval.
- The content-only preview uses draft pages, authenticated preview access and no automatic public activation. The intended post-review public status of the three pages is declared in R separately from this actual draft state. Form processing, payments, account migration and external services are excluded. Required contact information must be present as explicit text; do not infer or correct it.

Unsupported content, undeclared required function or a non-decorative image without necessary description blocks planning. Permitted omissions are fixed before execution and appear in the report. Required business information cannot be omitted through a warning.

## 3. Fixed E and explicit deployment bindings B

E must pin WordPress, one clean theme, the reconstruction engine F, allowed plugin list (initially only this engine's required plugin), PHP and extensions, database family/version/charset/collation, locale/timezone, URL/permalink policy, image handler and initialization recipe. Include exact package hashes and retrieval references; an archived package or equivalent verified availability is needed for disaster use. A container image digest may represent the runtime closure but a permanent host is not required.

Initialization creates an empty site with an explicitly identified local operator account, removes or disables stock sample content, and never imports the old DB/options/users/configuration. The account is operational, not a migrated business user. Its numeric ID and credentials are bindings; its required capabilities and exclusion from public content are rules. Require empty reconstruction scope; do not destroy pre-existing business content to make a target fit.

B contains destination origin/base path, filesystem root, DB connection/namespace, operator numeric ID, fresh secrets and run_id. Store only redacted connection/secret references in evidence. Dates used by WP internally are excluded only when operational; no business dates are silently synthesized. Architecture/locale/media-handler choices affecting output belong in E, not B.

Execution phases: retrieve and hash-check the entire pinned closure -> close external access -> initialize target -> apply plan -> observe -> compare -> await publication decision. During apply/observe, deny outbound mail/API/payment and scheduler execution at runtime/network and application layers. Required test HTTP access is limited to the target; no external analytics/fonts/assets. Record blocked attempts as well as actual sends: any unexpected attempt fails the no-side-effect condition. This is required future behaviour, not proven existing capability.

Time-limited environments can be created only when needed and removed after evidence is saved. Same-server isolation is allowed if it satisfies the declared containment contract; always-on second EC2 is not a prerequisite.

## 4. Pure plan P and execution receipt

`P = plan(A,R,E)` contains stable asset-ID operations only: verify inputs, register images, create three page shells, populate bodies/relations, configure declared navigation/landing role and verify scope. Stable order is image asset ID then role order; real DB IDs are resolved only by the executor. Plan generation has no hidden old-server access, clock-dependent content, randomness or network lookups. Record a plan hash under the versioned serialization below.

The executor records an injective asset-ID -> target object-ID map, hashes of actual stored originals, applied definition/plan identity and operation outcomes. Two assets cannot map to one target object; one asset cannot acquire two live objects on retry. Resume uses the same D/P and reconciles the target; changing input midway is a new run, not a retry.

Executor receipts are evidence of what was attempted, not the comparison oracle. The logical-state extractor must read the actual target DB and served preview/asset bytes and verify recorded mappings. Do not produce an apparent pass by copying P or Q to an output report.

## 5. Logical observation and comparison C

C builds a normalized observation with:

- Pages keyed by stable asset ID: role, title, slug, ordered paragraph strings, parent=null, actual status=draft, intended activation status from R, rendered content sequence and image/link entries at declared boundaries.
- Images keyed by asset ID: revision, original hash/bytes/type/dimensions, actual served original hash, declared decorative/alt/caption contract and attachment mapping validity.
- Global role navigation and per-page related navigation: label, order and resolved target asset IDs. Landing role must resolve to the company page in the preview entry, without publishing it.
- Coverage: exactly three required pages, exactly included image assets, zero unresolved relations, no unexpected reconstructed content or enabled extra plugins. Explicit initialization-only objects may be allowlisted by E, not silently ignored.
- Behaviour: authenticated operator can view all required pages and images; following each internal link reaches its expected asset; unauthenticated public access does not expose draft business content; external/scheduled side-effect attempts and deliveries are zero.

Extract plain text from the designated content nodes and compare Unicode strings exactly after HTML entity decoding and consistent CRLF -> LF conversion. Preserve paragraph order, spaces, punctuation and meaningful line breaks. Do not trim, lowercase, collapse whitespace, remove HTML-derived missing text or normalize Unicode variants to conceal discrepancies. The rendering contract must prevent CSS whitespace collapse from hiding meaningful whitespace, or reject input it cannot preserve. Comparing DB text alone does not prove the served content matches.

Map internal DB IDs through the verified injective map. Resolve target URLs through actual routing/response identity to stable IDs. Do not indiscriminately strip hosts, queries or fragments. Only known target origins/base paths and operational preview authentication tokens are bindings; their presence and validity are tested before exclusion. External or unresolved destinations fail.

Raw operational IDs, generated filesystem paths, salts and operational timestamps may differ; retain redacted/raw observations separately where safe. Source media bytes must match exactly. Optional thumbnail byte identity and theme chrome pixel identity are not required in v1; content image source/dimensions, text/relations and declared behaviour remain mandatory. Do not count visual differences outside scope as tested equal.

Canonical comparison serialization: JSON UTF-8; object keys sorted by code-point order, arrays preserve semantic order; strings decoded then serialized with LF policy above; booleans/null and integer counts only, no floats/duplicate keys; fixed escaping convention from a versioned serializer. Hash the serialized observation, but report field-level differences too. A serializer/comparator change changes C and the acceptance identity. Do not assume current PHP key sorting is a universal cross-language canonicalization standard.

## 6. Expected result Q and one bounded acceptance experiment

Q is prepared/reviewed independently from the synthetic source, before running F. It declares exact strings, roles, paragraph order, original image hash/dimensions, edge positions/labels, global/related navigation, preview status and required behaviours. Do not generate Q by reusing the planner, renderer or extractor under test. A future tool may assist authoring, but a reviewed independent fixture is required for this first experiment.

Suggested fixture: company title “Example Company”, services “Services”, contact “Contact”; explicit company description, service statement, contact text “Email: contact@example.invalid” and “Telephone: TEST-0001”; one generated decorative PNG with its actual byte hash frozen when the fixture is created. These are proposed synthetic values, not changes to the existing fixture or production data. Q must contain exact finished values/hashes before the experiment, not placeholders.

Accept only when `C(W1) = C(W2) = Q`, and both runs satisfy containment/coverage checks. Use two independently initialized environments and the same D/A/R/E/C/Q; deliberately vary target origin/base path and numeric ID allocation through permitted E-defined initialization bindings. No second run may reuse the first run's rebuilt DB, outputs or caches. Disable access to old WordPress and retain evidence that no unlisted source was read.

Minimum negative controls for the future comparator: change one contact character, drop an image, swap a link destination and reorder a paragraph: each must fail. Change only legitimate numeric IDs/origin: it must pass after routing/map validation. These are bounded checks of the comparator, not a new long-duration observation project. No tests executed this turn.

Comparison mismatch, missing evidence or unavailable fixed dependency is a failure/blocked result, never “probably equivalent”. Emit definition/plan/comparator hashes, environment verification, redacted bindings, raw and normalized observations, expected-state reference, omission report, side-effect observations and structured differences. A pass authorizes no automatic public release and does not claim absence of malware.

## 7. Compatibility and implementation boundary

Existing A remains immutable. Introduce D/R/E/C/Q alongside it; do not overwrite old Profile or commit manifest, or reinterpret legacy signed Restore approvals. The current Profile is only role assignment. Existing S3 schema/storage tests continue as storage evidence; they do not satisfy this contract.

New work after specification: descriptor/closure validator, stricter A-to-R eligibility checker, pure planner, bounded fresh-WP executor, actual-state extractor and comparator. Exact runtime/theme/engine artifacts are not yet bound; no runnable D or reconstruction pass exists. The existing fixture's lack of real contact values or image semantics must be addressed explicitly when preparing the new synthetic fixture. Backup for S3 and production are unchanged.

Implementation follow-up: [minimum validator/planner](rbr-planner-minimum.md), planning only; WP execution and comparison remain unimplemented.
