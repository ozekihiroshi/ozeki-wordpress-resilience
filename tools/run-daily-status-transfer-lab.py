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
    prefix='owr-daily-wire-'+secrets.token_hex(5);network=prefix;server=prefix+'-worker';client=prefix+'-web';created=[];checks=[];network_created=False
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
        with tempfile.TemporaryDirectory(prefix='owr-daily-wire-') as temp:
            work=Path(temp);code=work/'code';code.mkdir()
            for name in ['notification-transfer','notification-live','notification-admin-bridge','notification-dispatch-lab','notification-health','pushover-adapter','monitor-delivery']:
                shutil.copy2(ROOT/'tools'/(name+'.py'),code/(name+'.py'))
            for key in ('host','client','wrong'):
                run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/key))
            for host in (server,client):
                run('docker','run','-d','--name',host,'--network',network,'--memory','256m','--entrypoint','sleep',IMAGE,'infinity');created.append(host)
                execute(host,'mkdir','-p','/opt/owr')
                run('docker','cp',str(ROOT/'tools'),host+':/opt/owr/tools')
                run('docker','cp',str(ROOT/'schemas'),host+':/opt/owr/schemas')
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

            tool='/opt/owr/tools/daily-status-transfer.py'
            forced='restrict,command="/usr/bin/python3 '+tool+' --config /etc/owr/read.json serve" '
            put(server,'/etc/owr/authorized_keys',forced+(work/'client.pub').read_text())
            source=Path.home()/'.local/share/owr-recovery-cleanup-20261020-v2'
            import hashlib
            original={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
            run('docker','cp',str(source),server+':/var/lib/owr-worker/state')
            execute(server,'chown','-R','owr-worker:owr-worker','/var/lib/owr-worker')
            producer=dict(site_id='generated-first-site',state='/var/lib/owr-worker/state',
                report_file='/var/lib/owr-public/daily.json',producer_health='/var/lib/owr-public/producer.json',
                lock_file='/var/lib/owr-worker/publish.lock')
            put(server,'/etc/owr/publish.json',producer)
            put(server,'/etc/owr/read.json',{k:producer[k] for k in ('site_id','report_file','producer_health')})
            put(server,'/etc/owr/sshd_config',chr(10).join(['Port 2222','ListenAddress 0.0.0.0','HostKey /etc/owr/host-key','PidFile /run/sshd/owr.pid','AuthorizedKeysFile /etc/owr/authorized_keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers owr-ingress','AllowTcpForwarding no','AllowAgentForwarding no','X11Forwarding no','PermitTTY no','PermitUserEnvironment no','LogLevel ERROR'])+chr(10))
            execute(server,'/usr/sbin/sshd','-f','/etc/owr/sshd_config')
            for key in ('client','wrong'):
                run('docker','cp',str(work/key),client+':/var/lib/owr-relay/'+key)
                execute(client,'chown','owr-relay:owr-relay','/var/lib/owr-relay/'+key)
                execute(client,'chmod','600','/var/lib/owr-relay/'+key)
            put(client,'/var/lib/owr-relay/known_hosts','owr-daily-generated-first-site '+(work/'host.pub').read_text(),'owr-relay:owr-relay','600')
            relay=dict(site_id='generated-first-site',host=server,user='owr-ingress',port=2222,
                identity_file='/var/lib/owr-relay/client',known_hosts='/var/lib/owr-relay/known_hosts',
                status_file='/var/lib/owr-status/daily.json',transfer_health='/var/lib/owr-status/transfer.json',
                lock_file='/var/lib/owr-relay/pull.lock')
            put(client,'/var/lib/owr-relay/config.json',relay,'owr-relay:owr-relay','600')
            def publish():return execute(server,'python3',tool,'--config','/etc/owr/publish.json','publish',user='owr-worker',check=False)
            def pull():return execute(client,'python3',tool,'--config','/var/lib/owr-relay/config.json','relay',user='owr-relay',check=False)
            def get(host,path):return json.loads(execute(host,'cat',path).stdout)
            ok(publish().returncode==0,'actual generated daily snapshot published')
            ok(pull().returncode==0,'fixed-command pinned SSH transfers snapshot')
            baseline=execute(client,'cat',relay['status_file']).stdout
            ok(execute(client,'test','-w',relay['status_file'],user='owr-web',check=False).returncode!=0,'WordPress user cannot write report')
            ok(execute(client,'test','-r',relay['identity_file'],user='owr-web',check=False).returncode!=0,'WordPress user cannot read SSH key')
            ok(execute(server,'test','-w',producer['report_file'],user='owr-ingress',check=False).returncode!=0,'SSH ingress cannot write report')
            ok(execute(server,'test','-r',producer['state']+'/daily.sqlite',user='owr-ingress',check=False).returncode!=0,'SSH ingress cannot read source ledger')
            initial_stamp=get(client,relay['status_file'])['observed_at']
            # Real periodic processes, with one-second dedicated lab interval.
            run('docker','exec','-d','-u','owr-worker',server,'sh','-c','echo $$ > /var/lib/owr-worker/loop.pid; exec python3 '+tool+' --config /etc/owr/publish.json publish --interval 1')
            run('docker','exec','-d','-u','owr-relay',client,'sh','-c','echo $$ > /var/lib/owr-relay/loop.pid; exec python3 '+tool+' --config /var/lib/owr-relay/config.json relay --interval 1')
            stamps=set();deadline=time.monotonic()+25
            while len(stamps)<3 and time.monotonic()<deadline:
                value=get(client,relay['status_file'])['observed_at']
                if value!=initial_stamp:stamps.add(value)
                time.sleep(.5)
            ok(len(stamps)>=3,'three real periodic publish/pull updates observed')
            ok(publish().returncode!=0 and pull().returncode!=0,'duplicate periodic execution refused by lock')
            for host,path,user in [(server,'/var/lib/owr-worker/loop.pid','owr-worker'),(client,'/var/lib/owr-relay/loop.pid','owr-relay')]:
                pid=execute(host,'cat',path).stdout.decode().strip()
                execute(host,'kill','-TERM',pid,user=user)
            time.sleep(1)
            old=get(client,relay['status_file'])
            # Bad host key is an actual SSH failure; previous report bytes must survive.
            good=(work/'host.pub').read_text()
            put(client,'/var/lib/owr-relay/known_hosts','owr-daily-generated-first-site '+(work/'wrong.pub').read_text(),'owr-relay:owr-relay','600')
            before=execute(client,'cat',relay['status_file']).stdout
            ok(pull().returncode!=0 and get(client,relay['transfer_health'])['state']=='transfer_failed','host-key mismatch shown as transfer failure')
            ok(execute(client,'cat',relay['status_file']).stdout==before,'failed transfer retains exact last report')
            run('docker','cp',client+':'+relay['transfer_health'],str(a.output/'transfer-failed.json'))
            put(client,'/var/lib/owr-relay/known_hosts','owr-daily-generated-first-site '+good,'owr-relay:owr-relay','600')
            ok(pull().returncode==0,'transfer recovers after pinned key restored')
            # Force source read failure using dedicated nonexistent source only.
            bad=dict(producer,state='/var/lib/owr-worker/absent')
            put(server,'/etc/owr/publish.json',bad)
            ok(publish().returncode!=0 and pull().returncode!=0,'producer failure delivered without losing previous report')
            ok(get(client,relay['transfer_health'])['state']=='source_failed','source failure distinguished from transport failure')
            run('docker','cp',client+':'+relay['transfer_health'],str(a.output/'source-failed.json'))
            put(server,'/etc/owr/publish.json',producer);ok(publish().returncode==0 and pull().returncode==0,'periodic path can resume after source repair')
            for name,path in [('daily.json',relay['status_file']),('transfer.json',relay['transfer_health'])]:
                run('docker','cp',client+':'+path,str(a.output/name))
            # Fixed command rejects shell commands even with the authorized key.
            import importlib.util
            spec=importlib.util.spec_from_file_location('wire',ROOT/'tools/daily-status-transfer.py')
            wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
            cmd=wire.command(relay);cmd[-1]='id'
            ok(execute(client,*cmd,user='owr-relay',check=False).returncode!=0,'arbitrary SSH command refused')
            ok(original=={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()},'original generated source unchanged')
    finally:
        for host in reversed(created):run('docker','rm','-f','-v',host)
        if network_created:run('docker','network','rm',network)
    result=dict(passed=True,checks=checks,containers_removed=True,real_ssh=True,periodic_updates=len(stamps),s3_calls=0,production_changed=False)
    (a.output/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=='__main__':main()
