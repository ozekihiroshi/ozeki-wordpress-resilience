import os
"""Read actual service state and probe mount/DAC restrictions in dedicated VM."""
import hashlib,json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==0 and Path('/etc/hostname').read_text().strip()=='owr-dedicated-vm'
checks=[]
def call(*args):
    return subprocess.run(args,capture_output=True,text=True,timeout=20)
def ok(value,label):
    if not value:raise AssertionError(label)
    checks.append(label)
def user_test(user,flag,path):
    return call('runuser','-u',user,'--','test',flag,path).returncode==0
units={}
for name,user in [('publisher','owr-status-publisher'),('relay','owr-status-relay')]:
    unit='owr-daily-status-'+name+'.service'
    props=dict(line.split('=',1) for line in call('systemctl','show',unit,
        '-p','MainPID','-p','ActiveState','-p','User','-p','Group','-p','NoNewPrivileges',
        '-p','ProtectSystem','-p','ProtectHome','-p','PrivateTmp','-p','ReadWritePaths',
        '-p','UnitFileState','-p','NRestarts','-p','ExecMainStartTimestamp').stdout.splitlines())
    ok(props['ActiveState']=='active' and props['UnitFileState']=='enabled',name+' enabled and active')
    ok(props['User']==user and props['NoNewPrivileges']=='yes' and props['ProtectSystem']=='strict' and props['ProtectHome']=='yes' and props['PrivateTmp']=='yes',name+' production restrictions loaded')
    pid=props['MainPID'];status=Path('/proc/'+pid+'/status').read_text()
    ok('NoNewPrivs:\t1' in status,name+' actual NoNewPrivs=1')
    ok(Path('/etc/systemd/system/'+unit).read_bytes()==Path('/opt/owr/examples/daily-status-transfer/'+unit).read_bytes(),name+' exact unmodified production unit')
    if 'CapabilityBoundingSet=' in Path('/etc/systemd/system/'+unit).read_text():
        extra=['CapabilityBoundingSet','AmbientCapabilities','PrivateDevices','ProtectKernelTunables',
               'ProtectKernelModules','ProtectKernelLogs','ProtectControlGroups','ProtectClock',
               'ProtectHostname','RestrictSUIDSGID','RestrictRealtime','LockPersonality',
               'RestrictNamespaces','RestrictAddressFamilies','SystemCallArchitectures',
               'MemoryDenyWriteExecute','PrivateNetwork']
        extended=dict(line.split('=',1) for line in call('systemctl','show',unit,*[a for p in extra for a in ('-p',p)]).stdout.splitlines())
        ok(extended['CapabilityBoundingSet']=='' and extended['AmbientCapabilities']=='',name+' capability sets empty')
        ok('CapBnd:\t0000000000000000' in status and 'CapEff:\t0000000000000000' in status,name+' actual effective and bounding capabilities empty')
        for key in extra[2:13]+['MemoryDenyWriteExecute']:
            ok(extended[key]=='yes',name+' '+key+' enabled')
        ok(extended['RestrictNamespaces'] in ('yes','~'),name+' namespaces restricted')
        ok(set(extended['RestrictAddressFamilies'].split())=={'AF_UNIX','AF_INET','AF_INET6'},name+' only required address families configured')
        ok('Seccomp:\t2' in status,name+' actual syscall filtering active')
        if name=='publisher':
            ok(extended['PrivateNetwork']=='yes' and os.readlink('/proc/'+pid+'/ns/net')!=os.readlink('/proc/self/ns/net'),'publisher isolated network namespace')
        props.update(extended)
    prefix=['nsenter','--target',pid,'--mount','--','runuser','-u',user,'--']
    ok(user_test(user,'-w','/etc/owr/world-writable-probe'),name+' probe is writable without namespace protection')
    code="import errno; p='/etc/owr/world-writable-probe'\ntry:\n open(p,'a').write('unexpected')\nexcept OSError as e:\n assert e.errno==errno.EROFS\nelse: raise AssertionError('write allowed')"
    r=call(*prefix,'python3','-c',code);ok(r.returncode==0,name+' ProtectSystem really rejects world-writable /etc probe: '+r.stderr[:100])
    ok(user_test(user,'-r','/home/owr-home-probe/readable'),name+' home probe readable outside namespace')
    ok(call(*prefix,'test','-r','/home/owr-home-probe/readable').returncode!=0,name+' ProtectHome blocks probe inside namespace')
    ok(call(*prefix,'test','-e','/tmp/owr-host-tmp-probe').returncode!=0,name+' private tmp does not expose host marker')
    marker='/tmp/owr-private-'+name
    ok(call(*prefix,'touch',marker).returncode==0 and not Path(marker).exists(),name+' private tmp writes stay isolated')
    ok(not user_test(user,'-w','/opt/owr/tools/daily-status-transfer.py'),name+' cannot modify code')
    ok(not user_test(user,'-w','/etc/owr/daily-status-'+('publish' if name=='publisher' else 'relay')+'.json'),name+' cannot modify config')
    units[name]=props
for user in ('www-data','owr-status-reader','owr-status-publisher'):
    ok(not user_test(user,'-r','/etc/owr/daily-status-client'),user+' cannot read relay private key')
for user in ('www-data','owr-status-reader','owr-status-relay'):
    ok(not user_test(user,'-r','/var/lib/owr-daily/daily.sqlite'),user+' cannot read ledger')
ok(user_test('owr-status-publisher','-r','/var/lib/owr-daily/daily.sqlite') and not user_test('owr-status-publisher','-w','/var/lib/owr-daily/daily.sqlite'),'publisher reads ledger but cannot write it')
ok(not user_test('owr-status-reader','-w','/var/lib/owr-status-source/daily.json'),'SSH reader cannot modify source report')
ok(user_test('www-data','-r','/var/lib/owr-status-web/daily.json') and not user_test('www-data','-w','/var/lib/owr-status-web/daily.json'),'web user reads delivered report but cannot write it')
raw=Path('/var/lib/owr-status-web/daily.json').read_bytes()
health=json.loads(Path('/var/lib/owr-status-web/transfer.json').read_bytes())
ok(health['state']=='ok' and health['report_sha256']==hashlib.sha256(raw).hexdigest(),'actual pinned SSH transfer and hash binding')
report=json.loads(raw)
ok(any(r['phase']=='restore_verified' for r in report['runs']),'restore verified history preserved')
hashes={str(p.relative_to('/var/lib/owr-daily')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/var/lib/owr-daily').rglob('*') if p.is_file()}
ok(hashes==json.loads(Path('/root/owr-source-before.json').read_text()),'source bytes unchanged')
print(json.dumps(dict(passed=True,checks=checks,units=units,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    kernel=call('uname','-r').stdout.strip(),report=report,transfer=health),ensure_ascii=False))
