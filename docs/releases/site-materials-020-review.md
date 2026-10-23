# 0.2.0 cumulative review

## Decision

Draft PR for review; **not ready for release**. Preserve the frozen candidate ZIPs and their successful bounded lifecycle evidence. No merge, tag, release, production change or automatic publication is included.

## Architecture and scope

The English README is primary, with RAADME-jp.md aligned to it. Accepted originals are saved to S3 before WordPress projection; a complete immutable generation and request-derived expectation support reconstruction without the source database. This is independent of Backup for S3. The new integrity policy does not require individual human approval for each edit; the retained signed three-page path has unchanged approval conditions.

Supported: multiple posts/pages, hierarchy, explicit portable text/link/image nodes, PNG/JPEG, fixed versions, retained copies, same-request resume and stale-operation rejection. Dedicated opt-in and private drafts remain mandatory. General Gutenberg/HTML/Markdown, automatic existing-site migration, multiple writer hosts, cold runtime bootstrap and production activation are not implemented. Retained kit-preparation UI is a compatibility path, not a prerequisite of the new architecture. Historical code/evidence is inventoried rather than silently deleted or claimed transferred.

## Release-blocking product finding: asymmetric material bounds

A single page with 320 paragraph nodes containing 20,000 ASCII characters each is accepted by normalize/save. Its canonical asset is 6,410,015 bytes. With the existing in-memory test store, save performs two writes and commits head.json, but receive rejects it with `Compressed object bounds` (6 MiB per-asset ceiling). This reproduces without AWS or WordPress and is a product contract defect, not a WSL or browser failure.

Do not treat the README's 64 MiB generation limit as an end-to-end supported text limit. The generation manifest also embeds Q and is subject to the 8 MiB stored-object ceiling; admission must account for that bound before any writes. Required follow-up: unify save/receive bounds, preflight canonical assets and manifest size before journal/head or remote writes, test boundary and multibyte inputs, then rebuild and revalidate the operator ZIP. Failed/unknown writes must still retain their journals; no blind replay or deletion is authorized. This review does not silently change the frozen runtime or claim a fix.

## Evidence and artifacts

- Frozen plugin: `54e0a5996138564d7c66c4919dda862667d901fe898ac6ff000b7390df79937c`.
- Frozen operator kit: `071b02af966b40b81a2c72efb9d1bcb7518270bcc3571cf4975f49d595bf36c4`.
- Prior real-S3 editor trial: 23 browser checks, 17 acknowledged PUTs, seven assets reconstructed after source removal. See site-materials-editor-validation.json.
- ZIP lifecycle: fresh, alpha.4 and alpha.5 upgrades each passed 24 browser checks; pending save resume, settings/history preservation, previous runtime state preservation and seven-asset reconstruction were tested with a persistent S3 double. No new cloud replay in this review.

The ZIP lifecycle result and this review were added after archive freeze. README review notices added for this PR are documentation-only differences from the frozen ZIPs; they do not imply that the ZIP was rebuilt with a product fix.

## Separate issue categories

- Product: size-contract defect above; listed supported-scope and deployment limitations.
- Test infrastructure: root-owned WordPress updater directories caused an earlier HTTP update failure; corrected dedicated fixture ownership passed with the same plugin hash. Builder version lookup was corrected before the final archives.
- Environment: historical read-only WSL timeout has no established root cause or plugin fix. It does not invalidate successful bounded evidence, nor establish coverage of the size boundary.

## CI fixture correction

Initial GitHub CI failed five distribution tests: fixtures still placed the version in PLUGIN[0] and assumed no assets directory. Corrected fixtures to name the main plugin explicitly and allow the already-created directory; the version-mismatch test now also targets the main plugin. This is a test-only correction, with no change to the frozen plugin/worker. Final CI status is recorded in the PR.

