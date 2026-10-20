import hashlib,json,os,subprocess,sys
from pathlib import Path
role=sys.argv[1];assert role in ('source','receiver') and os.geteuid()==0
assert Path('/etc/hostname').read_text().strip()=='owr-two-'+role
mode='publisher' if role=='source' else 'relay'
unit='owr-daily-status-'+mode+'.service';user='owr-status-'+mode
checks=[]
def call(*args):return subprocess.run(args,capture_output=True,text=True,timeout=20)
def ok(value,label):
    if not value:raise AssertionError(label)
    checks.append(label)
props=dict(line.split('=',1) for line in call('systemctl','show',unit,*[x for p in
    ('MainPID','ActiveState','UnitFileState','User','NoNewPrivileges','ProtectSystem','ProtectHome','PrivateTmp',
     'PrivateDevices','PrivateNetwork','CapabilityBoundingSet','MemoryDenyWriteExecute','NRestarts') for x in ('-p',p)]).stdout.splitlines())
ok(props['ActiveState']=='active' and props['UnitFileState']=='enabled','own service enabled and active')
ok(props['User']==user and props['ProtectSystem']=='strict' and props['ProtectHome']=='yes','dedicated identity and filesystem restrictions')
ok(props['NoNewPrivileges']=='yes' and props['PrivateTmp']=='yes' and props['PrivateDevices']=='yes' and props['MemoryDenyWriteExecute']=='yes','hardening enabled')
status=Path('/proc/'+props['MainPID']+'/status').read_text()
ok('CapBnd:\t0000000000000000' in status and 'CapEff:\t0000000000000000' in status,'actual capabilities empty')
ok('NoNewPrivs:\t1' in status and 'Seccomp:\t2' in status,'actual privilege and syscall restrictions')
ok(Path('/etc/systemd/system/'+unit).read_bytes()==Path('/opt/owr/examples/daily-status-transfer/'+unit).read_bytes(),'exact production unit content')
def access(who,flag,path):return call('runuser','-u',who,'--','test',flag,path).returncode==0
ok(not access(user,'-w','/opt/owr/tools/daily-status-transfer.py'),'service cannot modify code')
if role=='source':
    ok(not Path('/var/lib/owr-status-web').exists() and not Path('/etc/owr/daily-status-client').exists(),'no receiver state or private key on source VM')
    ok(props['PrivateNetwork']=='yes','publisher private network')
    ok(access(user,'-r','/var/lib/owr-daily/daily.sqlite') and not access(user,'-w','/var/lib/owr-daily/daily.sqlite'),'publisher ledger read only')
    ok(not access('owr-status-reader','-r','/var/lib/owr-daily/daily.sqlite'),'SSH reader cannot read ledger')
    ok(not access('owr-status-reader','-w','/var/lib/owr-status-source/daily.json'),'SSH reader cannot modify report')
    hashes={str(p.relative_to('/var/lib/owr-daily')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/var/lib/owr-daily').rglob('*') if p.is_file()}
    ok(hashes==json.loads(Path('/root/source-before.json').read_text()),'source data unchanged')
else:
    ok(not Path('/var/lib/owr-daily').exists() and not Path('/var/lib/owr-status-source').exists(),'no source ledger or publisher report on receiver VM')
    ok(not access('www-data','-r','/etc/owr/daily-status-client'),'web cannot read private key')
    ok(access('www-data','-r','/var/lib/owr-status-web/daily.json') and not access('www-data','-w','/var/lib/owr-status-web/daily.json'),'web report read only')
    raw=Path('/var/lib/owr-status-web/daily.json').read_bytes();health=json.loads(Path('/var/lib/owr-status-web/transfer.json').read_text())
    ok(health['state']=='ok' and health['report_sha256']==hashlib.sha256(raw).hexdigest(),'received report and healthy hash binding')
    ok(any(r['phase']=='restore_verified' for r in json.loads(raw)['runs']),'restore history preserved')
print(json.dumps(dict(role=role,passed=True,checks=checks,properties=props,
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()),ensure_ascii=False))
