"""Shared isolated runtime using existing generated SSH/S3 integration and trust gates."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
ROOT=Path(__file__).resolve().parents[1]
REPORT_SCOPE='Generated data: existing SSH inventory and experimental S3 fixed versions/retention -> unchanged test signature/current-registry gates -> shared pair preparation/inspection/restore -> daily registration/cleanup; no production changes'
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(*args):
    db,web,php,sql,hold,ready,release,run,check,results,output=args
    existing=load('pair_real_integration','onboarding-ssh-s3-cases.py')
    integration=existing.Integration(db,web,sql,run,results)
    # Root owns the disposable trust fixture; SSH retains the existing operator's
    # config/host pins. No keys are copied and no remote files are modified.
    def authorize(actor,**request):
        host={'writer':'community','reader':'dm'}[actor]
        script=(ROOT/'tools/lab-s3-request.py').read_text()
        p=subprocess.run(['runuser','-u','ozeki','--','ssh','-o','BatchMode=yes',
            '-o','ConnectTimeout=15',host,'python3 -c '+shlex.quote(script)],
            input=json.dumps({'actor':actor,**request}).encode(),capture_output=True,timeout=120)
        if p.returncode:raise RuntimeError('Existing lab role authorization failed; details suppressed')
        return json.loads(p.stdout)
    integration.transport.authorize=authorize
    try:
        load('pair_shared_cases','same-host-roundtrip-cases.py').exercise(*args,integration=integration)
    finally:
        integration.close()
