# Same-host verification: priority 1 setup checks

> Update: this single-container profile is diagnostic. The existing restore worker uses the [shared two-container contract](same-host-runtime.md).

[日本語](same-host-verification-jp.md)

Implemented scope: read-only configuration and local Docker admission checks. **Not a restore launcher, installer or approval.** Existing signed approval, expiry and current-registry rules are unchanged. The result is eligible_for_dedicated_trial, never production-ready or restore-verified.

## Supported minimum

Linux with Python 3, /proc/meminfo and a local Docker engine at /var/run/docker.sock, invoked through /usr/bin/docker. No remote Docker contexts. The inspector needs daemon access, which is powerful: do not grant it to WordPress/PHP or mount the socket inside the test container. The host administrator and Docker engine are trusted. This cannot establish independence against host compromise.

Use the [configuration example](../../examples/same-host-verification/config.example.json). Place the JSON outside the public web directory. It contains references/limits, not DB passwords or signing keys. Replace both ID placeholders and declare all production file/DB paths. Missing paths, symlink components and workspace overlap in either direction are rejected. The existing deployment preflight's bounded, duplicate-rejecting JSON reader and capture digest are reused.

The workspace must already exist with mode 0700 and belong to the inspection user. No directories, containers, permissions or files are created by the checker. Preparation remains an administrator action in this priority; a general installer/UI is deferred.

The exact stopped disposable container must have:
- Numeric user 65534:65534; read-only root; all capabilities dropped; no-new-privileges only.
- NetworkMode none AND actual network membership only none; no published ports/links/DNS overrides.
- No mounts, binds, volumes, volumes-from, devices or Docker socket. No shared host PID/IPC/UTS/user namespace; private cgroup namespace.
- No restart policy or health check; memory, total memory+swap, CPU and process limits matching the configuration.
- Only /tmp and /work tmpfs, each with the exact options rw,nosuid,nodev,noexec,size=BYTES,mode=1777. Combined tmpfs budgets must be below container memory.

This strict initial profile does not support images declaring data volumes or a running database service. It establishes a disposable sandbox contract; the later restore runner must provision an appropriate runtime inside that boundary. Current approval-required recovery is not connected or bypassed.

## Operator command

    python3 tools/same-host-preflight.py --config /private/same-host.json

Exit 0: eligible for dedicated trial; exit 2: blocked. JSON includes issue codes, config hash, same_host placement, independent_verification=false, restore_started=false and approval_changed=false. Main groups: invalid config/input; unavailable inspection; path/permission problems; disk/memory headroom; network/mount/root/namespace/resource violations. Fix the configuration, not the reported result.

required_workspace_bytes is an operator-provided bound for staging; it must be based on expanded artifacts, not merely compressed size. Disk free space must cover it plus reserve_disk_bytes. MemAvailable must cover container memory plus reserve_memory_bytes. Example values are illustration, not universal site sizing. Current availability is a snapshot, not a reservation. Capacity races, disk quotas for later staging, concurrent-worker limits and execution-time bounds must be enforced by the future runner and rechecked immediately before execution. Docker CPU/memory/pid settings limit this container, not total host workload.

Docker admission is read-only but not an atomic launch authorization. Config/runtime may change after inspect. Do not cache a pass as permission to start; the future runner must bind the exact IDs/config hash and revalidate before running.

## Dedicated evidence

13 unit tests pass, including a matrix of unsafe settings. The generated-data real-Docker lab passes 10 cases: unchanged stopped-container CLI inspection; actual non-root execution, root-write denial, loopback-only interfaces and tmpfs write; production-fixture and Docker-socket mounts rejected; added external network rejected; unbounded memory rejected; root rejected; injected low available memory rejected; requested disk requirement above actual free space rejected; production fixture unchanged. Created containers are removed even after assertions fail.

Run tests:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_same_host_preflight.py -v
    PYTHONDONTWRITEBYTECODE=1 python3 tools/run-same-host-preflight-lab.py

The second command explicitly creates and starts only its own disposable generated-data container. Ubuntu 24.04 must already be available; no pull, S3 access, credentials, production access or WordPress restore occurs. Invalid containers are inspected while stopped and never started.

Initial real-Docker testing exposed a **product checker defect**: NetworkMode=none alone missed additional network membership. The checker now requires actual membership exactly {none}; a unit regression and the real-container case pass. This was not an environmental timeout. No separate environment blocker was observed. Memory shortage was injected, not created by exhausting the host; no stress, mail delivery, payment or end-to-end WordPress test is claimed. Historical observation is closed and untouched.

See [evidence](../../evidence-public/same-host-preflight.json) and [initial specification](../spec/selectable-recovery-spec.md). No release ZIP, production rollout or new approval behavior is part of this change.
Regression: existing deployment preflight 21 tests and recurring capture review 16 tests passed. Current recovery trust 28 tests were skipped because they require the dedicated root-owned registry lab; these are not passes. No existing approval module was modified.
