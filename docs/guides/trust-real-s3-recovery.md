# SSH current trust with real fixed-version S3 recovery

This extends the [SSH-to-recovery integration](trust-ssh-recovery.md) by replacing fixture storage responses with actual requests through the existing `queue-s3-adapter.py`. Run with `--real-s3` on the dedicated development Docker host:

```sh
python3 tools/run-trust-ssh-recovery-lab.py --execute-lab --real-s3 \
  --fixture /private/generated-previous-attempt \
  --output /private/new-real-s3-lab-directory
```

Only the previous dedicated generated-data set's exact approved object versions are reused. No new S3 object is written, no production approval is renewed, and no ongoing 72-hour observation set is selected. New signatures and the new registry are disposable test trust.

## Execution boundary

The separate sender uses pinned SSH to install the current registry on the dedicated receiver. That receiver calls the actual recovery entry with its fixed root-owned authority file. The old self-consistent bundle, revoked set and damaged latest signature are checked before the valid latest request.

The receiver is network-isolated. A **test-only Unix socket broker** on WSL calls the existing real S3 adapter; only the two exact locators in the selected manifest are allowed, with at most two requests. This avoids copying the workstation's SSH credentials to the receiver. The adapter uses the existing EC2 role authorization path (`OwrM1RecoveryReader`) and sends actual HTTPS GET requests containing the fixed Version IDs. Live response version, retention, encryption, size and content hashes are checked by the existing adapter and recovery gate. Downloaded bytes, not the local original fixture files, feed the default offline restoration.

This broker is test infrastructure, not a new production credential service or direct network access from the isolated receiver. The receiver shares the development host kernel and Docker daemon; physical host/daemon independence is not claimed. The prior separate-VM SSH verification remains separate evidence.

## Evidence and failure handling

- Denied attempts must construct no retrieval adapter, issue no object GET and leave no broker request event. Bucket metadata preflight is distinct from object retrieval.
- The accepted request must produce exactly two actual fixed-version GETs and no PUT, with successful retention/content verification.
- Real WordPress/MariaDB import, post/media checks, HTTP 200, disabled cron/external HTTP, isolation and cleanup use the existing default restore implementation.
- The broker writes a `started` event before retrieval and retains receipts. A failed or uncertain operation is not retried automatically. Inspect the incomplete workspace and live resources before continuing.

Production data, production keys, IAM, FTP/MySQL and observation resources remain unchanged. Classify an SSH/AWS/host error by evidence, not as a plugin defect by default. Preserve failed attempts separately from successful trials. This trial does not establish malware cleanliness, online global revocation, root-level rollback prevention or cancellation after restoration has started.

Result: four cases passed, exactly two actual fixed-version GETs and no PUT. Restored generated post/media matched and HTTP returned 200; restore and SSH containers were removed. [Evidence](../../evidence-public/trust-real-s3-recovery.json) includes live Version IDs, retention receipts and scope limitations. No new environment or product fault was observed in this run.
