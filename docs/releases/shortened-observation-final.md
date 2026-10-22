# Shortened observation: final assessment

English | [日本語](shortened-observation-final-jp.md)

On October 22, 2026 the operator explicitly shortened the original 72-hour plan and requested initial-edition assembly. The original plan and audit records remain unchanged. This is **68h 28m 24s of elapsed observation**, not a 72-hour pass.

- Start: October 19 15:55:56 JST. End: October 22 12:24:21 JST.
- Three daily slots: storage, test approval, fixed-version isolated recovery and audits completed (see [three-day evidence](../../evidence-public/initial-release-three-days.json)). No extra saves, signatures or restores were performed to close the trial.
- Final snapshot: 127 samples, three approved sets, 89,527,925 stored bytes, zero uncertain PUTs, 15 preserved trust files, 0 open trial incidents and 0 undelivered trial notifications. Notifications were local trial deliveries, not a production alert-service availability test.
- Coverage: two gaps longer than two hours remain (4h26m33s and 4h24m8s). Periodic successful samples do not establish continuous health between samples. Do not subtract gaps and label the remainder continuous uptime.
- Final capacity/continuity checks found no current problem. Historical failures and missing observations remain; later success does not erase them. Later implementations do not inherit this trial's observation duration.
- Power settings restored and verified: battery sleep after three minutes, AC sleep disabled, retaining the user's AC preference. The original minimum time remains in the power record; explicit authorized shortening allowed restoration.

## Decision

The three daily scenarios and final preservation checks support assembling the experimental initial edition. Continuous coverage is **not established**, the original 72-hour target is **not completed**, and production readiness is **not established**. The duration was project-selected; no cited external standard was identified in the reviewed planning records. Further tests should be justified by changed boundaries and explicit fault/expiry/scheduling claims, rather than a universal duration requirement.

Environment: historical observation gaps remain. Test infrastructure: known corrected defects and the unresolved historical browser startup issue remain separately documented. Product: restricted remote SSH capture and collector-loss release remain an unverified integration boundary; no new implementation is included. See [initial edition](initial-experimental-edition.md) and [machine-readable final record](../../evidence-public/initial-release-shortened-observation.json).
