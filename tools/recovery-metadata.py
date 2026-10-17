#!/usr/bin/env python3
"""Offline metadata bootstrap. Never downloads, extracts, or executes assets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 1024 * 1024
ROLES = {"database", "uploads", "wordpress_core", "themes", "plugins",
         "configuration", "runtime", "recovery_manifest"}
def require(ok, message):
    if not ok:
        raise ValueError(message)

def pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, "duplicate JSON key")
        out[key] = value
    return out

def read(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT, "metadata exceeds 1 MiB")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda x: require(False, "invalid number")), raw

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def validate_schema(document, name):
    schema, _ = read(ROOT / "schemas" / (name + ".schema.json"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)

def validate_ram(ram):
    validate_schema(ram, "recovery-asset-manifest")
    # jsonschema format checks can be disabled by missing optional packages.
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", ram["created_at"]),
            "invalid timestamp")
    require(datetime.fromisoformat(ram["created_at"].replace("Z", "+00:00")).tzinfo is not None,
            "timestamp must have timezone")
    assets = {a["id"]: a for a in ram["assets"]}
    require(len(assets) == len(ram["assets"]), "duplicate asset ID")
    require({a["role"] for a in assets.values()} >= ROLES, "missing mandatory role")
    for a in assets.values():
        require(a["required"], "M1 assets must be required")
        require(a["id"] not in a["depends_on"], "self dependency")
        require(all(d in assets for d in a["depends_on"]), "unknown dependency")
    active, done = set(), set()
    def visit(key):
        require(key not in active, "dependency cycle")
        if key in done:
            return
        active.add(key)
        for dep in assets[key]["depends_on"]:
            visit(dep)
        active.remove(key)
        done.add(key)
    for key in assets:
        visit(key)
    return ram

def validate_set(record, ram, raw):
    validate_schema(record, "recovery-set")
    require(record["site_id"] == ram["site_id"], "site mismatch")
    require(record["set_id"] == ram["set_id"], "set mismatch")
    require(record["ram_sha256"] == digest(raw), "RAM hash mismatch")
    require(record["asset_ids"] == sorted(a["id"] for a in ram["assets"]),
            "set must bind every RAM asset exactly once")

def inspect(ram_path, set_path, expected_set_sha256=None, asset_root=None):
    ram, raw = read(ram_path)
    record, set_raw = read(set_path)
    validate_ram(ram)
    validate_set(record, ram, raw)
    if expected_set_sha256:
        require(re.fullmatch("[0-9a-f]{64}", expected_set_sha256), "invalid anchor")
        require(digest(set_raw) == expected_set_sha256, "independent anchor mismatch")
    results = []
    for asset in ram["assets"]:
        loc = asset["locator"]
        status = "pending" if loc["kind"] == "pending" else "not_observed"
        if asset_root is not None and loc["kind"] == "local":
            root = Path(asset_root).resolve()
            target = (root / loc["path"]).resolve()
            require(target.is_relative_to(root), "asset escapes root")
            require(target.is_file(), "local asset missing")
            size, sha = 0, hashlib.sha256()
            with target.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    size += len(block)
                    require(size <= asset["size_bytes"], "asset larger than declaration")
                    sha.update(block)
            require(size == asset["size_bytes"] and sha.hexdigest() == asset["sha256"],
                    "asset integrity mismatch")
            status = "local_integrity_checked"
        results.append({"id": asset["id"], "role": asset["role"],
                        "locator": loc, "status": status})
    return {"kind": "phase2_metadata_inspection", "schema_version": 1,
            "site_id": ram["site_id"], "set_id": ram["set_id"],
            "metadata_valid": True,
            "anchor": "operator_supplied_digest_matched" if expected_set_sha256 else "not_supplied",
            "authenticity": "unverified", "external_availability": "unverified",
            "restore": "untested", "recovery_ready": False, "assets": results}

def publish(ram_path, output):
    ram, raw = read(ram_path)
    validate_ram(ram)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    record = {"format": "owr-recovery-set", "schema_version": 1,
              "site_id": ram["site_id"], "set_id": ram["set_id"],
              "ram_sha256": digest(raw),
              "asset_ids": sorted(a["id"] for a in ram["assets"])}
    validate_set(record, ram, raw)
    # Exclusive directory reserves ID; failures leave it reserved for inspection.
    destination = output / ram["set_id"]
    destination.mkdir()
    (destination / "ram.json").write_bytes(raw)
    data = (json.dumps(record, indent=2) + "\n").encode()
    (destination / "recovery-set.json").write_bytes(data)
    return {"directory": str(destination), "set_sha256": digest(data),
            "anchor_note": "Transfer digest independently; this output is not a trusted anchor."}

def generate(baseline_path, declarations_path, output):
    baseline, _ = read(baseline_path)
    ram, _ = read(declarations_path)
    # Allowlisted version fields only; no DB data or runtime.env is read.
    env = baseline["environment"]
    ram["created_at"] = datetime.now(timezone.utc).isoformat()
    ram["environment"] = {
        "wordpress": env["wordpress"], "php": env["php"], "database": env["database"],
        "themes": [{"name": env["theme"]["name"], "version": env["theme"]["version"]}],
        "plugins": [{"name": "ozeki-database-backup-for-s3", "version": env["backup_plugin"]}],
        "inventory_scope": "phase1_baseline_only"}
    validate_ram(ram)
    with Path(output).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(ram, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"output": str(output), "evidence_level": "E1", "authenticity": "unverified"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("generate")
    p.add_argument("--baseline", required=True)
    p.add_argument("--declarations", required=True)
    p.add_argument("--output", required=True)
    p = commands.add_parser("freeze")
    p.add_argument("--ram", required=True)
    p.add_argument("--output", required=True)
    p = commands.add_parser("inspect")
    p.add_argument("--ram", required=True)
    p.add_argument("--set", required=True)
    p.add_argument("--expected-set-sha256")
    p.add_argument("--asset-root")
    args = parser.parse_args()
    if args.command == "generate":
        result = generate(args.baseline, args.declarations, args.output)
    elif args.command == "freeze":
        result = publish(args.ram, args.output)
    else:
        result = inspect(args.ram, args.set, args.expected_set_sha256, args.asset_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    from jsonschema.exceptions import ValidationError
    try:
        sys.exit(main())
    except ValidationError as exc:
        print(json.dumps({"error": "schema_validation", "path": list(exc.absolute_path)}),
              file=sys.stderr)
        sys.exit(2)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        # Invalid input values may contain secrets; do not echo them.
        print(json.dumps({"error": type(exc).__name__, "message": "metadata rejected"}),
              file=sys.stderr)
        sys.exit(2)