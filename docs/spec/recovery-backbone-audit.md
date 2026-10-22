# Recovery backbone: static code audit

> Follow-up: the runtime mismatch recorded here has been resolved and tested for the dedicated profile using the [shared dedicated two-container contract](../guides/same-host-runtime.md). Other backbone gaps and general-release readiness are not resolved by this change alone.

English primary | [日本語](recovery-backbone-audit-jp.md)

2026-10-22. Read-only source review against the selectable-recovery specification. No commands that capture, sign, access S3, restore or run tests were executed. Existing priority-1 changes remain uncommitted and are not main/released behavior. This is not an exhaustive security audit.

## Finding

There is a connected **experimental backbone**, not just isolated components. It is not yet a supported general maintainer workflow. Source code embeds fixture identities, infrastructure and content expectations. UI work alone cannot finish it.

| Axis | Connected code today | Boundary |
|---|---|---|
| Create usable editions | Coordinator.tick_admitted -> capture_from_files -> publish -> verify_saved -> awaiting_approval -> approve -> Worker.run -> recover -> record_restore | Backend injection and fixture configuration required; no daily capture CLI; generated identities and contents |
| Protect editions | Exact versions, signed documents/pins, role-separated transport, retention observations, current-generation/revocation checks | Transport tied to laboratory bucket/roles/SSH hosts; protection depends on deployed IAM. No integrated site incident freeze/quarantine pipeline |
| Make editions usable at need | Recovery worker, direct recover CLI, isolated Docker restore and result registration/cleanup | Worker needs local daily ledger; direct recover avoids publisher ledger but still needs externally prepared trust inputs/registry and fixture runtime. No complete on-demand kit bootstrapping |

## Source anchors

- [first-site-daily.py](../../tools/first-site-daily.py): publish requires generated-first-site and limits assets to 128 MiB; SITE is isolated-queue-lab. tick_admitted accepts a backend and admission paths, links technical checks through storage. approve verifies signature/pins and versions. CLI exposes status/reconcile/record-restore/approve, **not tick_admitted**.
- [first-site-capture.py](../../tools/first-site-capture.py): capture uses a supplied backend; validate restricts file root, asset size, retention and site profile. CLI validates only. Profile validation is not a general capture deployment.
- [queue-s3-adapter.py](../../tools/queue-s3-adapter.py): laboratory bucket/region, SSH aliases community/dm, AWS roles and owner are fixed. Bucket policy/lifecycle expectations are experiment-specific. Replacing a bucket string alone is not a supported storage configuration.
- [first-site-daily-recovery-worker.py](../../tools/first-site-daily-recovery-worker.py): persists request/outcome/registration; rejects unresolved attempts and unapproved days; depends on the daily ledger and local receipt/approval files.
- [first-site-daily-restore.py](../../tools/first-site-daily-restore.py): direct recover does not read publisher workspace or ledger. It checks the current registry, signature, exact versions, inventory, then restores and records. It still requires generated-first-site, experimental bucket, 128 MiB bound, lab/m1/images.env, fixture DB naming/environment and hard-coded post/media assertions.
- [onboarding-recovery-cases.py](../../tools/onboarding-recovery-cases.py) and [first-site-daily-admission-cases.py](../../tools/first-site-daily-admission-cases.py): test orchestration actually connects acquisition, signing, approval, recovery and registration using injected backend/transport. This is a harness, not a customer entry point.
- [current-recovery-trust.py](../../tools/current-recovery-trust.py): root-owned independent local registry, current version/pins/revocations and at most 24-hour validity. No authority-outage fallback.
- [run-independent-recovery.py](../../tools/run-independent-recovery.py): an additional M1 restoration path exists, but expects named source containers, M1 bundle shape and bootstrap runtime. Do not treat it as a generic unattended kit provisioner.
- [pilot signer](../../tools/pilot/sign-protected-candidate.py): real-site pilot path exists; explicitly site-specific and disabled unless requested. Its signed scope says cross-asset consistency and cleanliness are unverified. Therefore “only synthetic code exists” would also be inaccurate.
- [plugin entry](../../ozeki-wordpress-resilience.php) and [packager](../../tools/build-release.py): WordPress loads administration/report/notification components. Plugin ZIP files do not themselves install the external acquisition/restore chain; the toolkit includes developer/lab assets separately.

## Newly introduced integration mismatch

[same-host-preflight.py](../../tools/same-host-preflight.py) is currently referenced by its lab/tests, not the recovery worker. It requires a stopped single container, numeric nonroot user, readonly root, no volumes, only /tmp and /work tmpfs, exact CPU/memory/pid controls and none networking.

Existing restore_offline creates a MariaDB and a WordPress container with images from lab configuration, uses DB initialization, filesystem extraction/chown, and a shared network namespace. It does not construct the strict preflight profile.

Therefore connecting the new preflight directly would reject existing restoration. This is a **product contract mismatch**, not an environment issue. Decide one working WordPress/MariaDB isolation contract, then make its preparer, checker and runner agree. Do not weaken a check merely to green the old harness, or claim the current preflight proves production restoration.

## Missing backbone and minimal completion order

1. Define one supported operational contract: actual assets/config handling, paired capture, runtime preparation, isolated DB and files, network/credentials and resource ownership. Reconcile the profile mismatch first.
2. Replace fixture-only coordination with a narrowly scoped configurable operator entry. Reuse Coordinator/gates/worker state and refusal logic; provide validated storage/identity and a supported capture backend. No arbitrary adapter coding for users; no silent lower-level bypass.
3. Generalize restore verification from specific test post/media to manifest-derived checks and explicitly configured application checks. Preserve test fixtures for regression, separate from production behavior.
4. Expose the existing chain as inspectable actions with one edition identity and durable status: stored, awaiting approval, approved, restore checked, held/revoked, cleanup pending. A UI is optional for an initial technician CLI, but a complete documented workflow is mandatory.
5. For the full new product promise, implement incident hold/quarantine/freeze ownership and source-independent kit/catalog/bootstrap. Do not claim those guarantees for an earlier limited slice.
6. Redesign automatic attestation and authority-outage authorization separately. Existing approval/expiry rules remain in force until reviewed; an initial manual-approval slice cannot claim a zero-touch normal week.

## Release assessment

- **Available now:** experimental developer toolkit and administration/reporting prototype, with fixture/pilot limitations explicit. Existing public prototype retains value; this audit does not erase prior bounded evidence.
- **Not ready now:** new-spec general same-host verification product; install-and-operate resilience; automatic clean-edition promotion; full source/control-loss recovery.
- **Possible first limited product after completion:** one supported site's manual-approval S3 edition -> isolated same-host restoration -> scoped result -> owned cleanup, via a supported CLI. It must have a supported way to produce/import its input; no hidden assumption that users can manufacture compatible signed sets. If acquisition is excluded, market it explicitly as a verifier for a documented compatible edition format, not full resilience.
- Extraction alone cannot produce this slice today: fixture restrictions and runner/preflight incompatibility need changes. A wrapper/UI-only release is insufficient.

No new test or acceptance claim. Environment issues, historical test-harness failures and the product gaps above are separate. Keep prior shortened observation closed. Next work is completion of the smallest contract/chain, not another series of unrelated screen/SSH/systemd experiments.
