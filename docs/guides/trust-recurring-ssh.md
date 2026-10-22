# Recurring registry operation across dedicated SSH hosts

This extends the [recurring operations procedure](trust-recurring-operations.md) using the existing pinned SSH updater. It is separate from the ongoing 72-hour observation and does not renew signed approvals.

The trial uses two fresh Ubuntu QEMU guests with distinct kernel boot IDs. Each is inside its own network-isolated wrapper container; sender-side SSH clients run in those wrappers. This proves separate guest registry/kernel behavior, not different physical failure domains or an independent administration workstation.

The same reviewed registry is deployed and read back from both guests. Only guest B's dedicated deployment authorized key is removed to cause a real SSH authentication failure; its separate lab administrator connection is retained for fault removal. A is updated and confirmed while B remains on its predecessor. B's short-lived registry expires through actual wall-clock passage without clock mocks. The current-trust and signature gates must then reject B while A remains ready. Restoring B's deployment key allows inspect, explicit validation and higher-revision apply, followed by matching readback on both guests.

Readiness here means the existing current-registry check and independent signature authorization both pass. This trial does not download S3 objects or launch restoration. Those integrations have separate prior evidence. No production hosts, keys, IAM, FTP/MySQL or observation datasets are used.

All signed approval files, signatures, public keys and pins are compared before and after on both guests and the sender. Registry renewal does not alter their bytes or approval expiry. The deployment result is not called complete while any intended host is unconfirmed. A stale expected-hash retry after successful recovery must be rejected.

The dedicated guests are stopped after success. Standalone lab private keys and cloud-init seed files are removed; stopped local disk images retain guest SSH host keys and remain private evidence. Public results contain no private keys.

See [machine-readable results](../../evidence-public/trust-recurring-ssh.json) for observed checks and scope. An actual authentication refusal is an intentional test-infrastructure fault, not a plugin defect or an unexplained host outage. Global immediate revocation, privileged-host rollback protection and atomic multi-host rollout remain outside the prototype's guarantee.

## Observed outcome

All seven checks passed on October 22, 2026. Receiver B actually expired at 10:29:06 JST; both receivers were confirmed recovered by 10:29:25 JST. Both dedicated VMs were stopped and standalone private keys removed. No new environment or product fault was established. The intentional authentication refusal is retained in the per-host SSH receipts as an unknown outcome, then reconciled by independent inspection and explicit refresh.
