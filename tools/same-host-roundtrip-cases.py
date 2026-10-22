"""Generated-data onboarding harness with a private root-owned current-registry fixture."""
import importlib.util
import json
from pathlib import Path
import tempfile
from datetime import datetime, timezone, timedelta
ROOT=Path(__file__).resolve().parents[1]
REPORT_SCOPE="Shared pair contract: generated capture -> local fixed versions -> test signature/current registry -> isolated WP/MariaDB restore -> registration/cleanup; no S3 or production"
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/"tools"/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(*args, integration=None):
    admission=load("pair_admission","first-site-daily-admission-cases.py")
    onboarding=load("pair_onboarding","onboarding-recovery-cases.py")
    original_onboarding_load=onboarding.load
    with tempfile.TemporaryDirectory(prefix="owr-pair-authority-",dir="/run") as private:
        authority=Path(private)/"current.json"
        def linked(name,file):
            m=original_onboarding_load(name,file)
            if file=="first-site-daily-restore.py":
                m.current_trust.AUTHORITY=authority
                original=m.recover
                def recover(**kw):
                    trust=Path(kw["trust"]);doc=json.loads((trust/"approved.json").read_bytes())
                    now=datetime.now(timezone.utc)
                    authority.write_text(json.dumps(dict(format="owr-current-recovery-trust-v1",
                        revision=1,issued_at=now.isoformat(),expires_at=(now+timedelta(hours=1)).isoformat(),
                        revoked_key_sha256=[],sets=[dict(site_id=m.d.SITE,set_id=kw["set_id"],
                        status="active",public_key_sha256=kw["key_hash"],
                        approved_document_sha256=kw["document_hash"],minimum_sequence=doc["sequence"])])))
                    authority.chmod(0o600)
                    result=original(**kw)
                    isolated=result["isolated_restore"]
                    assert all(isolated[p]["issues"]==[] for p in ("preflight","before_database","before_files"))
                    return result
                m.recover=recover
            return m
        onboarding.load=linked
        original_admission_load=admission.load
        admission.load=lambda name,file: onboarding if file=="onboarding-recovery-cases.py" else original_admission_load(name,file)
        admission.exercise(*args,roundtrip=True,integration=integration)
