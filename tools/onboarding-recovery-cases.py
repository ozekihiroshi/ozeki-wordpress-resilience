"""New admission-to-recovery boundary; local versioned transport, real isolated restore."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT_SCOPE='Generated WP/MariaDB admission to signed isolated recovery and status registration; local fixed-version substitute, synthetic inventory/retention, disposable test signer; no AWS/SSH/production or 72h observation changes'
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(*args):
    load('admission_cases','first-site-daily-admission-cases.py').exercise(*args,roundtrip=True)

def finish(daily,row,root,paths,Adapter,operations,run,check,results):
    api=load('roundtrip_daily','first-site-daily.py')
    recovery=load('roundtrip_restore','first-site-daily-restore.py')
    worker=load('roundtrip_worker','first-site-daily-recovery-worker.py').Worker(daily.root)
    trust=root/'independent-test-operator'
    def recover(**kw):return recovery.recover(**kw,adapter_factory=Adapter)
    before=list(operations)
    try:worker.run('before-approval',row['day'],trust,recover=recover)
    except ValueError:pass
    else:raise RuntimeError('unsigned set accepted')
    check(operations==before and worker.row('before-approval') is None,'unsigned recovery had side effects')
    results.append(dict(name='unsigned_admitted_set_no_recovery_or_read',passed=True))
    work=daily.root/row['id']
    check(not list(daily.root.rglob('*.pem')),'publisher contains signing key')
    run('python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',str(work/'candidate.json'),'--operator',str(trust))
    doc=api.gate.sha((trust/'approved.json').read_bytes());key=api.gate.sha((trust/'public.pem').read_bytes())
    sig=(trust/'approved.sig').read_bytes();(trust/'approved.sig').write_bytes(b'invalid')
    try:daily.approve(row['day'],trust,doc,key,Adapter)
    except ValueError:pass
    else:raise RuntimeError('invalid signature accepted')
    check(operations==before,'invalid signature read remote assets')
    (trust/'approved.sig').write_bytes(sig)
    daily.approve(row['day'],trust,doc,key,Adapter)
    check(daily.status(api.gate.now())['runs'][0]['phase']=='approved','approval confused with restore')
    results.append(dict(name='separate_signature_approval_and_invalid_signature_rejection',passed=True))
    # Make capture workspace unavailable. Recovery must use fixed remote versions.
    paths['workspace'].rename(root/'capture-unavailable')
    result=worker.run('approved-roundtrip',row['day'],trust,recover=recover)
    check(result['outcome']=='succeeded' and result['registration']=='recorded','isolated restore or result registration failed')
    status=daily.status(api.gate.now())
    check(status['runs'][0]['phase']=='restore_verified' and not status['production_recovery_approved'],'incorrect final status')
    snapshot=list(operations)
    check(worker.run('approved-roundtrip',row['day'],trust,recover=recover)==result and operations==snapshot,'duplicate recovery repeated work')
    check(sum(x['method']=='PUT' for x in operations)==2,'recovery wrote storage')
    api.io.write_json(root/'roundtrip-status.json',status)
    results.append(dict(name='admitted_capture_signed_fixed_version_real_isolated_restore_registered',passed=True,transport='local substitute, not AWS',capture_workspace_available=False))
    results.append(dict(name='duplicate_recovery_no_get_put_or_restore',passed=True))
