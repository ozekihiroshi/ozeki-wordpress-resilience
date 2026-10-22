# Committed S3 generation to independently approved reconstruction

Historical boundary note: the receipt-only experiment below preceded the real coordinator experiment. The latter is now verified separately in [live coordinator results](rbr-live-coordinator.md); the remaining gap is production editor integration, not the tested CLI coordinator.

Prototype CLI inlet; no production enrollment or automatic publication. This increment consumes a fixed-version generation receipt and an explicit reconstruction profile, without calling the synthetic generation/plan fixture builders.

`tools/rbr-generation-kit.py --generation generation.json --profile profile.json --work NEW-PRIVATE-DIRECTORY --execute-generated-lab`

The generation file is the fixed S3 reference (locator, SHA-256, size) of an `owr-rbr-generation-v1` manifest. The profile has `schema: owr-rbr-definition-profile-v1`, `site_id`, `rules_ref`, `environment_ref`, `comparison_ref`, `expected_ref`, and `required_scope`. It cannot supply a replacement `assets_ref` or P. R/E/C/Q are independently selected fixed S3 references; Q is not inferred from the resulting WordPress.

The inlet reads actual S3 versions and retains D.assets_ref exactly. It validates the source site's manifest, S3 commit time against deadline, and the generation promise `protect_until = deadline + 35 days`. The source generation and its existing reference closure must already be protected through that horizon. An insufficient source fails closed; this inlet does not silently transform the selected generation.

R/E/C/Q dependencies are reused if sufficiently protected. Otherwise their bytes are copied to new immutable versions, with references rebuilt bottom-up. New objects request 36 days plus ten minutes at creation, using the existing experimental request signer. This is a new-object retention header, not PutObjectRetention, a bucket-default change or an extension of a previous version. Every copied version is read back and must cover the generation horizon. The legacy per-object 35-day transfer behaviour remains unchanged. The PHP coordinator retains its legacy 36-day-default mode and now also has an opt-in explicit new-version retention mode; see rbr-live-coordinator.md. The experimental bucket has no default retention rule.

The trusted local planner validates the resulting definition and generates P. Eight existing execution-code files and D are stored, then the root is stored last. The result is `stored_awaiting_independent_approval`. The root receipt enters unchanged `rbr-approved-kit.py`; key pin/current registry/expiry/signature checks remain mandatory. The inlet never creates or extends an approval and never launches WordPress.

A work-directory lock rejects concurrent callers. Exact input binding and the existing PUT journal support a same-input restart: acknowledged identical PUTs are reused; unknown PUTs block resending. Retention is observed anew on a restart. Changing generation/profile requires a new private work directory. Partial files are not a successful result.

## Scope and evidence boundaries

Only the existing experimental bucket, fixed SSH role brokers and generated corporate-site scope are supported. This is not the WordPress save hook or a generic production S3 connector. Runtime store/architecture/bootstrap prerequisites remain. All referenced parent/provenance objects are currently required through the selected horizon too: an older short-protected lineage fails closed; archival-lineage separation is not implemented.

The live inlet test prepares an actual S3 manifest after reading back its generated-data originals. It tests the committed-generation receipt boundary, not the PHP generation coordinator's actual-AWS concurrency/IAM behaviour. The latter remains a separate unverified boundary; offline coordinator fault/race results are not re-labelled live evidence.

Environment, harness defects and product gaps must remain distinct. No new 72-hour claim, production change, real-site approval renewal or public activation is included.

## Dedicated result

PASS: actual fixed S3 generation preserved in fetched D; the new root entered the existing independent approval gate, and two fresh private WordPress targets matched Q. All fetched kit objects cover the generation promise. The retained-copy publication journal has no unknown PUT. Final commit-time validation reproduced the same root from acknowledged live readback evidence without any PUT and freshly re-read the source generation. See [evidence](../../evidence-public/rbr-generation-kit.json). This proves the receipt-to-reconstruction boundary, not live PHP-coordinator/editor integration.
