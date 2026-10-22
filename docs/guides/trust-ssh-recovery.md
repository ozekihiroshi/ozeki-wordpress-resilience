# SSH-deployed current trust at the recovery entry

This dedicated integration connects the existing pinned SSH registry deployment to `first-site-daily-restore.py` without overriding the fixed authority path or replacing its signature/current-trust checks.

The receiver has its own container filesystem and `/etc/owr-trust/current-recovery.json`. A separate sender container applies the reviewed registry through a restricted SSH command and verifies the installed hash. This exercise shares the development host kernel and Docker daemon; it is not a second physical host or another VM. The prior [SSH VM exercise](trust-registry-ssh.md) remains separate evidence.

## Cases

1. A complete old bundle (its own matching public key, pin, approval and valid signature) passes the low-level signature check but is rejected by the actual recovery entry against the SSH-installed current registry. No output directory, storage adapter or GET is started.
2. An otherwise valid signed bundle for a revoked set is likewise blocked before retrieval.
3. The current bundle with a damaged signature is rejected before retrieval: a current-registry match cannot replace signature validation.
4. Only the latest approved bundle proceeds through asset verification and the default actual offline WordPress/MariaDB restoration. Check generated post content, attachment/media hash, HTTP 200, disabled cron/external HTTP, network isolation and cleanup of newly created restore resources. Record the exact SSH-installed registry hash in the recovery result.

Storage is deliberately a local generated fixed-version adapter, using previously generated dedicated test assets. Its version and retention responses are fixtures, **not new AWS evidence**. SSH deployment, current-registry lookup, RSA signatures, recovery entry, file/hash validation, database import, WordPress startup and HTTP check are real. No production data, production keys, existing 72-hour sets or real S3 writes are used.

## Reproduce on a dedicated development Docker host

```sh
python3 tools/run-trust-ssh-recovery-lab.py --execute-lab \
  --fixture /private/generated-previous-attempt \
  --output /private/new-empty-lab-directory
```

The fixture must contain `trust-snapshot/approved.json` and `verified-assets/` from the generated-first-site exercise. Choose a new output directory. The tool generates new disposable signing keys, signed approvals and SSH keys, reuses existing restore code, and uses the preinstalled `owr-external-lab:local` image and pinned images from `lab/m1/images.env`.

The receiver mounts the development Docker socket to exercise the actual restore implementation. This grants daemon-level authority and is a **lab arrangement**, not a recommended production privilege boundary. New restore resources carry the existing ownership labels/tokens and are removed by the existing restore cleanup. No host services are restarted. Completed SSH containers are removed. On an incomplete run, inspect `incomplete.json`, the result/ownership records and live containers before retry; do not blindly restart the whole exercise. Generated local evidence is retained outside the repository.

## Classification

- Environment: no production changes or new unexplained host fault claimed.
- Test infrastructure: the first run specified a nonexistent `/usr/local/bin/python3` for the forced command; image inspection confirmed `/usr/bin/python3`. This was corrected, with failure retained rather than counted as a pass. Later incomplete runs preserve their containers and identity files for diagnosis.
- Product: this is connection verification of existing gates. It does not add global revocation distribution, continuous cancellation after restore starts, root-level rollback protection or malware-cleanliness proof.

The ongoing 72-hour observation and its historical gaps remain unchanged. This new integration result is not a final verdict for that observation.

Four integration cases passed; [evidence](../../evidence-public/trust-ssh-recovery.json) records SSH-installed hash binding, actual restoration and HTTP 200, cleanup, fixture-storage scope and the initial infrastructure correction.
