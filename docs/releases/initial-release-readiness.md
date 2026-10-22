# Initial experimental edition readiness

> **Observation closed by operator decision:** 68h 28m 24s, three daily slots completed, two historical gaps retained. This is not a 72-hour pass. See [final assessment](shortened-observation-final.md).

October 22, 2026, after PR #8 (`71e54a7`). This is an experimental development edition, not production acceptance or a formal release. See the [initial edition summary](initial-experimental-edition.md), [current status](current-status.md) and [verified artifacts](recurring-trust-final-zip.md).

| Work item | Initial edition assessment |
|---|---|
| Scope and evidence inventory | Documented, with product/environment/test infrastructure distinctions and evidence reuse limits |
| Installation, scheduling and stopping | Dedicated procedures and state retention tested; full automatic production deployment is not provided |
| Capture through recovery | Generated-data dedicated profiles and real experimental S3 verified; restricted SSH capture remains a known integration gap |
| Operational observation | Three daily slots completed; observation closed after 68h28m24s by operator decision. Two gaps retained; no 72-hour pass or continuous coverage claim |
| Distribution | PR #8 merged; CI passed; verified frozen final-v2 ZIPs selected unchanged, with updated companion documentation |

The 72-hour duration is a project-selected observation target, not an identified external standard. The shortened observation is closed, without added stored sets. Final assessment, power restoration and follow-up pause are complete; gaps remain. Later changes do not inherit its coverage.

[Operator sequence](../guides/first-site-operator-runbook.md) / [Deployment planning](../guides/external-deployment-plan.md) / [Pilot acceptance](../guides/production-pilot-acceptance.md) / [Trust operations](../guides/trust-recurring-operations.md).
