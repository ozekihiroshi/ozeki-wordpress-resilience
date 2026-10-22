# RBR 05 — Staged minimum plan (not started)

Status: Stage 0 design and static code assessment, 2026-10-22. Baseline: main `f5ebf8ca74a50e469741b67f36d6dfa4e9200b6e` (PR #10 merged); working tree was clean before this assessment. No implementation, live inspection, test execution, deployment or changed approval policy. English primary; [Japanese overview](rbr-overview-jp.md).

## Sequence

1. Approve the contract: normal-original premise, protected-save boundary, stable IDs, Profile/generation fields, required pages, incident holds and retention of referenced originals. Output is a bounded specification, not new infrastructure.
2. Implement one vertical slice later: three corporate pages and PNG/JPEG originals -> S3-first generation -> fresh manually prepared WP -> pages/media/links -> verification report. Reuse image/text/loss rules. One fixed clean theme, no extra functional plugins, no old users/options/SQL restore. No full controller, extra EC2 or notification rollout.
3. Integrate operator screens and resumable operation: normal-save status, Profile setup, recovery access, generation selection, plan, progress, missing-item disposition and manual publication decision.
4. Add safe operation policy: freeze/quarantine, hold lookup, version conflicts, uncertain outcomes and retention review; these must be complete before claiming incident-ready operation. Optional background/controller work follows actual demand.

Implementation priorities by dependency: N2 and N3 -> N1 -> N4 and N5 -> N7; design N6 upfront and complete before incident product acceptance. A vertical slice alone is not the incident-ready release.

## Proposed finite acceptance boundary

Use only generated company/services/contact content, one valid image, one broken reference and one unsupported form. Close the source after saving. New WP must obtain Profile/assets through independent recovery access, create new IDs and reconstruct required information. Record which required items pass, fail or use explicitly accepted substitutes. No public launch in the PoC.

Future fault cases should target new boundaries only: S3 save failure prevents protected WP completion; S3 success/WP failure resumes without duplicate originals/pages; incomplete generation is not selectable as complete; new IDs preserve relationships; old source unavailable; declared holds block selection; retained original remains usable after source modification. Do not repeat SSH/systemd/VM reboot or broad Restore trials as RBR proof.

Completion is business information present with exceptions explained, not identical layout or IDs. PDF, video, builders, menus from arbitrary themes, commerce, membership, global plugin settings and unsynchronized update routes are outside the first slice. Required unsupported functionality prevents a ready-to-publish result until an explicit alternative is chosen.

Effort is relative, not a quotation: storage/identity contract = medium; pre-save integration/reconciliation = high; new WP importer/resume = high; simple report/UI = medium; broad editor/hosting support = high and outside first slice. No reliable calendar or financial estimate exists before hook coverage and host constraints are resolved. Existing preview does not eliminate these tasks.

Sources: [portable extraction](../../tools/portable-content.py), [preview](../../tools/portable-preview.py), [ZIP evidence](../../evidence-public/portable-final-zip.json). Unknown: supported edit entry points, storage authentication, minimum hosting capabilities; resolve before promising time/cost. No PoC or test executed in Stage 0.
