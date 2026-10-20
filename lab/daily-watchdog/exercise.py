import sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'lab/two-vm'))
source=(REPO/'lab/two-vm/exercise.py').read_text()
# Reuse the tested dedicated VM installation and fixed read-only transfer setup.
__file__=str(REPO/'lab/two-vm/exercise.py')
exec(source.split("first=wait('ok')")[0])
from common import ex,run,name
import shutil
STAGE=REPO/'lab/daily-watchdog'
first=wait('ok')
(OUT/'watchdog').mkdir()
shutil.copytree(REPO/'tools',OUT/'code/tools')
shutil.copyfile(STAGE/'observer-loop.py',OUT/'watchdog/observer-loop.py')
for role in ('source','receiver'):
    run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(OUT/'watchdog'/role))
    group='owr-status-read' if role=='source' else 'www-data'
    remote(role,'sudo useradd --system --no-create-home --shell /bin/sh --gid '+group+' owr-daily-probe')
    remote(role,'sudo usermod -p "*" owr-daily-probe')
    config=dict(monitor_id='daily-'+role,site_id='generated-first-site',
                report_file='/var/lib/owr-status-'+('source' if role=='source' else 'web')+'/daily.json')
    write(role,'/etc/owr/watchdog-probe.json',json.dumps(config).encode(),group)
    write(role,'/etc/owr/watchdog-probe-keys',b'restrict,command="/usr/bin/python3 /opt/owr/tools/daily-watchdog-probe.py --config /etc/owr/watchdog-probe.json" '+(OUT/'watchdog'/(role+'.pub')).read_bytes(),group)
    write(role,'/etc/ssh/sshd_config.d/81-owr-probe.conf',b'Match User owr-daily-probe\n    AuthorizedKeysFile /etc/owr/watchdog-probe-keys\n    AuthenticationMethods publickey\n    DisableForwarding yes\n    PermitTTY no\nMatch all\n')
    remote(role,'sudo sshd -t && sudo systemctl reload ssh')
    (OUT/'watchdog'/(role+'-known')).write_bytes(b'owr-notification-daily-'+role.encode()+b' '+(OUT/role/'host.pub').read_bytes())
    cfg=dict(monitor_id='daily-'+role,state='/lab/watchdog/'+role+'-state',stale_after_seconds=100,
        ssh=dict(site_id='daily-'+role,host='127.0.0.1',user='owr-daily-probe',port=2222 if role=='source' else 2223,
                 identity_file='/lab/watchdog/'+role,known_hosts='/lab/watchdog/'+role+'-known'))
    (OUT/'watchdog'/(role+'.json')).write_text(json.dumps(cfg))
    denied=remote(role,'sudo -u owr-daily-probe test -w '+config['report_file'],check=False)
    ok(denied.returncode!=0,role+' probe cannot modify report')
run('docker','exec','-d',name(),'python3','/lab/watchdog/observer-loop.py')
def status(role):
    p=ex('cat','/lab/watchdog/'+role+'-status.json',check=False)
    return json.loads(p.stdout) if p.returncode==0 else None
def await_status(role,alarm,reach=None):
    end=time.monotonic()+240
    while time.monotonic()<end:
        s=status(role)
        if s and bool(s['watchdog']['active'])==alarm and (reach is None or bool(s['reachability']['active'])==reach):
            return s
        time.sleep(3)
    raise RuntimeError('watchdog deadline '+role+' '+str(status(role)))
def delivered():
    p=ex('cat','/lab/watchdog/delivered.jsonl',check=False)
    return [json.loads(x) for x in p.stdout.splitlines()]
def healthy():
    for role in ('source','receiver'):
        s=await_status(role,False,False)
        ok(s['reachable'],role+' authenticated healthy')
def recovered(label):
    healthy()
    event(label,notifications=delivered())
healthy(); event('watchdog_healthy')
# Drop delivery as well: independent durable outbox must retain alarms.
ex('touch','/lab/watchdog/fail-delivery')
qmp('receiver','set_link',{'name':'data0','up':False});event('data_link_down')
s=await_status('receiver',True,False)
ok(s['reachable'] and s['watchdog']['undelivered']>0,'link loss detected while receiver SSH reachable; failed delivery pending')
ok(not status('source')['watchdog']['active'],'source stays healthy during data-link loss')
ex('rm','/lab/watchdog/fail-delivery')
end=time.monotonic()+30
while status('receiver')['watchdog']['undelivered']:
    if time.monotonic()>end:raise RuntimeError('pending alarm not retried')
    time.sleep(2)
ok(any(e['transition']=='opened' for e in delivered()),'pending alarm delivered to local HTTP receiver')
qmp('receiver','set_link',{'name':'data0','up':True})
wait('ok',first['report']['observed_at']);recovered('data_link_recovered')
poweroff('source');event('source_powered_off')
await_status('source',True,True);await_status('receiver',True,False)
event('source_outage_alerted',notifications=delivered())
start('source');wait_ssh('source')
wait('ok');recovered('source_recovered')
poweroff('receiver');event('receiver_powered_off')
await_status('receiver',True,True)
ok(not status('source')['watchdog']['active'],'source healthy while receiver OS stopped')
event('receiver_outage_alerted',notifications=delivered())
start('receiver');wait_ssh('receiver');wait('ok')
recovered('receiver_recovered')
# Restart observer with same durable state; no duplicate transitions.
ex('touch','/lab/watchdog/stop');time.sleep(5)
before=delivered()
restart_at=datetime.now(timezone.utc)
ex('rm','/lab/watchdog/stop')
run('docker','exec','-d',name(),'python3','/lab/watchdog/observer-loop.py');time.sleep(8)
healthy()
tick=json.loads(ex('cat','/lab/watchdog/loop-tick.json').stdout)
ok(datetime.fromisoformat(tick['at'])>restart_at,'restarted observer completes a fresh loop')
ok(delivered()==before,'observer restart preserves state without duplicate delivery')
opened=[(e['site'],e['kind']) for e in before if e['transition']=='opened']
resolved=[(e['site'],e['kind']) for e in before if e['transition']=='resolved']
ok(sorted(opened)==sorted(resolved) and len(opened)>=5,'every alarm has a recovery notification')
ok(len({e['event_id'] for e in before})==len(before),'all accepted notification IDs unique')
ok((OUT/'host-boot-before').read_text()==Path('/proc/sys/kernel/random/boot_id').read_text(),'WSL not rebooted')
ex('touch','/lab/watchdog/stop');time.sleep(5)
result=dict(passed=True,checks=checks,events=events,notifications=before,threshold_seconds=100,
    real_time=True,notification_transport='local HTTP only',external_notifications=False,
    observer_outside_both_guests=True,same_physical_host=True,s3_calls=0)
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('COMPLETE '+str(len(checks)),flush=True)
