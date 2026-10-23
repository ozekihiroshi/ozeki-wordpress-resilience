# Request-derived Q and generation binding (prototype)

For new explicit three-page enrollments, Q is generated from the validated save request and frozen alongside that request before generation storage begins. Page titles/slugs/plain paragraphs come from the request; image digests/dimensions and page relations come from verified enrollment originals. No reconstructed DB, rendered page or successful test result supplies Q. Q describes the private draft reconstruction; the source site's published status is not copied.

The job includes `expected_sha256` over canonical Q. The existing coordinator includes this in its immutable intent; the committed manifest's `intent_sha256` binds that exact intent. After generation confirmation, the save API writes a create-only fixed-version `owr-rbr-bound-expected-v1` sidecar with the exact generation reference, immutable intent and Q. It uses reserved `originals/request-expectation/<operation>/source`; that asset identity cannot be enrolled. The sidecar must cover the generation retention horizon. Only then does normal WordPress projection proceed. Q storage failure leaves public content unchanged and the operation unresolved. Retrying the same operation uses its frozen Q, same generation and idempotent fixed sidecar; a changed request cannot reuse it. No approval is issued or extended.

The applied receipt adds `expected_ref`. Supply that complete receipt to `rbr-generation-kit.py` with this profile (all references are fixed references):

```json
{"schema":"owr-rbr-request-profile-v1","site_id":"corporate-test","rules_ref":{},"environment_ref":{},"comparison_ref":{}}
```

Replace the three empty reference placeholders with the selected pinned R/E/C references. Do not provide `expected_ref` or `required_scope` in this profile. The builder verifies the sidecar/generation/intent/Q hashes, request-page identities, enrolled image identity, original relations and retention. It obtains Q and required scope from the frozen sidecar, not from reconstruction output. It stores the exact Q and emits a v2 kit containing `expected_binding_ref`, still in `stored_awaiting_independent_approval`.

The v2 root requires the binding. Updated fetch and received-kit verification recheck it against D.assets_ref, D.expected_ref and scope before executing the plan. Old fetch tools reject the v2 schema instead of ignoring its new contract. Signature, key pin, independent current registry, revocation, expiry and before-execution checks are unchanged. A correctly generated Q means the expected content matches the request; it is not authorization to reconstruct or publish. Existing v1/manual-Q kits remain supported under their original contract.

## Validation and limits

[Evidence](../../evidence-public/rbr-request-q.json): 32 real WordPress HTTP/MariaDB checks with the existing filesystem S3 protocol double, including Q-write failure after generation commit, public-content preservation and same-generation/Q resume. A real PHP planner consumed the actual fifth-generation receipt without manual Q, produced P and an approval-pending v2 kit. 75 Python regression cases include eight PHP-generator assertions. Modified Q, wrong generation, mismatched intent, manual-Q override, missing v2 binding and short binding retention are rejected.

This increment does not repeat real AWS storage or the previous two-target reconstruction trial. Fixed images/relations, three existing root pages and plain text remain the scope. Entirely blank business text or a relation outside the edited paragraphs is rejected. There is no generalized Gutenberg, new-media or Markdown authoring. Legacy enrolled/pending journals without frozen expected-state context are not silently migrated, regenerated from their DB or reset; retain their code/state and plan migration separately. Old completed operations can still replay their original receipt. Production rollout and automatic publication remain absent.

Static review found and fixed a potential intent/Q key collision before the dedicated runtime test. An initial dependency-copy preparation was intentionally stopped before creating containers; the partial folder was preserved. These are separate from environmental failures; none newly occurred in the final trial.

## Request-derived Q through real S3 (2026-10-23)

The follow-up [live evidence](../../evidence-public/rbr-request-q-live.json) connects actual protected-editor saves to experimental S3 and the signed reconstruction inlet. Three generations and 21 browser checks passed, including pre-commit failure, public-content preservation, conflicting/stale editor rejection and post-commit interruption with same-generation resume. The actual applied receipt supplies `expected_ref`; no manual Q is supplied. Before reconstruction, the fixed binding, intent hash and Q hash were checked. The real PHP planner produced nine steps and a v2 kit stopped at independent approval pending.

A separate root-only test signing account approved the kit under the existing signature, pin, current-registry, revocation and expiry contract. Both source and builder workspaces were hidden from the actual recovery process in a private mount namespace. Fixed S3 versions supplied Q and the reconstruction inputs; two fresh isolated WordPress targets matched that exact Q and each other. A deliberately wrong Q was rejected. Selected assets and the Q binding cover the generation retention horizon; the parent remains provenance and is not fetched. No source parent was deleted or expired.

75 RBR regression tests passed. Dedicated runtime and firewall rules were cleaned up; the existing nine containers were unchanged. No production change, automatic publication, approval extension or new product-code change was needed. Separate signer identity on one host and cached OCI images do not establish physical independence or a cold-cache recovery. General authoring and legacy enrollment migration remain outside scope.

Test-infrastructure note: an auxiliary hash check initially used ASCII-escaped JSON for Japanese content, unlike the product's UTF-8 canonical representation. Correcting the helper to the existing product rule made the check pass; no stored data, product validation or approval was changed. The initial sandbox WSL access denial was resolved by the authorized execution path, without changing WSL configuration.
