"""Shared bounded two-container contract for generated WordPress/MariaDB recovery."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

s = importlib.util.spec_from_file_location("same_host_base", Path(__file__).with_name("same-host-preflight.py"))
base = importlib.util.module_from_spec(s); s.loader.exec_module(base)
FORMAT = "owr-same-host-wordpress-pair-v1"
MEMORY = 1024**3
CAPS = {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID", "NET_BIND_SERVICE"}
FIELDS = {"format", "workspace", "production_paths", "token", "db_id", "web_id", "db_image", "web_image"}

def mounts(role):
    paths = {"/tmp": 32, ("/run/mysqld" if role == "db" else "/run"): 32}
    paths.update({"/var/lib/mysql": 512} if role == "db" else
                 {"/var/www/html": 512, "/var/log/apache2": 8, "/var/lock/apache2": 8})
    return {p: f"rw,nosuid,nodev,noexec,size={m*1024**2},mode=1777" for p,m in paths.items()}

def create_args(role, name, image, token, env, db_id=None):
    if role not in {"db", "web"} or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("invalid role/image")
    args = ["docker", "create", "--name", name, "--label", "owr.daily-restore=generated",
            "--label", "owr.recovery-token="+token, "--label", "owr.runtime-role="+role,
            "--network", "none" if role == "db" else "container:"+db_id,
            "--read-only", "--user", "0:0", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--ipc", "private", "--cgroupns", "private",
            "--memory", str(MEMORY), "--memory-swap", str(MEMORY),
            "--cpus", "0.5", "--pids-limit", "128", "--no-healthcheck",
            "--log-driver", "local", "--log-opt", "max-size=1m", "--log-opt", "max-file=2", "--env-file", str(env)]
    for cap in sorted(CAPS): args += ["--cap-add", cap]
    for path, options in mounts(role).items(): args += ["--tmpfs", path+":"+options]
    return args + [image]

def assess(c, inspector=base.inspect_container, phase="prepared"):
    issues=[]
    def check(ok, code):
        if not ok: issues.append(code)
    try:
        if set(c) != FIELDS or c["format"] != FORMAT or phase not in {"prepared","db_started","running"}:
            raise ValueError("invalid configuration")
        if not re.fullmatch(r"[0-9a-f]{32}", c["token"]): raise ValueError("invalid token")
        work=base.local_path(c["workspace"])
        check(work.is_dir() and work.stat().st_uid==os.geteuid() and work.stat().st_mode & 0o777 == 0o700, "workspace_not_private")
        if not isinstance(c["production_paths"],list): raise ValueError("production paths")
        for path in c["production_paths"]:
            prod=base.local_path(path)
            check(not (work==prod or work in prod.parents or prod in work.parents), "production_overlap")
        check(shutil.disk_usage(work).free >= 1024**3, "disk_headroom_insufficient")
        check(not os.statvfs(work).f_flag & os.ST_RDONLY, "workspace_readonly")
        check(base.memory_available() >= (2*MEMORY if phase=="prepared" else 256*1024**2), "memory_headroom_insufficient")
        check(c["db_id"] != c["web_id"], "duplicate_container")
        for role in ("db","web"):
            ident=c[role+"_id"]
            if not re.fullmatch("[0-9a-f]{64}",ident): raise ValueError("exact ID required")
            d=inspector(ident); h=d["HostConfig"]; conf=d["Config"]
            check(d["Id"]==ident and d["Image"]==c[role+"_image"], "image_or_id_mismatch")
            labels=conf.get("Labels") or {}
            check(labels.get("owr.recovery-token")==c["token"] and labels.get("owr.runtime-role")==role
                  and labels.get("owr.daily-restore")=="generated", "ownership_mismatch")
            expected = "running" if phase=="running" or (phase=="db_started" and role=="db") else "created"
            check(d["State"]["Status"]==expected, "runtime_state_mismatch")
            check(conf.get("User")=="0:0" and h.get("ReadonlyRootfs") is True, "runtime_identity_or_rootfs")
            check(not h.get("Privileged") and set(h.get("CapDrop") or [])=={"ALL"}
                  and {cap.removeprefix("CAP_") for cap in (h.get("CapAdd") or [])}==CAPS
                  and set(h.get("SecurityOpt") or [])=={"no-new-privileges"}, "privilege_mismatch")
            check(not h.get("Devices") and not h.get("DeviceRequests") and not h.get("DeviceCgroupRules"), "devices_forbidden")
            check(not h.get("Binds") and not h.get("Mounts") and not h.get("VolumesFrom")
                  and not d.get("Mounts"), "persistent_mounts_forbidden")
            check(h.get("Tmpfs")==mounts(role), "tmpfs_mismatch")
            check(set(conf.get("Volumes") or {}).issubset(mounts(role)), "image_volume_not_shadowed")
            check(not h.get("PidMode") and not h.get("UTSMode") and not h.get("UsernsMode")
                  and h.get("IpcMode")=="private" and h.get("CgroupnsMode")=="private", "namespace_mismatch")
            expected_net="none" if role=="db" else "container:"+c["db_id"]
            networks=set(d["NetworkSettings"]["Networks"])
            check(h.get("NetworkMode")==expected_net and networks==({"none"} if role=="db" else set())
                  and not h.get("PortBindings") and not h.get("PublishAllPorts")
                  and not h.get("Links") and not h.get("ExtraHosts") and not h.get("Dns"), "network_mismatch")
            check(h.get("Memory")==MEMORY and h.get("MemorySwap")==MEMORY and h.get("NanoCpus")==500000000
                  and h.get("PidsLimit")==128 and not h.get("OomKillDisable"), "resource_mismatch")
            check(h.get("LogConfig")=={"Type":"local","Config":{"max-size":"1m","max-file":"2"}}, "log_limit_mismatch")
            check((h.get("RestartPolicy") or {}).get("Name")=="no"
                  and (conf.get("Healthcheck") or {}).get("Test")==["NONE"], "background_execution")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        issues.append("invalid_or_unavailable")
    return {"format":"owr-same-host-pair-assessment-v1","state":"blocked" if issues else "eligible_for_dedicated_trial",
            "phase":phase,"issues":issues,"approval_changed":False,"independent_verification":False,
            "contract":FORMAT}

class Rejected(ValueError):
    def __init__(self, result):
        super().__init__("same-host runtime rejected: "+",".join(result["issues"]))
        self.assessment=result

def require(c, phase):
    result=assess(c,phase=phase)
    if result["issues"]: raise Rejected(result)
    return result
