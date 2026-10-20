# Dedicated systemd VM acceptance test

Requires WSL/Linux with Docker and /dev/kvm, about 2.3 GB free memory and several GB disk.
Also requires the existing owr-external-lab:local image built from lab/consistency/ExternalLab.Dockerfile (with the pinned BASE_IMAGE used by the existing labs).
Never reboot the WSL host or Docker daemon for this test.
Uses generated fixture ~/.local/share/owr-recovery-cleanup-20261020-v2; production data is not an input.
Only the dedicated QEMU guest reboots. Its enclosing Docker container has network=none,
CPU/memory limits, no host ports, and only /dev/kvm plus dedicated lab/image mounts.

From the repository root:

```sh
docker build -t owr-systemd-vm:lab lab/systemd-vm
python3 lab/systemd-vm/download-image.py
export OWR_VM_LAB_OUTPUT="$HOME/.local/share/owr-systemd-vm-new-unique-trial"
python3 lab/systemd-vm/start-vm.py
python3 lab/systemd-vm/exercise-vm.py
python3 lab/systemd-vm/cleanup-vm.py
```

Use a new output directory; start refuses an existing one. On failure inspect the retained
serial.log, guest services via inspect-vm.py, and recorded container name. Do not rerun
setup blindly. cleanup-vm.py validates the container image, network and mount before
powering off/removing only that VM. It can also clean a failed dedicated trial.
Initial acquisition of the public base image/build packages needs Internet; execution does not.
Image checksum is compared with Ubuntu's SHA256SUMS from the same HTTPS source.

Raw output contains disposable SSH private keys, cloud-init seed and VM disk; keep it private.
Only sanitized evidence belongs in evidence-public. Final reproducible scripts use the
same tested logic with an environment override for output location and repository-relative code path.
OWR_VERIFY_HARDENED is an internal continuation mode used for the recorded baseline comparison;
normal new trials use the final hardened units directly and do not need that variable.
