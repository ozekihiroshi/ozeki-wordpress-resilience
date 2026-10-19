"""Disposable two-host SSH lab; no production or real notification delivery."""
import importlib.util,json,shutil,tempfile,secrets,ipaddress
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if not (ROOT/'run-notification-runtime-lab.py').exists():ROOT=Path('/mnt/d/workspace/ozeki-wordpress-resilience/tools')
s=importlib.util.spec_from_file_location('lab',ROOT/'run-notification-runtime-lab.py');lab=importlib.util.module_from_spec(s);s.loader.exec_module(lab)
run=lab.run
name='owr-observer-'+secrets.token_hex(4);server=name+'-monitor';client=name+'-observer';created=[];checks=[];net=False
def ex(host,*args,**kw):return run('docker','exec',*(['-i'] if kw.get('input') is not None else []),host,*args,**kw)
def ok(value,label):
    if not value:raise AssertionError(label)
    checks.append(label);print('PASS '+label,flush=True)
try:
    ids=run('docker','network','ls','-q').stdout.decode().split()
    used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in (n['IPAM'].get('Config') or []) if c.get('Subnet')]
    used += [ipaddress.ip_network(r['dst'],strict=False) for r in json.loads(run('ip','-j','route').stdout) if r.get('dst') and r['dst']!='default']
    subnet=next(ipaddress.ip_network(f'10.253.{i}.0/28') for i in range(256) if not any(ipaddress.ip_network(f'10.253.{i}.0/28').overlaps(n) for n in used))
    run('docker','network','create','--internal','--subnet',str(subnet),name);net=True
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp);code=work/'code';code.mkdir()
        for n in ['notification-transfer','monitor-runtime-lab','operations-monitor-lab','monitor-delivery','heartbeat-ssh']:
            shutil.copy2(ROOT/(n+'.py'),code/(n+'.py'))
        shutil.copy2(Path(__file__).with_name('watchdog-observer.py'),code/'watchdog-observer.py')
        for k in ['host','client','wrong']:run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/k))
        for host in [server,client]:
            run('docker','run','-d','--name',host,'--network',name,'--memory','256m','--entrypoint','sleep',lab.IMAGE,'infinity');created.append(host)
            ex(host,'mkdir','-p','/opt/owr','/etc/owr','/run/sshd','/health','/state')
            run('docker','cp',str(code)+'/.',host+':/opt/owr/')
            ex(host,'chown','-R','root:root','/opt/owr');ex(host,'chmod','-R','go-w','/opt/owr')
        def put(host,path,value,mode='644'):
            f=work/'upload';f.write_text(value if isinstance(value,str) else json.dumps(value));run('docker','cp',str(f),host+':'+path);ex(host,'chown','root:root',path);ex(host,'chmod',mode,path)
        ex(server,'useradd','-m','-s','/bin/sh','owr-probe');ex(server,'usermod','-p','*','owr-probe')
        put(server,'/etc/owr/host-key',(work/'host').read_text(),'600')
        put(client,'/etc/owr/client',(work/'client').read_text(),'600')
        put(client,'/etc/owr/known_hosts','owr-notification-lab '+(work/'host.pub').read_text())
        put(server,'/etc/owr/authorized_keys','restrict,command="/usr/bin/python3 /opt/owr/watchdog-observer.py endpoint --config /etc/owr/endpoint.json" '+(work/'client.pub').read_text())
        put(server,'/etc/owr/endpoint.json',dict(monitor_id='lab-watchdog',heartbeat_file='/health/heartbeat.json'))
        put(server,'/etc/owr/sshd_config','\n'.join(['Port 2222','HostKey /etc/owr/host-key','PidFile /run/sshd/lab.pid','AuthorizedKeysFile /etc/owr/authorized_keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers owr-probe','AllowTcpForwarding no','AllowAgentForwarding no','PermitTTY no','LogLevel ERROR'])+'\n')
        def sshd():ex(server,'/usr/sbin/sshd','-f','/etc/owr/sshd_config')
        sshd()
        cfg=dict(monitor_id='lab-watchdog',state='/state',stale_after_seconds=5,ssh=dict(site_id='lab',host=server,user='owr-probe',port=2222,identity_file='/etc/owr/client',known_hosts='/etc/owr/known_hosts'))
        put(client,'/etc/owr/observer.json',cfg)
        put(client,'/opt/owr/tick.py', '''import importlib.util,json,sys
from datetime import datetime,timezone,timedelta
s=importlib.util.spec_from_file_location('observer','/opt/owr/watchdog-observer.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def send(e):
 if len(sys.argv)>2:raise RuntimeError('mock outage')
 with open('/state/events.jsonl','a') as f:f.write(json.dumps(e)+'\\n')
print(json.dumps(m.observe(json.load(open('/etc/owr/observer.json')),now=datetime.now(timezone.utc)+timedelta(seconds=int(sys.argv[1])),sender=send)))
''')
        def tick(offset=0,fail=False):return json.loads(ex(client,'python3','/opt/owr/tick.py',str(offset),*(['fail'] if fail else [])).stdout)
        def beat():
            ex(server,'python3','-c',"import json;from datetime import datetime,timezone;json.dump(dict(format='owr-monitor-heartbeat-v1',monitor_id='lab-watchdog',completed_at=datetime.now(timezone.utc).isoformat(),undelivered=0,open_incidents=0),open('/health/heartbeat.json','w'))")
        beat();r=tick()
        if not r['reachable']:
            diagnostic=ex(client,'ssh','-vv','-F','/dev/null','-p','2222','-i','/etc/owr/client','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=owr-notification-lab','-o','UserKnownHostsFile=/etc/owr/known_hosts','owr-probe@'+server,'watchdog-probe',input=b'{"format":"owr-watchdog-probe-v1","nonce":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}',check=False)
            print(diagnostic.stdout.decode(),diagnostic.stderr.decode()[-5000:],flush=True)
        ok(r['reachable'] and not r['watchdog']['active'],'healthy authenticated probe')
        r=tick(8,True);ok(r['reachable'] and 'monitor_stopped' in r['watchdog']['active'] and not r['reachability']['active'],'stalled completion while host reachable')
        ok(r['watchdog']['undelivered']==1,'failed notification retained durably')
        r=tick(8);ok(r['watchdog']['undelivered']==0,'observer restart retries pending alert')
        # Advance real time before fresh completion: simulated clock must never move backwards.
        import time
        time.sleep(9);beat();r=tick();ok(not r['watchdog']['active'],'fresh completion resolves stopped watchdog')
        run('docker','stop','-t','1',server)
        time.sleep(6)
        r=tick();ok(not r['reachable'] and 'monitor_stopped' in r['reachability']['active'],'whole monitored container stopped')
        run('docker','start',server);sshd();r=tick();ok(r['reachable'] and not r['reachability']['active'] and 'monitor_stopped' in r['watchdog']['active'],'SSH recovery does not refresh old completion')
        beat();r=tick();ok(not r['watchdog']['active'],'watchdog fresh recovery')
        put(client,'/etc/owr/known_hosts','owr-notification-lab '+(work/'wrong.pub').read_text())
        time.sleep(6);r=tick();ok(not r['reachable'] and 'monitor_stopped' in r['reachability']['active'],'host pin mismatch fails closed')
        put(client,'/etc/owr/known_hosts','owr-notification-lab '+(work/'host.pub').read_text());beat();tick()
        put(server,'/health/heartbeat.json',{});r=tick();ok(r['reachable'] and 'heartbeat_invalid' in r['watchdog']['active'],'invalid heartbeat separate from reachability')
        beat();r=tick();ok(not r['watchdog']['active'],'valid completion resolves invalid record')
        denied=ex(server,'runuser','-u','owr-probe','--','sh','-c','test -w /health/heartbeat.json || test -w /opt/owr/watchdog-observer.py',check=False)
        ok(denied.returncode!=0,'endpoint cannot modify heartbeat or code')
        before=ex(client,'cat','/state/events.jsonl').stdout;tick();after=ex(client,'cat','/state/events.jsonl').stdout
        ok(before==after,'restart does not duplicate resolved transitions')
        ok(json.loads(run('docker','network','inspect',name).stdout)[0]['Internal'],'isolated network, no external notification')
finally:
    for host in reversed(created):run('docker','rm','-f','-v',host,check=False)
    if net:run('docker','network','rm',name,check=False)
Path(__file__).with_name('watchdog-observer-lab-result.json').write_text(json.dumps(dict(checks=checks,count=len(checks),real_notifications=False,production_modified=False),indent=2)+'\n')
