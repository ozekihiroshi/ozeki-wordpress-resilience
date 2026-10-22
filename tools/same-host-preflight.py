#!/usr/bin/env python3
"""Read-only same-host Docker verification admission. Never creates or starts containers."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("deployment_preflight", Path(__file__).with_name("deployment-preflight.py"))
preflight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preflight)
FIELDS = {"format", "workspace", "production_paths", "container_id", "image_id",
          "memory_bytes", "nano_cpus", "pids_limit", "tmpfs_bytes",
          "required_workspace_bytes", "reserve_disk_bytes", "reserve_memory_bytes"}
NUMBERS = FIELDS - {"format", "workspace", "production_paths", "container_id", "image_id"}


def local_path(value):
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        raise ValueError("absolute Linux path required")
    p = Path(value)
    if ".." in p.parts or any(x.is_symlink() for x in (p, *p.parents)):
        raise ValueError("symlink or traversal")
    return p.resolve(strict=True)


def validate(config):
    if not isinstance(config, dict) or set(config) != FIELDS:
        raise ValueError("invalid_fields")
    if config["format"] != "owr-same-host-verification-v1":
        raise ValueError("invalid_format")
    for key in NUMBERS:
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError("invalid_resource_limit")
    if not re.fullmatch(r"[0-9a-f]{64}", str(config["container_id"])):
        raise ValueError("exact_container_id_required")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(config["image_id"])):
        raise ValueError("exact_image_id_required")
    if not isinstance(config["production_paths"], list) or not config["production_paths"]:
        raise ValueError("production_scope_required")
    work = local_path(config["workspace"])
    if not work.is_dir():
        raise ValueError("workspace_not_directory")
    for item in config["production_paths"]:
        source = local_path(item)
        if work == source or work in source.parents or source in work.parents:
            raise ValueError("workspace_overlaps_production")
    st = work.stat()
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
        raise ValueError("workspace_not_private")
    if config["tmpfs_bytes"] * 2 >= config["memory_bytes"]:
        raise ValueError("tmpfs_exceeds_memory_budget")
    return work


def memory_available():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise ValueError("memory_availability_unknown")


def inspect_container(container_id):
    # Never use shell, remote context, inherited Docker context or TLS overrides.
    env = {k: v for k, v in os.environ.items() if not k.startswith("DOCKER_")}
    command = ["/usr/bin/docker", "--host", "unix:///var/run/docker.sock",
               "inspect", "--type", "container", container_id]
    done = subprocess.run(command, env=env, capture_output=True, timeout=15, check=True)
    if len(done.stdout) > 1024 * 1024:
        raise ValueError("inspect_too_large")
    rows = json.loads(done.stdout)
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("inspect_invalid")
    return rows[0]


def inspect_issues(c, d):
    issues = []
    def require(condition, code):
        if not condition:
            issues.append(code)
    h, conf, state = d["HostConfig"], d["Config"], d["State"]
    require(d["Id"] == c["container_id"] and d["Image"] == c["image_id"], "container_binding_mismatch")
    require(state.get("Status") in {"created", "exited"} and not state.get("Running")
            and not state.get("Paused") and not state.get("Restarting"), "container_not_stopped")
    require(conf.get("User") == "65534:65534", "nonroot_identity_required")
    require(h.get("ReadonlyRootfs") is True, "readonly_root_required")
    require(h.get("NetworkMode") == "none" and not h.get("PortBindings")
            and not h.get("PublishAllPorts") and not h.get("Links")
            and not h.get("ExtraHosts") and not h.get("Dns")
            and set(d["NetworkSettings"]["Networks"]) == {"none"}, "network_isolation_required")
    require(not h.get("Privileged") and set(h.get("CapDrop") or []) == {"ALL"}
            and not h.get("CapAdd") and not h.get("Devices") and not h.get("DeviceRequests")
            and not h.get("DeviceCgroupRules"), "capability_isolation_required")
    require(set(h.get("SecurityOpt") or []) == {"no-new-privileges"}, "security_options_required")
    require(not h.get("PidMode") and not h.get("UTSMode") and not h.get("UsernsMode")
            and h.get("IpcMode") in {"private", "none"}
            and h.get("CgroupnsMode") == "private", "namespace_isolation_required")
    require(not d.get("Mounts") and not h.get("Binds") and not h.get("Mounts")
            and not h.get("VolumesFrom") and not conf.get("Volumes"), "mounts_forbidden")
    require(not conf.get("Healthcheck") and not h.get("Init")
            and (h.get("RestartPolicy") or {}).get("Name") == "no", "background_execution_forbidden")
    require(h.get("Memory") == c["memory_bytes"] and h.get("MemorySwap") == c["memory_bytes"]
            and h.get("NanoCpus") == c["nano_cpus"] and h.get("PidsLimit") == c["pids_limit"]
            and h.get("OomKillDisable") is not True, "resource_limits_mismatch")
    # Strict canonical policy avoids permissive parsing of Docker tmpfs options.
    expected = "rw,nosuid,nodev,noexec,size=" + str(c["tmpfs_bytes"]) + ",mode=1777"
    require(h.get("Tmpfs") == {"/tmp": expected, "/work": expected}, "bounded_tmpfs_required")
    return issues


def assess(config, inspector=inspect_container, memory_probe=memory_available, disk_probe=shutil.disk_usage):
    result = {"format": "owr-same-host-preflight-v1", "state": "blocked",
              "verification_location": "same_host", "independent_verification": False,
              "restore_started": False, "approval_changed": False, "issues": [],
              "not_verified": ["runtime_restore", "all_production_paths_declared",
                               "host_root_compromise", "future_capacity", "approval_and_current_registry"]}
    try:
        work = validate(config)
        result["config_sha256"] = preflight.capture.digest(config)
        fs = os.statvfs(work)
        if fs.f_flag & os.ST_RDONLY:
            result["issues"].append("workspace_readonly")
        if disk_probe(work).free < config["required_workspace_bytes"] + config["reserve_disk_bytes"]:
            result["issues"].append("disk_headroom_insufficient")
        if memory_probe() < config["memory_bytes"] + config["reserve_memory_bytes"]:
            result["issues"].append("memory_headroom_insufficient")
        result["issues"].extend(inspect_issues(config, inspector(config["container_id"])))
    except ValueError:
        result["issues"].append("configuration_or_observation_invalid")
    except (OSError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        result["issues"].append("inspection_unavailable_or_invalid")
    if not result["issues"]:
        result["state"] = "eligible_for_dedicated_trial"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        config = preflight.read_json(args.config)
        if isinstance(config, dict) and config.get("format") == "owr-same-host-wordpress-pair-v1":
            spec = importlib.util.spec_from_file_location("pair_runtime", Path(__file__).with_name("same-host-runtime.py"))
            runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
            result = runtime.assess(config)
        else:
            result = assess(config)
    except (ValueError, OSError, RecursionError):
        result = {"format": "owr-same-host-preflight-v1", "state": "blocked",
                  "restore_started": False, "approval_changed": False,
                  "issues": ["input_unreadable_or_invalid"]}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["state"] == "eligible_for_dedicated_trial" else 2


if __name__ == "__main__":
    raise SystemExit(main())
