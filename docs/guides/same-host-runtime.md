# Shared same-host WordPress/MariaDB runtime contract

English primary | [日本語](same-host-runtime-jp.md)

This change reconciles preparation, inspection and the existing generated-site restore worker. It is not a general-site release, new approval policy, automatic attestation or cloud bootstrapper.

## Contract and integration

same-host-runtime.py owns both create_args and assess. The read-only same-host-preflight.py CLI dispatches format owr-same-host-wordpress-pair-v1 to this contract. The original single-container format remains a standalone diagnostic profile; it is not the WordPress runtime.

first-site-daily-restore.py reuses its existing signature/current-registry/fixed-version checks, SQL import, file restoration, WordPress content checks, result registration interface and ownership cleanup. Only after existing trust checks does it prepare two stopped containers. It resolves image IDs, persists runtime-config.json, checks both containers, starts MariaDB, checks again before SQL import, starts WordPress sharing only that DB's isolated network namespace, and checks again before file extraction. No alternate restore path bypasses approval.

Prepared, db_started and running are explicit states. A state or configuration mismatch blocks advancement. Each assessment is recorded in isolation.json; a rejection is retained with its issues. Startup failure is recognized when a target exits, not merely after the readiness timeout.

Preparation and inspection use the explicit local Docker Unix socket, ignoring inherited remote contexts. The root-owned test authority is redirected ONLY inside the dedicated test harness to a new private /run folder. Production authority paths, signature checks, expiry and revocation rules are untouched.

## Why this differs from the first diagnostic profile

Official MariaDB and Apache/WordPress images initialize as container root, perform ownership changes and then run database/web workloads under service identities. The old universal user-65534/no-write profile could not run those entrypoints. This is an explicit second contract, not accepting arbitrary privileged containers:
- Read-only root filesystem and no host bind mounts, persistent volumes, devices or socket access.
- Capabilities dropped then only CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID and NET_BIND_SERVICE restored; no-new-privileges required.
- DB network none; web shares exactly the prepared DB ID's namespace; no published ports, additional networks, links or DNS overrides.
- Fresh credentials confined to disposable targets. WordPress cron/external HTTP/file modifications disabled by the existing fixture environment; network isolation is the independent egress boundary.
- Per container: 1 GiB memory and equal memory+swap limit, 0.5 CPU, 128 pids, no automatic restart/healthcheck, bounded local Docker logs (1 MiB x 2).
- Bounded noexec/nosuid/nodev tmpfs: DB data and web files 512 MiB each; /tmp and runtime directories 32 MiB; Apache log/lock directories 8 MiB each. /run/mysqld is explicitly prepared for MariaDB.
- Prepared check needs 2 GiB current available host memory and 1 GiB disk headroom. These are small-lab defaults, snapshots, not concurrent resource reservations or universal sizing.
- Host root, daemon compromise, concurrent administrative changes and hostile-code kernel attacks remain outside this guarantee.

No persistent target volume survives normal cleanup. Cleanup uses existing ownership tokens. Abrupt host loss/interrupted recovery still uses existing reviewed cleanup; this change does not claim automatic orphan cleanup.

## Scope still limited

Recovery still accepts the generated site's format, laboratory limits and fixed test-content assertions. The lab explicitly uses production_paths=[] because no production host directory is used and all host/volume mounts are prohibited. General site enrollment must populate and validate the actual source/workspace contract; this does not remove that backlog. The operator CLI inspects a prepared pair without starting it. A general setup UI and universal image support are not included.

The audit's runtime mismatch is addressed for this dedicated profile. Other backbone gaps (configurable acquisition/storage, generic content checks, incident freeze/quarantine, on-demand kit bootstrap) remain.

## Validation on 2026-10-22

[Evidence](../../evidence-public/same-host-runtime.json): 22 preflight/runtime tests, 28 current-trust tests, 10 recovery-worker tests and 11 cleanup tests passed. All 8 generated-site roundtrip cases passed: admission blocks, duplicate prevention, capture, local fixed-version storage, separate test signature/current registry, isolated WordPress restore, result registration and resource cleanup. The capture workspace was unavailable during restore. This is real Docker/WordPress/MariaDB with a local storage substitute, not an AWS roundtrip.

Three failed attempts remain recorded privately: Docker's CAP_ capability spelling, missing /run/mysqld after tmpfs setup, and incompatible local-log max-file=1. These were runtime-contract implementation defects and were corrected; they are not classified as unexplained host-environment failures. Approval rules were unchanged.

The subsequent [real experimental S3 roundtrip](same-host-s3-roundtrip.md) also passed, using this unchanged runtime contract.
