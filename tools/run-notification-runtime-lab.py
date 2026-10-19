#!/usr/bin/env python3
"""Real SSH across two disposable isolated containers; mock notification provider only."""
import argparse,ipaddress,json,os,secrets,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE='owr-external-lab:local'

def run(*args,input=None,check=True,timeout=90):
    p=subprocess.run(args,input=input,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(args[0]+' failed: '+p.stderr.decode()[-1200:]+p.stdout.decode()[-1200:])
    return p

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    prefix='owr-runtime-'+secrets.token_hex(5);network=prefix;server=prefix+'-worker';client=prefix+'-web';created=[];checks=[];network_created=False
    def ok(test,label):
        if not test:raise AssertionError(label)
        checks.append(label);print('PASS '+label,flush=True)
    def execute(host,*args,user=None,**kw):return run('docker','exec',*(['-i'] if kw.get('input') is not None else []),*(['-u',user] if user else []),host,*args,**kw)
    print('LAB_RESOURCE_PREFIX '+prefix,flush=True)
    try:
        run('docker','image','inspect',IMAGE)
        ids=run('docker','network','ls','-q').stdout.decode().split()
        used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in (n['IPAM'].get('Config') or []) if c.get('Subnet')]
        for route in json.loads(run('ip','-j','route').stdout):
            if route.get('dst') and route['dst']!='default':used.append(ipaddress.ip_network(route['dst'],strict=False))
        subnet=next((ipaddress.ip_network('10.253.'+str(i)+'.0/28') for i in range(256) if not any(ipaddress.ip_network('10.253.'+str(i)+'.0/28').overlaps(n) for n in used)),None)
        if subnet is None:raise RuntimeError('no non-overlapping dedicated subnet')
        run('docker','network','create','--internal','--subnet',str(subnet),network);network_created=True
        with tempfile.TemporaryDirectory(prefix='owr-runtime-') as temp:
            work=Path(temp);code=work/'code';code.mkdir()
            for name in ['notification-runtime','monitor-runtime-lab','operations-monitor-lab','notification-transfer','notification-live','notification-admin-bridge','notification-dispatch-lab','notification-health','pushover-adapter','monitor-delivery']:
                shutil.copy2(ROOT/'tools'/(name+'.py'),code/(name+'.py'))
            for key in ('host','client','wrong'):
                run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/key))
            for host in (server,client):
                run('docker','run','-d','--name',host,'--network',network,'--memory','256m','--entrypoint','sleep',IMAGE,'infinity');created.append(host)
                execute(host,'mkdir','-p','/opt/owr')
                run('docker','cp',str(code)+'/.',host+':/opt/owr/')
                execute(host,'chown','-R','root:root','/opt/owr')
                execute(host,'chmod','-R','go-w','/opt/owr')
            # Separate ingress and privileged delivery users on the external host.
            execute(server,'groupadd','owr-mailbox')
            for user in ('owr-ingress','owr-worker'):
                execute(server,'useradd','-m','-s','/bin/sh','-G','owr-mailbox',user)
                execute(server,'usermod','-p','*',user)
            execute(server,'mkdir','-p','/run/sshd','/etc/owr','/var/lib/owr-inbox','/var/lib/owr-public','/var/lib/owr-worker')
            for path,owner,mode in [('/var/lib/owr-inbox','owr-ingress:owr-mailbox','2750'),('/var/lib/owr-public','owr-worker:owr-mailbox','2750'),('/var/lib/owr-worker','owr-worker:owr-worker','700')]:
                execute(server,'chown',owner,path);execute(server,'chmod',mode,path)
            execute(client,'groupadd','owr-web')
            for user in ('owr-relay','owr-web'):
                execute(client,'useradd','-m','-s','/bin/sh','-G','owr-web',*(['-g','owr-web'] if user=='owr-web' else []),user)
            execute(client,'mkdir','-p','/var/lib/owr-relay','/var/lib/owr-requests','/var/lib/owr-status')
            for path,owner,mode in [('/var/lib/owr-relay','owr-relay:owr-relay','700'),('/var/lib/owr-requests','owr-web:owr-web','2770'),('/var/lib/owr-status','owr-relay:owr-web','2750')]:
                execute(client,'chown',owner,path);execute(client,'chmod',mode,path)
            def put(host,path,value,owner='root:root',mode='644'):
                file=work/'upload';file.write_text(value if isinstance(value,str) else json.dumps(value))
                run('docker','cp',str(file),host+':'+path);execute(host,'chown',owner,path);execute(host,'chmod',mode,path)
            run('docker','cp',str(work/'host'),server+':/etc/owr/host-key');execute(server,'chmod','600','/etc/owr/host-key')
            forced='restrict,command="/usr/bin/python3 /opt/owr/notification-transfer.py receive --config /etc/owr/receiver.json" '
            put(server,'/etc/owr/authorized_keys',forced+(work/'client.pub').read_text())
            put(server,'/etc/owr/receiver.json',dict(site_id='lab-site',inbox_db='/var/lib/owr-inbox/inbox.sqlite',report_file='/var/lib/owr-public/status.json'))
            put(server,'/etc/owr/stage.json',dict(site_id='lab-site',inbox_db='/var/lib/owr-inbox/inbox.sqlite',worker_requests='/var/lib/owr-worker/requests',stage_db='/var/lib/owr-worker/stage.sqlite',stage_lock='/var/lib/owr-worker/stage.lock'))
            put(server,'/etc/owr/publish.json',dict(site_id='lab-site',worker_status='/var/lib/owr-worker/status.json',public_status='/var/lib/owr-public/status.json'))
            put(server,'/etc/owr/sshd_config','\n'.join(['Port 2222','ListenAddress 0.0.0.0','HostKey /etc/owr/host-key','PidFile /run/sshd/owr.pid','AuthorizedKeysFile /etc/owr/authorized_keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers owr-ingress','AllowTcpForwarding no','AllowAgentForwarding no','X11Forwarding no','PermitTTY no','PermitUserEnvironment no','Subsystem sftp internal-sftp','LogLevel ERROR'])+'\n')
            execute(server,'/usr/sbin/sshd','-f','/etc/owr/sshd_config')
            for key in ('client','wrong'):
                run('docker','cp',str(work/key),client+':/var/lib/owr-relay/'+key);execute(client,'chown','owr-relay:owr-relay','/var/lib/owr-relay/'+key);execute(client,'chmod','600','/var/lib/owr-relay/'+key)
            put(client,'/var/lib/owr-relay/known_hosts','owr-notification-lab-site '+(work/'host.pub').read_text(),'owr-relay:owr-relay','600')
            relay=dict(site_id='lab-site',host=server,user='owr-ingress',port=2222,identity_file='/var/lib/owr-relay/client',known_hosts='/var/lib/owr-relay/known_hosts',requests_dir='/var/lib/owr-requests',relay_lock='/var/lib/owr-relay/relay.lock',status_file='/var/lib/owr-status/status.json')
            put(client,'/var/lib/owr-relay/config.json',relay,'owr-relay:owr-relay','600')
            def relay_run():return execute(client,'python3','/opt/owr/notification-transfer.py','exchange','--config','/var/lib/owr-relay/config.json',user='owr-relay')
            def worker(action):return execute(server,'python3','/opt/owr/lab-worker.py',action,user='owr-worker')
            worker_code='''import importlib.util,json,os,sqlite3,sys,time
from pathlib import Path
def load(n):
 s=importlib.util.spec_from_file_location(n,'/opt/owr/'+n+'.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
os.umask(0o027)
root=Path('/var/lib/owr-worker');live=load('notification-live');bridge=load('notification-admin-bridge');transfer=load('notification-transfer')
class Provider:
 def send(self,event):
  with (root/'sent.jsonl').open('a') as f:f.write(json.dumps(event)+'\\n')
  return {}
if sys.argv[1]=='init':
 (root/'requests').mkdir();(root/'secret').write_text(json.dumps(dict(token='t'*30,user='u'*30)));(root/'secret').chmod(0o600)
 with sqlite3.connect(root/'source.sqlite') as db:db.execute('CREATE TABLE outbox(payload TEXT)')
 settings=dict(format='owr-notification-settings-v1',site_id='lab-site',revision=1,revision_token='rev1',channels=[dict(id='phone',provider='pushover',profile='push',recipient='lab',enabled=True,kinds=['backup_missing'],retry=60,expire=300)])
 config,binding=bridge.compile_settings(settings,dict(push=dict(transport='pushover',credentials_file=str(root/'secret'))),root/'source.sqlite',root/'delivery')
 bridge.dispatch.run(config,factory=lambda c:Provider());live.apply(config,binding,bridge.digest(config))
else:transfer.stage(json.loads(Path('/etc/owr/stage.json').read_text()))
config=live.current(root/'delivery');bridge.dispatch.run(config,factory=lambda c:Provider());live.tests(config,root/'requests',factory=lambda c:Provider())
value=bridge.status(config,dict(config['admin_binding'],config_hash=bridge.digest(config)),simulated=True);value['secret']='DO-NOT-TRANSFER'
transfer.atomic(root/'status.json',value,0o600);transfer.publish(json.loads(Path('/etc/owr/publish.json').read_text()))
'''
            put(server,'/opt/owr/lab-worker.py',worker_code);worker('init')
            ok(json.loads(relay_run().stdout)['report_received'],'pinned SSH retrieves initial sanitized status')
            request_id='11111111-1111-4111-8111-111111111111'
            request=dict(request_id=request_id,site_id='lab-site',channel_id='phone',revision=1,revision_token='rev1',created_at=int(time.time()))
            put(client,'/var/lib/owr-requests/'+request_id+'.json',request,'owr-web:owr-web','640')
            put(client,'/var/lib/owr-requests/.request.lock','','owr-web:owr-web','644')
            put(client,'/opt/owr/lost-ack.py',"import importlib.util,json\ns=importlib.util.spec_from_file_location('t','/opt/owr/notification-transfer.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)\ndef lost(c,p):\n t.ssh(c,p)\n raise TimeoutError('simulated lost acknowledgement')\nt.exchange(json.load(open('/var/lib/owr-relay/config.json')),lost)\n")
            failed=execute(client,'python3','/opt/owr/lost-ack.py',user='owr-relay',check=False)
            ok(failed.returncode!=0 and execute(client,'test','-f','/var/lib/owr-requests/'+request_id+'.json',user='owr-web',check=False).returncode==0,'lost SSH acknowledgement retains local request')
            ok(json.loads(relay_run().stdout)['stored']==1,'web-owned request durably acknowledged across SSH')
            worker('run');relay_run()
            result=json.loads(execute(client,'cat','/var/lib/owr-status/status.json',user='owr-web').stdout)
            ok(result['tests'][0]['status']=='accepted','external worker result returns to web-readable report')
            ok(b'DO-NOT-TRANSFER' not in json.dumps(result).encode(),'private worker fields excluded')
            # Recreate the same request to simulate lost acknowledgement and transport replay.
            put(client,'/var/lib/owr-requests/'+request_id+'.json',request,'owr-web:owr-web','640');relay_run();worker('run');relay_run()
            sent=execute(server,'cat','/var/lib/owr-worker/sent.jsonl',user='owr-worker').stdout.splitlines()
            ok(len(sent)==1,'replay after processing does not send twice')
            ok(json.loads(sent[0])['kind']=='notification_test','only fixed test body reaches mock provider')
            cmd=['ssh','-F','/dev/null','-T','-p','2222','-i','/var/lib/owr-relay/client','-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=owr-notification-lab-site','-o','UserKnownHostsFile=/var/lib/owr-relay/known_hosts','-o','GlobalKnownHostsFile=/dev/null','owr-ingress@'+server]
            for command,label in [('id','arbitrary command denied'),('sftp','SFTP command denied')]:
                ok(execute(client,*cmd,command,user='owr-relay',check=False).returncode!=0,label)
            ok(execute(client,*(cmd[:-1]+['-s',cmd[-1],'sftp']),user='owr-relay',check=False).returncode!=0,'SFTP subsystem denied')
            packet=dict(format='owr-notification-exchange-v1',site_id='foreign-site',nonce='a'*32,requests=[])
            ok(execute(client,*cmd,'notification-exchange',input=json.dumps(packet).encode(),user='owr-relay',check=False).returncode!=0,'foreign site rejected over real SSH')
            ok(execute(client,*cmd,'notification-exchange',input=b'x'*32769,user='owr-relay',check=False).returncode!=0,'oversized SSH input rejected')
            forwarding=cmd[:-1]+['-o','ExitOnForwardFailure=yes','-R','24567:127.0.0.1:22',cmd[-1],'notification-exchange']
            ok(execute(client,*forwarding,user='owr-relay',check=False,timeout=25).returncode!=0,'remote forwarding denied')
            wrong=cmd.copy();wrong[wrong.index('/var/lib/owr-relay/client')]='/var/lib/owr-relay/wrong'
            ok(execute(client,*wrong,'notification-exchange',user='owr-relay',check=False).returncode!=0,'unregistered client key denied')
            put(client,'/var/lib/owr-relay/bad_known','owr-notification-lab-site '+(work/'wrong.pub').read_text(),'owr-relay:owr-relay','600')
            wrong=cmd.copy();wrong[wrong.index('UserKnownHostsFile=/var/lib/owr-relay/known_hosts')]='UserKnownHostsFile=/var/lib/owr-relay/bad_known'
            ok(execute(client,*wrong,'notification-exchange',user='owr-relay',check=False).returncode!=0,'incorrect host pin denied')
            for host,user,path,access,label in [
                (server,'owr-ingress','/var/lib/owr-worker/secret','-r','ingress cannot read provider credential'),
                (server,'owr-ingress','/var/lib/owr-worker/delivery/dispatch.sqlite','-w','ingress cannot alter delivery DB'),
                (server,'owr-worker','/var/lib/owr-inbox/inbox.sqlite','-w','worker cannot mutate transport inbox'),
                (server,'owr-ingress','/opt/owr/notification-transfer.py','-w','ingress cannot alter forced command'),
                (server,'owr-ingress','/var/lib/owr-public/status.json','-w','ingress cannot forge worker report'),
                (client,'owr-web','/var/lib/owr-relay/client','-r','WordPress account cannot read SSH private key'),
                (client,'owr-web','/var/lib/owr-status/status.json','-w','WordPress account cannot overwrite result')]:
                ok(execute(host,'test',access,path,user=user,check=False).returncode!=0,label)
            # Wrong site and stale revision: transport rejects scope, worker blocks stale requests.
            request.update(request_id='22222222-2222-4222-8222-222222222222',revision_token='old')
            put(client,'/var/lib/owr-requests/'+request['request_id']+'.json',request,'owr-web:owr-web','640');relay_run();worker('run');relay_run()
            result=json.loads(execute(client,'cat','/var/lib/owr-status/status.json',user='owr-web').stdout)
            ok(any(t['status']=='blocked' for t in result['tests']),'stale revision is blocked by independent worker')
            # Real recurring processes: independent relay, worker and observer.
            execute(server,'useradd','-m','-s','/bin/sh','-G','owr-mailbox','owr-watchdog')
            execute(server,'mkdir','-p','/var/lib/owr-watchdog');execute(server,'chown','owr-watchdog:owr-watchdog','/var/lib/owr-watchdog');execute(server,'chmod','700','/var/lib/owr-watchdog')
            execute(client,'mkdir','-p','/etc/owr')
            put(server,'/etc/owr/receiver.json',dict(site_id='lab-site',inbox_db='/var/lib/owr-inbox/inbox.sqlite',report_file='/var/lib/owr-public/status.json',relay_monitor_id='lab-relay',relay_heartbeat_file='/var/lib/owr-inbox/relay-heartbeat.json'))
            relay.update(relay_monitor_id='lab-relay',relay_heartbeat_file='/var/lib/owr-relay/heartbeat.json')
            put(client,'/var/lib/owr-relay/config.json',relay,'owr-relay:owr-relay','600')
            put(client,'/etc/owr/runtime-relay.json',dict(monitor_id='lab-relay',heartbeat_file='/var/lib/owr-relay/heartbeat.json',cycle_lock='/var/lib/owr-relay/cycle.lock',transfer_config='/var/lib/owr-relay/config.json'))
            put(server,'/etc/owr/runtime-worker.json',dict(monitor_id='lab-worker',heartbeat_file='/var/lib/owr-public/worker-heartbeat.json',cycle_lock='/var/lib/owr-worker/cycle.lock',stage_config='/etc/owr/stage.json',publish_config='/etc/owr/publish.json',delivery_state='/var/lib/owr-worker/delivery',requests_dir='/var/lib/owr-worker/requests'))
            targets=[dict(role=role,monitor_id='lab-'+role,heartbeat_file=path,watchdog_state='/var/lib/owr-watchdog/'+role,stale_after_seconds=8) for role,path in [('relay','/var/lib/owr-inbox/relay-heartbeat.json'),('worker','/var/lib/owr-public/worker-heartbeat.json')]]
            put(server,'/etc/owr/runtime-watchdog.json',dict(delivery={},targets=targets))
            schedule_code="""import importlib.util,json,os,sys,time
from pathlib import Path
s=importlib.util.spec_from_file_location('runtime','/opt/owr/notification-runtime.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
os.umask(0o027);role=sys.argv[1];base=Path('/var/lib/owr-'+({'relay':'relay','worker':'worker','watchdog':'watchdog'}[role]));(base/'scheduler.pid').write_text(str(os.getpid()))
config=json.loads(Path('/etc/owr/runtime-'+role+'.json').read_text())
def alert(event):
 with (base/'alerts.jsonl').open('a') as f:f.write(json.dumps(event)+'\\n')
class Provider:
 def send(self,event):
  with (base/'sent.jsonl').open('a') as f:f.write(json.dumps(event)+'\\n')
  return {}
while True:
 start=time.monotonic()
 try:
  result=r.watchdog(config,sender=alert) if role=='watchdog' else r.cycle(role,config,**({'factory':lambda c:Provider()} if role=='worker' else {}))
  r.transfer.atomic(base/'last-cycle.json',result)
 except Exception as e:r.transfer.atomic(base/'last-cycle.json',dict(error_type=type(e).__name__))
 time.sleep(max(0.05,1-(time.monotonic()-start)))
"""
            for host in (server,client):put(host,'/opt/owr/lab-schedule.py',schedule_code)
            def start_job(role):
                host=client if role=='relay' else server
                run('docker','exec','-d','-u','owr-'+role,host,'python3','/opt/owr/lab-schedule.py',role)
            def stop_job(role):
                host=client if role=='relay' else server
                pid=int(execute(host,'cat','/var/lib/owr-'+role+'/scheduler.pid').stdout)
                execute(host,'kill','-TERM',str(pid))
            def observed():
                value=execute(server,'cat','/var/lib/owr-watchdog/last-cycle.json',check=False)
                return json.loads(value.stdout) if value.returncode==0 else {}
            def until(predicate,label,timeout=35):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    value=observed()
                    if predicate(value):ok(True,label);return
                    time.sleep(1)
                raise AssertionError(label+' '+json.dumps(observed()))
            def healthy(value):return all(role in value and value[role].get('active')==[] for role in ('relay','worker'))
            for role in ('relay','worker','watchdog'):start_job(role)
            until(lambda v:healthy(v) and execute(server,'test','-f','/var/lib/owr-inbox/relay-heartbeat.json',check=False).returncode==0,'independent recurring jobs reach healthy state')
            stop_job('relay')
            until(lambda v:'monitor_stopped' in v.get('relay',{}).get('active',[]) and v.get('worker',{}).get('active')==[],'relay stop detected while worker continues')
            start_job('relay');until(healthy,'relay recovery resolves its stop incident')
            stop_job('worker')
            until(lambda v:'monitor_stopped' in v.get('worker',{}).get('active',[]) and v.get('relay',{}).get('active')==[],'worker stop detected while relay continues')
            start_job('worker');until(healthy,'worker recovery resolves its stop incident')
            # A live relay process with a broken SSH pin is still a failed transfer.
            good=(work/'host.pub').read_text()
            put(client,'/var/lib/owr-relay/known_hosts','owr-notification-lab-site '+(work/'wrong.pub').read_text(),'owr-relay:owr-relay','600')
            until(lambda v:'monitor_stopped' in v.get('relay',{}).get('active',[]) and v.get('worker',{}).get('active')==[],'SSH outage detected despite live relay scheduler')
            put(client,'/var/lib/owr-relay/known_hosts','owr-notification-lab-site '+good,'owr-relay:owr-relay','600');until(healthy,'SSH restoration resolves transfer incident')
            events=[json.loads(line) for line in execute(server,'cat','/var/lib/owr-watchdog/alerts.jsonl',user='owr-watchdog').stdout.splitlines()]
            ok(sum(e['transition']=='opened' and e['kind']=='monitor_stopped' for e in events)==3,'stop alerts deduplicated across recurring watchdog ticks')
            ok(sum(e['transition']=='resolved' and e['kind']=='monitor_stopped' for e in events)==3,'exactly one recovery for each injected outage')
            for role in ('relay','worker','watchdog'):stop_job(role)
            inspect=json.loads(run('docker','inspect',server,client).stdout)
            ok(all(not item['HostConfig']['PortBindings'] for item in inspect),'no host ports published')
            ok(json.loads(run('docker','network','inspect',network).stdout)[0]['Internal'],'container network has no external route')
    finally:
        failures=[]
        for host in reversed(created):
            if run('docker','rm','-f','-v',host,check=False).returncode:failures.append(host)
        if network_created and run('docker','network','rm',network,check=False).returncode:failures.append(network)
        if failures:raise RuntimeError('cleanup failed '+','.join(failures))
    result=dict(format='owr-notification-runtime-lab-v1',passed=len(checks),checks=checks,external_notifications_sent=0,production_deployed=False,containers_removed=True)
    (a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
