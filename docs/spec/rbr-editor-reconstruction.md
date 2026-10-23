# Edited-generation signed reconstruction (prototype)

Follow-up: new enrollments now support [request-derived Q](rbr-request-q.md). The manual Q trial below remains historical evidence.

The editor remains explicitly enabled for company/services/contact. `rbr-generation-kit.py --generation SAVE_RESULT.json --profile PROFILE.json --work NEW_PRIVATE_DIR --execute-generated-lab` now also accepts the actual applied save API response (`state`, `replayed`, `generation`, `sequence`). It preserves the fixed generation reference and checks its manifest sequence. The receipt is an input locator, not an approval. No fixture generator replaces edited page assets.

Q is an explicit expected-state document selected before reconstruction and stored as a fixed S3 object. For this bounded trial, `examples/rbr-editor-expected.json` specifies the intended three edits, retained image digest/dimensions and relationships. It is not copied from the reconstructed DB or generated from observed success. An operator must update/review Q and required business expectations for changed content; generic automatic Q authoring/UI is not supplied. R/E/C stay pinned. A stale Q must fail comparison rather than be rewritten to match output.

A site generation is a full snapshot. Its `parent` is authenticated provenance inside the unchanged generation bytes, not a runtime input. Builder, receiver and received-kit integrity verification use the same dependency rule: skip only `parent` of the exact known generation schema. Every selected asset, rule, runtime and Q still requires fixed bytes and applicable retention. Unknown generation fields fail closed. Other objects with a field named parent retain ordinary traversal. This is not a historical-chain audit and does not extend/delete old retained versions.

The kit builder yields `stored_awaiting_independent_approval`. Existing independent signature, current registry, expiry and before-execution rechecks remain mandatory. A new explicit test approval is needed; existing approvals are never extended. Reconstruction creates two disposable WordPress targets, matches each against Q, and keeps pages draft without public activation.

The dedicated live trial uses three browser-authored generations and the real API's idempotent applied receipt. Source containers are removed before kit reconstruction. The source workspace is hidden in a private mount namespace during recovery; only S3 assets and pinned dependencies supply reconstruction input. The existing local execution-image cache is reused; this is not a new cold-cache/bootstrap or physically separate signer-host claim. No production/IAM/default-retention change.


## Dedicated validation record

See [public evidence](../../evidence-public/rbr-editor-reconstruction.json). The selected generation is the third actual browser edit, obtained from the API's applied receipt. The source WordPress is stopped and its data directory and kit-building workspace are hidden during recovery. Two fresh private targets are compared to the independently specified edited Q; a stale contact expectation is also rejected using the captured DB/HTTP observations.

The initial builder attempt stopped before any kit PUT, approval or WordPress launch: the negative-control test had been made independent of the old fixture's telephone text, while E still pinned the old engine bundle. Only `tools/rbr-reconstruct-lab.py` differed. A new explicitly pinned E and fresh workspace resolved the test-profile mismatch. The failed attempt is preserved. This is a test-infrastructure correction; signature/expiry checks were not relaxed. Existing cached runtime images are reused.

Parent unavailability/expiry is exercised offline; no retained S3 parent is deleted or expired for this trial. Actual retrieval omits the parent while preserving its reference in the signed manifest. Selected assets still satisfy their generation retention horizon. This does not certify historical lineage or cold-cache recovery.
