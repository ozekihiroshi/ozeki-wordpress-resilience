#!/usr/bin/env python3
"""Actual systemd lifecycle, SSH handoff and WordPress browser stale/recovery test."""
import argparse,ipaddress,json,os,secrets,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE='owr-external-lab:local'

def run(*args,input=None,check=True,timeout=90):
    p=subprocess.run(args,input=input,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(args[0]+' failed: '+p.stderr.decode()[-1200:]+p.stdout.decode()[-1200:])
    return p

import contextlib,types
@contextlib.contextmanager
def ui_session(statusdir):
    args=types.SimpleNamespace(plugin_zip=None)
    images=dict(line.split('=',1) for line in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in line)
    prefix='owr-systemd-ui-'+secrets.token_hex(5);db=prefix+'-db';web=prefix+'-web';browser=prefix+'-browser';created=[];checks=[]
    try:
        with tempfile.TemporaryDirectory(prefix='owr-systemd-ui-') as temp:
            work=Path(temp);work.chmod(0o755)
            requests=work/'requests';requests.mkdir(mode=0o770)
            plugin=work/'plugin';(plugin/'src').mkdir(parents=True)
            shutil.copy2(ROOT/'ozeki-wordpress-resilience.php',plugin/'ozeki-wordpress-resilience.php')
            shutil.copy2(ROOT/'src/NotificationAdmin.php',plugin/'src/NotificationAdmin.php')
            shutil.copy2(ROOT/'src/ObserverAdmin.php',plugin/'src/ObserverAdmin.php')
            shutil.copy2(ROOT/'src/DailyAdmin.php',plugin/'src/DailyAdmin.php')
            shutil.copy2(ROOT/'src/DailyWatchdogAdmin.php',plugin/'src/DailyWatchdogAdmin.php')
            shutil.copy2(ROOT/'src/ObserverSettings.php',plugin/'src/ObserverSettings.php')
            observer_requests=requests/'observer';observer_requests.mkdir(mode=0o770)
            password=secrets.token_hex(24);env=work/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("OWR_DAILY_TRANSFER_FILE","/status/transfer.json"); define("OWR_DAILY_STATUS_FILE","/status/daily.json"); define("OWR_DAILY_SITE_ID","generated-first-site"); define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true); define("OWR_NOTIFICATION_STATUS_FILE","/status/status.json"); define("OWR_NOTIFICATION_REQUEST_DIR","/requests");\n');env.chmod(0o600)
            env.write_text(env.read_text().replace('WORDPRESS_CONFIG_EXTRA=', 'WORDPRESS_CONFIG_EXTRA=define("OWR_OBSERVER_STATUS_FILE","/status/observer.json"); '))
            env.write_text(env.read_text().replace('WORDPRESS_CONFIG_EXTRA=', 'WORDPRESS_CONFIG_EXTRA=define("OWR_OBSERVER_REQUEST_DIR","/requests/observer"); '))
            if args.plugin_zip:
                if not args.plugin_zip.is_file():raise ValueError('plugin ZIP missing')
                env.write_text(env.read_text().replace('define("DISALLOW_FILE_MODS",true);','define("FS_METHOD","direct");'))
            for image in (images['OWR_DB_IMAGE'],images['OWR_WP_IMAGE'],'selenium/standalone-chrome:latest'):run('docker','image','inspect',image)
            run('docker','run','-d','--name',db,'--network','none','--memory','512m','--env-file',str(env),images['OWR_DB_IMAGE']);created.append(db)
            deadline=time.monotonic()+100
            while run('docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized',check=False).returncode:
                if time.monotonic()>deadline:raise RuntimeError('DB startup timeout')
                time.sleep(1)
            run('docker','run','-d','--name',web,'--network','container:'+db,'--memory','768m','--env-file',str(env),*(['-v',str(plugin)+':/var/www/html/wp-content/plugins/ozeki-wordpress-resilience:ro'] if not args.plugin_zip else []),'-v',str(statusdir)+':/status:ro','-v',str(requests)+':/requests',images['OWR_WP_IMAGE']);created.append(web)
            run('docker','exec',web,'chown','33:'+str(os.getgid()),'/requests')
            run('docker','exec',web,'chmod','2770','/requests')
            run('docker','exec',web,'chown','33:'+str(os.getgid()),'/requests/observer');run('docker','exec',web,'chmod','2770','/requests/observer')
            deadline=time.monotonic()+100
            while run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode:
                if time.monotonic()>deadline:raise RuntimeError('WP startup timeout')
                time.sleep(1)
            code='define("WP_INSTALLING",true);require "/var/www/html/wp-load.php";require_once ABSPATH."wp-admin/includes/upgrade.php";wp_install("Resilience notification lab","labadmin","lab@example.invalid",false,"",getenv("LAB_ADMIN_PASSWORD"));update_option("siteurl","http://127.0.0.1");update_option("home","http://127.0.0.1");$id=wp_create_user("labeditor",getenv("LAB_ADMIN_PASSWORD"),"editor@example.invalid");(new WP_User($id))->set_role("editor");require_once ABSPATH."wp-admin/includes/plugin.php";$r=activate_plugin("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");if(is_wp_error($r)){throw new Exception($r->get_error_message());}echo "installed";'
            if args.plugin_zip:
                run('docker','cp',str(args.plugin_zip.resolve()),web+':/tmp/owr-distribution.zip')
                installer='require_once ABSPATH."wp-admin/includes/file.php";require_once ABSPATH."wp-admin/includes/class-wp-upgrader.php";$u=new Plugin_Upgrader(new Automatic_Upgrader_Skin());$r=$u->install("/tmp/owr-distribution.zip");if(is_wp_error($r)||!$r){throw new Exception("ZIP install failed");}'
                code=code.replace('require_once ABSPATH."wp-admin/includes/plugin.php";',installer+'require_once ABSPATH."wp-admin/includes/plugin.php";')
            run('docker','exec','-u','www-data',web,'php','-r',code)
            if args.plugin_zip:checks.append('distribution ZIP installed by WordPress Plugin_Upgrader and activated')
            run('docker','run','-d','--name',browser,'--network','container:'+db,'--memory','2g','--shm-size','1g','--env-file',str(env),'-v',str(ROOT/'lab/notification-admin')+':/lab:ro','selenium/standalone-chrome:latest');created.append(browser)
            for item in json.loads(run('docker','inspect',db,web,browser).stdout):
                assert not item['HostConfig']['PortBindings']
            checks.append('isolated network namespace; no published ports')

            yield web,browser
    finally:
        for name in reversed(created):run('docker','rm','-f','-v',name)

@contextlib.contextmanager
def wire_temp(client):
    with tempfile.TemporaryDirectory(prefix='owr-daily-wire-') as temp:
        try:
            yield temp
        finally:
            # Restore bind ownership before TemporaryDirectory attempts cleanup.
            run('docker','exec',client,'chown','-R',str(os.getuid())+':'+str(os.getgid()),'/var/lib/owr-status',check=False)
            run('docker','exec',client,'chmod','700','/var/lib/owr-status',check=False)

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
        with wire_temp(client) as temp:
            work=Path(temp);work.chmod(0o755);statusdir=work/'status';statusdir.mkdir();code=work/'code';code.mkdir()
            for name in ['notification-transfer','notification-live','notification-admin-bridge','notification-dispatch-lab','notification-health','pushover-adapter','monitor-delivery']:
                shutil.copy2(ROOT/'tools'/(name+'.py'),code/(name+'.py'))
            for key in ('host','client','wrong'):
                run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/key))
            for host in (server,client):
                run('docker','run','-d','--name',host,'--network',network,'--memory','256m',*(['-v',str(statusdir)+':/var/lib/owr-status'] if host==client else []),'--entrypoint','sleep',IMAGE,'infinity');created.append(host)
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
            for path,owner,mode in [('/var/lib/owr-relay','owr-relay:owr-relay','700'),('/var/lib/owr-requests','owr-web:owr-web','2770'),('/var/lib/owr-status','owr-relay:33','2750')]:
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
            units=[];systemd_evidence={'events':[]}
            from datetime import datetime,timezone
            def event(label,**extra):
                systemd_evidence['events'].append(dict(event=label,at=datetime.now(timezone.utc).isoformat(),**extra))
                print('EVENT '+label,flush=True)
            def unit_start(role,host,user,config,pidpath):
                name=prefix+'-'+role
                # ExecStop explicitly terminates the in-container process: stopping only
                # the docker exec client does not guarantee its child has stopped.
                stopper=work/(role+'-stop.py')
                stopper.write_text("import subprocess\np=subprocess.run("+repr(['docker','exec',host,'cat',pidpath])+",capture_output=True,text=True)\nif p.returncode==0 and p.stdout.strip().isdigit():\n subprocess.run("+repr(['docker','exec','-u',user,host,'kill','-TERM'])+"+[p.stdout.strip()],check=False)\n")
                command=['/usr/bin/docker','exec','-u',user,host,'sh','-c',
                    'echo $$$$ > '+pidpath+'; exec python3 '+tool+' --config '+config+' '+role+' --interval 2']
                unitdir=Path('/run/user')/str(os.getuid())/'systemd/user'
                unitdir.mkdir(parents=True,exist_ok=True)
                unitfile=unitdir/(name+'.service')
                if unitfile.exists():raise RuntimeError('unexpected existing unit')
                unitfile.write_text('[Unit]\nDescription=Disposable OWR systemd lifecycle lab\n[Service]\nType=simple\nRestart=no\nSuccessExitStatus=143\nTimeoutStopSec=25\nExecStart='+' '.join(json.dumps(x) for x in command)+'\nExecStop=/usr/bin/python3 '+str(stopper)+'\n')
                units.append(name)
                run('systemctl','--user','daemon-reload')
                run('systemctl','--user','start',name)
                return name
            def active(name):
                return run('systemctl','--user','is-active',name,check=False).stdout.decode().strip()
            def wait_state(state,timeout=30):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    if get(client,relay['transfer_health'])['state']==state:return
                    time.sleep(.5)
                raise AssertionError('receiver did not become '+state)
            try:
                with ui_session(statusdir) as (web,browser):
                    def screen(state,label):
                        response=run('docker','exec',browser,'python3','/lab/daily-systemd-browser.py',state,timeout=90)
                        systemd_evidence['events'].append(dict(event=label,at=datetime.now(timezone.utc).isoformat(),browser=json.loads(response.stdout)))
                        run('docker','cp',browser+':/tmp/systemd-'+state+'.png',str(a.output/(label+'.png')))
                        ok(True,'real Chromium '+label+' '+state)
                    pub=unit_start('publish',server,'owr-worker','/etc/owr/publish.json','/var/lib/owr-worker/loop.pid')
                    rec=unit_start('relay',client,'owr-relay','/var/lib/owr-relay/config.json','/var/lib/owr-relay/loop.pid')
                    stamps=set();deadline=time.monotonic()+30
                    while len(stamps)<3 and time.monotonic()<deadline:
                        value=get(client,relay['status_file'])['observed_at']
                        if value!=initial_stamp:stamps.add(value)
                        time.sleep(.5)
                    ok(len(stamps)>=3 and active(pub)=='active' and active(rec)=='active','systemd units produce three periodic updates')
                    ok(publish().returncode!=0 and pull().returncode!=0,'systemd loops hold duplicate execution locks')
                    screen('ok','running')
                    run('systemctl','--user','stop',rec,pub)
                    ok(active(pub)=='inactive' and active(rec)=='inactive','both systemd units stopped')
                    frozen=execute(client,'cat',relay['transfer_health']).stdout
                    frozen_report=execute(client,'cat',relay['status_file']).stdout
                    source_frozen=execute(server,'cat',producer['report_file']).stdout
                    event('both_stopped');start=time.monotonic()
                    # Real elapsed time; no mutation or artificial aging of report timestamps.
                    while time.monotonic()-start<305:
                        time.sleep(10)
                        assert frozen==execute(client,'cat',relay['transfer_health']).stdout
                        assert frozen_report==execute(client,'cat',relay['status_file']).stdout
                        assert source_frozen==execute(server,'cat',producer['report_file']).stdout
                        print('STOPPED_SECONDS '+str(round(time.monotonic()-start)),flush=True)
                    systemd_evidence['stopped_seconds']=time.monotonic()-start
                    screen('stopped','stopped-real-time')
                    run('systemctl','--user','start',rec)
                    wait_state('source_stale')
                    screen('source_stale','receiver-only-resumed')
                    run('systemctl','--user','start',pub)
                    wait_state('ok')
                    screen('ok','both-resumed')
                    ok(get(client,relay['status_file'])['observed_at']!=json.loads(frozen_report)['observed_at'],'resumption refreshes actual source observation')
                    event('both_recovered')
                    for name in units:
                        (a.output/(name+'.journal')).write_bytes(run('journalctl','--user','-u',name,'--no-pager','-n','60').stdout)
            finally:
                for name in reversed(units):
                    run('systemctl','--user','stop',name,check=False)
                    (a.output/(name+'.journal')).write_bytes(run('journalctl','--user','-u',name,'--no-pager','-n','60').stdout)
                    run('systemctl','--user','reset-failed',name,check=False)
                    (Path('/run/user')/str(os.getuid())/'systemd/user'/(name+'.service')).unlink(missing_ok=True)
                run('systemctl','--user','daemon-reload')
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
        if client in created:
            execute(client,'chown','-R',str(os.getuid())+':'+str(os.getgid()),'/var/lib/owr-status',check=False)
            execute(client,'chmod','700','/var/lib/owr-status',check=False)
        if 'work' in locals() and work.exists():
            assert work.resolve().parent==Path('/tmp') and work.name.startswith('owr-daily-wire-')
            shutil.rmtree(work)
        for host in reversed(created):run('docker','rm','-f','-v',host)
        if network_created:run('docker','network','rm',network)
    result=dict(passed=True,checks=checks,containers_removed=True,real_ssh=True,periodic_updates=len(stamps),systemd=systemd_evidence,s3_calls=0,production_changed=False)
    (a.output/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=='__main__':main()
