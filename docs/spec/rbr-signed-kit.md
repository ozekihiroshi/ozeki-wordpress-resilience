# Independently approved S3 reconstruction kit (prototype)

The supported S3 reconstruction entry is `tools/rbr-approved-kit.py`. It requires a separately provisioned public-key pin, an explicitly signed approval, the fixed-version root receipt, and the existing root-protected current-trust registry. The unsigned `rbr-s3-kit.py fetch` CLI is disabled. Low-level Python functions and the disposable fixture runner remain test primitives, not security boundaries against an administrator who replaces code.

The approval binds the complete root receipt (bucket/key/Version ID/size/hash), site, set, sequence, purpose, no-publication flag, and validity window of at most seven days. RSA-SHA256 and the existing current-trust checker are reused. Root references transitively bind A/R/E/C/Q/D, executable code, and actual runtime archives. An approval is not automatically renewed, and signatures do not certify absence of malware. Existing Restore approval formats and conditions are unchanged.

Before the first S3 GET, the entry checks the separate key pin, exact signature, approved-document digest, target, sequence, expiry, and current revocation registry. It rechecks the same registry revision before downloaded planner execution and before reconstruction. Changes require a new invocation/review. Fixed-version contents, code tree, image inventory, and regenerated plan are checked again. Fresh private work/output directories are required for downloading. `--received` may revalidate a complete previously downloaded kit; it still requires a fresh output and performs full signature/reference checks before execution. There is no partially completed target resume or automatic publication.

## Operator flow

1. Keep the root receipt and review the chosen kit outside the publisher. Create an approval with `format: owr-rbr-kit-approval-v1`, `algorithm: rsa-sha256`, `site_id`, `set_id`, positive `sequence`, timezone-bearing `issued_at`/`expires_at`, `scope: generated-private-reconstruction`, `public_activation: false`, and the complete `root_receipt` object.
2. Sign the exact reviewed bytes on the signing side. Provision `public.pem` and `pin.json` independently. The pin includes active status, site, minimum sequence, public-key SHA256 and approved-document SHA256. Never copy the private key to the reconstruction account.
3. Deploy the existing current-trust registry through its existing independently administered procedure. It must name this key, approval digest, site/set, minimum sequence and active status, and have a valid (maximum 24-hour) registry window. Expiry fails closed; renewal is a human approval operation.
4. Run the approved entry with `--trust`, `--approval`, `--signature`, `--receipt`, `--site-id`, `--set-id`, fresh `--work`/`--output` and explicit `--allow-disposable-lab`. Provision a compatible isolated Docker runtime and S3 reader separately. This is a synthetic corporate-site prototype, not a production deployment wizard.
5. Inspect `result.json` and `approval-verification.json`. Successful private reconstruction does not authorize publication.

## Boundaries

Signing and recovery are separate roles. A local dedicated test can enforce account-level separation but does not prove independence against whole-host/root compromise. The bootstrap verifier, current registry provisioning, public-key delivery and host remain trust prerequisites. Compatible classic Docker image identity/architecture is still required. Arbitrary themes/forms and production activation remain unsupported. An expired approval or unavailable current registry intentionally blocks recovery; an authorized operator must supply current trust rather than bypass it.

Experiment results are recorded in `evidence-public/rbr-signed-kit.json`. Environment, harness failures and product limitations are reported separately.

## Findings from the dedicated experiment

- Test infrastructure: the private overlay initially made `/etc` mode 0700. The existing authority checker stopped before any S3 GET. The overlay permission was corrected to 0755 without changing the host `/etc`.
- Product execution control: Python generated a comparator bytecode cache during the first successful reconstruction. Full tree checking correctly rejected this extra executable file on reuse. The runner now starts with `python3 -B`; the old cache was retained outside the kit rather than allowed by the verifier.
- Environment: the previously documented classic Docker compatibility and bridge forwarding requirements remain. Temporary rules apply only within the dedicated bridges and are removed after the experiment.
- The lab signing key is inaccessible to the recovery user. The registry is installed only in a private mount namespace. This verifies privilege separation, not a separate physical signing host.

Final result: PASS. The approved live S3 path retrieved 75 fixed objects and reconstructed twice with both logical states matching Q. Final code then revalidated the received kit and reconstructed two fresh private targets, again matching Q. Fifteen offline signature cases, ten live authority/file-change rejection cases and the disabled unsigned CLI passed. No S3 PUT, production change or publication occurred. Temporary rules and dedicated runtime were removed/stopped.

The temporary network-policy harness also encountered a network-removal/list-inspect race. It removed its rules and stopped; the harness now retries inspection when a network disappears. It was restarted without launching a duplicate reconstruction. The final result includes recovery from that interruption.
