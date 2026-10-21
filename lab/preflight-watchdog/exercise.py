import json,shutil,time
from pathlib import Path

def run(repo,out,vm,write,profile,digest,checks):
 state=out/'vm/watchdog';state.mkdir(mode=0o700)
 shutil.copytree(repo/'tools',out/'vm/code/tools')
 shutil.copyfile(repo/'lab/preflight-watchdog/observer-loop.py',state/'observer-loop.py')
 events=[]
 def ok(test,label):
  if not test:raise AssertionError(label)
  checks.append(label);print('PASS '+label,flush=True)
 for role,port in [('source',2224),('receiver',2225)]:
  vm.run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(state/role))
  vm.remote(role,'sudo useradd --system --no-create-home --shell /bin/sh --gid www-data owr-preflight-probe && sudo usermod -p "*" owr-preflight-probe')
  cfg=dict(monitor_id='preflight-'+role,site_id=profile['site_id'],config_sha256=digest,report_file='/var/lib/owr-preflight-web/report.json',health_file='/var/lib/owr-preflight-web/health.json')
  write(role,'/etc/owr/watchdog-probe.json',cfg,0o640,'root:www-data')
  write(role,'/etc/owr/watchdog-keys','restrict,command="/usr/bin/python3 -B /opt/owr/tools/preflight-watchdog-probe.py --config /etc/owr/watchdog-probe.json" '+(state/(role+'.pub')).read_text(),0o644)
  write(role,'/etc/ssh/sshd_config.d/81-preflight-probe.conf','Match User owr-preflight-probe\n AuthorizedKeysFile /etc/owr/watchdog-keys\n AuthenticationMethods publickey\n DisableForwarding yes\n PermitTTY no\nMatch all\n',0o644)
  vm.remote(role,'sudo sshd -t && sudo systemctl reload ssh')
  (state/(role+'-known')).write_text('owr-notification-preflight-'+role+' '+(out/'vm'/role/'host.pub').read_text())
  (state/(role+'.json')).write_text(json.dumps(dict(monitor_id='preflight-'+role,state='/lab/watchdog/'+role+'-state',stale_after_seconds=100,ssh=dict(site_id='preflight-'+role,host='127.0.0.1',user='owr-preflight-probe',port=port,identity_file='/lab/watchdog/'+role,known_hosts='/lab/watchdog/'+role+'-known'))))
  ok(vm.remote(role,'sudo -u owr-preflight-probe test -w /var/lib/owr-preflight-web/report.json',check=False).returncode!=0,role+' probe cannot write reports')
  ok(vm.remote(role,'sudo -u owr-preflight-probe test -x /var/lib/owr-preflight',check=False).returncode!=0,role+' probe cannot read private state')
 vm.run('docker','exec','-d',vm.name(),'python3','/lab/watchdog/observer-loop.py')
 def status(role):return json.loads(vm.ex('cat','/lab/watchdog/'+role+'-status.json').stdout)
 def delivered():
  p=vm.ex('cat','/lab/watchdog/delivered.jsonl',check=False)
  return [json.loads(x) for x in p.stdout.splitlines()]
 def wait(fn,label,seconds=230):
  until=time.monotonic()+seconds
  while time.monotonic()<until:
   try:
    if fn():ok(True,label);return
   except (RuntimeError,ValueError):pass
   time.sleep(3)
  raise AssertionError(label)
 def healthy():return all(not status(r)['watchdog']['active'] and not status(r)['reachability']['active'] for r in ('source','receiver'))
 def note(label):events.append(dict(label=label,source=status('source'),receiver=status('receiver'),notifications=delivered()))
 wait(healthy,'both independent probes healthy');note('initial')
 # Keep HTTP delivery unavailable: alert must remain durable while guest communication is cut.
 vm.ex('touch','/lab/watchdog/fail-delivery')
 vm.qmp('receiver','set_link',{'name':'data0','up':False})
 wait(lambda:bool(status('receiver')['watchdog']['active']) and status('receiver')['watchdog']['undelivered']>0,'preflight transfer outage creates pending independent alert')
 ok(status('receiver')['reachable'] and not status('source')['watchdog']['active'],'management reachable and source healthy during data link failure')
 note('link_failed_delivery_pending')
 vm.ex('rm','/lab/watchdog/fail-delivery')
 wait(lambda:status('receiver')['watchdog']['undelivered']==0 and len(delivered())>0,'pending alarm reaches HTTP receiver')
 vm.qmp('receiver','set_link',{'name':'data0','up':True})
 wait(healthy,'link recovery clears alarm');note('link_recovered')
 # Real service stop, no synthetic timestamps or fake transport.
 vm.remote('source','sudo systemctl stop owr-preflight')
 wait(lambda:bool(status('source')['watchdog']['active']),'inspection service stop detected')
 wait(lambda:bool(status('receiver')['watchdog']['active']),'receiver does not conceal stalled inspection')
 ok(all(status(r)['reachable'] for r in ('source','receiver')),'SSH alone does not imply inspection progress');note('source_stopped')
 vm.remote('source','sudo systemctl start owr-preflight')
 wait(healthy,'inspection restart resolves alerts');note('source_recovered')
 vm.remote('receiver','sudo systemctl stop owr-preflight-transfer')
 wait(lambda:bool(status('receiver')['watchdog']['active']),'transfer service stop detected')
 ok(not status('source')['watchdog']['active'],'inspection stays healthy during transfer stop');note('transfer_stopped')
 vm.remote('receiver','sudo systemctl start owr-preflight-transfer')
 wait(healthy,'transfer restart resolves alert');note('transfer_recovered')
 before=delivered();tick=json.loads(vm.ex('cat','/lab/watchdog/loop-tick.json').stdout)
 vm.ex('touch','/lab/watchdog/stop');time.sleep(7);vm.ex('rm','/lab/watchdog/stop')
 vm.run('docker','exec','-d',vm.name(),'python3','/lab/watchdog/observer-loop.py')
 wait(lambda:json.loads(vm.ex('cat','/lab/watchdog/loop-tick.json').stdout)['pid']!=tick['pid'],'independent observer restarted with same state')
 wait(healthy,'observer restart remains healthy');time.sleep(5)
 ok(delivered()==before,'observer restart does not duplicate notifications')
 opened=[(x['site'],x['kind']) for x in before if x['transition']=='opened'];resolved=[(x['site'],x['kind']) for x in before if x['transition']=='resolved']
 ok(len(opened)>=4 and sorted(opened)==sorted(resolved),'all preflight alarms have recovery notifications')
 ok(len({x['event_id'] for x in before})==len(before),'accepted notification IDs unique')
 ok((out/'vm/host-boot-before').read_text()==Path('/proc/sys/kernel/random/boot_id').read_text(),'WSL not rebooted')
 vm.ex('touch','/lab/watchdog/stop');time.sleep(5)
 (out/'notifications.json').write_text(json.dumps(dict(events=events,notifications=before,threshold_seconds=100,service_interval_seconds=60,real_time=True,external_notifications=False,receiver='local HTTP',observer_outside_both_guests=True),indent=2))
