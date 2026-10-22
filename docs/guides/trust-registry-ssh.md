# SSH deployment of current recovery trust

Prototype. Reuses `notification-transfer.py` for pinned, bounded SSH exchanges and `update-current-recovery-trust.py` for protected compare-and-swap deployment. Read [administrator review and failure rules](trust-registry-update.md) first.

## Receiver setup

On a dedicated recovery host, an administrator installs the tools and their imports in a root-owned directory that the SSH user cannot modify, and creates `/etc/owr-trust` as root:root 0755. Use a dedicated deployment account and key. This key is a **trust administrator credential**, never a backup writer or WordPress credential: it can submit reviewed current registries for this host. It is not a signature over upstream authority; administrator review of candidate origin remains required.

Use a root-owned authorized-keys file and restrict that key to this forced command (adapt only the trusted installation path):

```text
restrict,command="sudo -n /usr/bin/python3 -B /opt/owr/tools/trust-registry-ssh.py endpoint" ssh-ed25519 PUBLIC_DEPLOYMENT_KEY
```

A narrowly scoped sudoers rule permits only `/usr/bin/python3 -B /opt/owr/tools/trust-registry-ssh.py endpoint` for that account. Validate sudoers with `visudo -cf` before enabling it. Do not allow a shell, arbitrary Python, arbitrary arguments, uploads to installed code, forwarding or an unrestricted sudo command. The forced command ignores arbitrary requested shell commands; input is the bounded JSON protocol, not shell text. Production has not been provisioned by this exercise.

## Sender setup and operations

Use a separate administrator-controlled sender and independently verified host public key. Example connection JSON:

```json
{"site_id":"recovery-lab","host":"recovery-host.example","user":"trustdeploy","port":22,"identity_file":"/private/deploy-key","known_hosts":"/private/trust-known-hosts"}
```

The known-hosts file entry uses `owr-trust-recovery-lab` as the alias. Obtain the fingerprint through a trusted channel; do not automatically trust an SSH scan. Keep the identity file private. `site_id` labels the host-key alias, not a restriction to one set: this key administers the host's entire registry.

```sh
python3 tools/trust-registry-ssh.py inspect --connection connection.json
python3 tools/trust-registry-ssh.py validate --connection connection.json \
  --candidate candidate.json --candidate-sha256 REVIEWED_SHA256 \
  --expected-current-sha256 INSPECTED_SHA256
python3 tools/trust-registry-ssh.py apply --connection connection.json \
  --candidate candidate.json --candidate-sha256 REVIEWED_SHA256 \
  --expected-current-sha256 INSPECTED_SHA256
python3 tools/trust-registry-ssh.py inspect --connection connection.json
```

Only explicitly reviewed bootstrap uses `absent` as expected hash. Candidate size over SSH is limited to 32 KiB. Preserve the candidate hash, expected installed hash and command output in the administrator's audit record. There is no scheduled deployment, automatic retry or remote-path parameter.

## Outcomes

- `validated`: receiver checked the proposal without replacing the registry.
- `applied`: receiver completed atomic replacement, sync and readback. Inspect independently afterward.
- `rejected`: input or state did not meet review/transition constraints. Inspect and review before a corrected request.
- `unknown`: connection/authentication/timeout or remote I/O prevented a conclusive result. This does **not** mean the registry was unchanged. Reconnect and inspect, comparing its hash with the reviewed candidate and previous hash. Do not blindly resend.

If the new hash is installed after a lost response, record reconciled success instead of sending again. If the old hash remains, diagnose the failure and revalidate before retry. Any other hash requires investigation. Old revisions and stale expected hashes remain rejected even after reconnecting. No communication failure extends an expired registry. Local root/whole-host rollback, upstream authenticity, cross-host atomic distribution and revocation after recovery has already started remain outside this implementation.

## Dedicated exercise

The lab uses a fresh Ubuntu VM under a network-isolated QEMU container, its own keys and generated registry. Sender and receiver have distinct kernel boot IDs. No production host, live backup, production key, FTP/MySQL or ongoing 72-hour resource is used. The response-loss fixture is a separate test-only forced command that delays the SSH reply after actual commit; it is not a production endpoint option. Evidence distinguishes actual SSH failures from injected response delay and does not claim a physical network outage or power-loss test.

Result: 13 dedicated real-SSH checks and 4 protocol regressions passed; the dedicated VM container was stopped. [Evidence](../../evidence-public/trust-registry-ssh.json) preserves the initial product defect (delivered rejection classified as unknown), its fix and validation. No failed attempt was rewritten as a clean first pass.
