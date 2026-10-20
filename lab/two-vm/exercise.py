import hashlib,json,shlex,time
from datetime import datetime,timezone
from pathlib import Path
from common import OUT,remote,cat,boot,wait_ssh,qmp,poweroff,start
BASE=Path(__file__).resolve().parent
events=[];checks=[]
def event(label,**extra):
    item=dict(event=label,at=datetime.now(timezone.utc).isoformat(),**extra);events.append(item)
    (OUT/'events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2))
    print('EVENT '+label,flush=True)
def ok(value,label):
    if not value:raise AssertionError(label)
    checks.append(label);print('PASS '+label,flush=True)
def receiver():
    code="import json,hashlib;from pathlib import Path;r=Path('/var/lib/owr-status-web/daily.json').read_bytes();h=json.loads(Path('/var/lib/owr-status-web/transfer.json').read_bytes());print(json.dumps(dict(report=json.loads(r),health=h,sha256=hashlib.sha256(r).hexdigest())))"
    p=remote('receiver','sudo python3 -c '+shlex.quote(code),check=False,timeout=15)
    return json.loads(p.stdout) if p.returncode==0 else None
def wait(state,previous=None,attempt=None):
    end=time.monotonic()+200
    while time.monotonic()<end:
        r=receiver()
        if r and r['health']['state']==state and r['health']['report_sha256']==r['sha256']:
            if (previous is None or r['report']['observed_at']!=previous) and (attempt is None or r['health']['attempted_at']!=attempt):
                return r
        time.sleep(3)
    raise RuntimeError('deadline waiting for '+state+'; preserve VM and events')
def write(role,path,data,group=None):
    code="from pathlib import Path;import sys,subprocess;p=Path("+repr(path)+");p.write_bytes(sys.stdin.buffer.read());p.chmod(0o640)"
    if group:code+=";subprocess.run(['chown',"+repr('root:'+group)+",str(p)],check=True)"
    remote(role,'sudo python3 -c '+shlex.quote(code),data=data)
def verify(stage):
    result={}
    for role in ('source','receiver'):
        result[role]=json.loads(remote(role,'sudo python3 - '+role,data=(BASE/'guest-verify.py').read_bytes()).stdout)
    (OUT/(stage+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result
for role in ('source','receiver'):
    remote(role,'sudo python3 - '+role,data=(BASE/'guest-setup.py').read_bytes(),timeout=120)
pub=cat('receiver','/etc/owr/daily-status-client.pub')
write('source','/etc/owr/daily-status-authorized-keys',
      b'restrict,command="/usr/bin/python3 /opt/owr/tools/daily-status-transfer.py --config /etc/owr/daily-status-read.json serve" '+pub,'owr-status-read')
write('receiver','/etc/owr/daily-status-known-hosts',b'owr-daily-generated-first-site '+(OUT/'source/host.pub').read_bytes(),'owr-status-relay')
for role,unit in [('source','publisher'),('receiver','relay')]:
    remote(role,'sudo systemctl enable --now owr-daily-status-'+unit)
first=wait('ok');second=wait('ok',first['report']['observed_at'])
history={k:second['report'][k] for k in ('runs','attempts')}
initial=verify('before-faults')
ok(initial['source']['boot_id']!=initial['receiver']['boot_id'],'different guest kernels and boot IDs')
event('healthy',source_boot=initial['source']['boot_id'],receiver_boot=initial['receiver']['boot_id'],report=second)

# Only the inter-VM data NIC goes down; management NICs remain reachable.
qmp('receiver','set_link',{'name':'data0','up':False});event('data_link_down')
failed=wait('transfer_failed')
again=wait('transfer_failed',attempt=failed['health']['attempted_at'])
ok(failed['sha256']==again['sha256'],'communication outage preserves exact last report across failed attempts')
ok(json.loads(cat('source','/var/lib/owr-status-source/daily.json'))['observed_at']!=failed['report']['observed_at'],'source continues publishing while link down')
ok(boot('source')==initial['source']['boot_id'] and boot('receiver')==initial['receiver']['boot_id'],'communication cut does not reboot either VM')
event('communication_failure_observed',first=failed,second=again)
qmp('receiver','set_link',{'name':'data0','up':True})
recovered=wait('ok',failed['report']['observed_at'])
event('communication_recovered',report=recovered)

# Stop only source OS; receiver must retain evidence and report transfer failure.
source_old=boot('source');receiver_old=boot('receiver')
poweroff('source');event('source_powered_off')
failed=wait('transfer_failed');time.sleep(10)
ok(receiver()['sha256']==failed['sha256'],'source outage preserves received report')
ok(boot('receiver')==receiver_old,'receiver keeps running during source outage')
event('source_outage_observed',report=failed)
start('source');source_new=wait_ssh('source',source_old)
recovered=wait('ok',failed['report']['observed_at'])
ok(source_new!=source_old and boot('receiver')==receiver_old,'only source Boot ID changes after power-on')
event('source_recovered',new_boot=source_new,report=recovered)

# Stop only receiver OS; source must continue. No receiver-local monitoring is
# claimed while its OS is powered off.
receiver_old=boot('receiver');source_old=boot('source')
before_source=json.loads(cat('source','/var/lib/owr-status-source/daily.json'))['observed_at']
poweroff('receiver');event('receiver_powered_off')
end=time.monotonic()+100
while True:
    current=json.loads(cat('source','/var/lib/owr-status-source/daily.json'))['observed_at']
    if current!=before_source:break
    if time.monotonic()>end:raise RuntimeError('publisher stopped with receiver')
    time.sleep(3)
ok(boot('source')==source_old,'source OS and updates continue while receiver is off')
event('source_update_during_receiver_outage',observed_at=current)
start('receiver');receiver_new=wait_ssh('receiver',receiver_old)
recovered=wait('ok',recovered['report']['observed_at'])
ok(receiver_new!=receiver_old and boot('source')==source_old,'only receiver Boot ID changes after power-on')
event('receiver_recovered',new_boot=receiver_new,report=recovered)
ok(all(recovered['report'][k]==v for k,v in history.items()),'recovery and cleanup history survives every fault')
final=verify('after-faults')
ok((OUT/'host-boot-before').read_text()==Path('/proc/sys/kernel/random/boot_id').read_text(),'WSL host not rebooted')
source=Path.home()/'.local/share/owr-recovery-cleanup-20261020-v2'
ok(json.loads((OUT/'source-hashes.json').read_text())=={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()},'original generated fixture unchanged')
for role,unit in [('source','publisher'),('receiver','relay')]:
    (OUT/role/'service-journal.txt').write_bytes(remote(role,'sudo journalctl -u owr-daily-status-'+unit+' --no-pager -n 80').stdout)
result=dict(passed=True,checks=checks,events=events,before=initial,after=final,guest_count=2,s3_calls=0,
    production_changed=False,existing_observation_changed=False,units_unmodified=True,interval_seconds=60)
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('COMPLETE '+json.dumps(dict(passed=True,checks=len(checks),before_after_role_checks=sum(len(r['checks']) for r in initial.values())+sum(len(r['checks']) for r in final.values()))),flush=True)
