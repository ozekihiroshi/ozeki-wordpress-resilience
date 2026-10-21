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
    prefix='owr-preflight-observer-ui-'+secrets.token_hex(5);db=prefix+'-db';web=prefix+'-web';browser=prefix+'-browser';created=[];checks=[]
    try:
        with tempfile.TemporaryDirectory(prefix='owr-preflight-observer-ui-') as temp:
            work=Path(temp);work.chmod(0o755)
            requests=work/'requests';requests.mkdir(mode=0o770)
            plugin=work/'plugin';(plugin/'src').mkdir(parents=True)
            shutil.copy2(ROOT/'ozeki-wordpress-resilience.php',plugin/'ozeki-wordpress-resilience.php')
            shutil.copy2(ROOT/'src/NotificationAdmin.php',plugin/'src/NotificationAdmin.php')
            shutil.copy2(ROOT/'src/ObserverAdmin.php',plugin/'src/ObserverAdmin.php')
            shutil.copy2(ROOT/'src/DailyAdmin.php',plugin/'src/DailyAdmin.php')
            shutil.copy2(ROOT/'src/DailyWatchdogAdmin.php',plugin/'src/DailyWatchdogAdmin.php')
            shutil.copy2(ROOT/'src/ObserverSettings.php',plugin/'src/ObserverSettings.php')
            shutil.copy2(ROOT/'src/PreflightAdmin.php',plugin/'src/PreflightAdmin.php')
            shutil.copy2(ROOT/'src/PreflightWatchdogAdmin.php',plugin/'src/PreflightWatchdogAdmin.php')
            observer_requests=requests/'observer';observer_requests.mkdir(mode=0o770)
            password=secrets.token_hex(24);env=work/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("OWR_PREFLIGHT_WATCHDOG_REPORTS",["source"=>["path"=>"/status/source.json","monitor_id"=>"preflight-source","transfer_file"=>"/status/source-transfer.json"],"receiver"=>["path"=>"/status/receiver.json","monitor_id"=>"preflight-receiver","transfer_file"=>"/status/receiver-transfer.json"]]); define("OWR_DAILY_TRANSFER_FILE","/status/transfer.json"); define("OWR_DAILY_STATUS_FILE","/status/daily.json"); define("OWR_PREFLIGHT_SITE_ID","generated-first-site"); define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true); define("OWR_NOTIFICATION_STATUS_FILE","/status/status.json"); define("OWR_NOTIFICATION_REQUEST_DIR","/requests");\n');env.chmod(0o600)
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

def main():
    import hashlib
    from datetime import datetime,timezone
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    prefix='owr-preflight-observer-wire-'+secrets.token_hex(5);network=prefix;created=[];checks=[];events=[]
    hosts={k:prefix+'-'+k for k in ('source','receiver','observer','relay')}
    status=a.output/'web-status';status.mkdir(mode=0o755)
    def ex(host,*args,check=True,**kw):return run('docker','exec',host,*args,check=check,**kw)
    def ok(v,label):
        if not v:raise AssertionError(label)
        checks.append(label);print('PASS '+label,flush=True)
    def event(label,**kw):
        events.append(dict(event=label,at=datetime.now(timezone.utc).isoformat(),**kw));(a.output/'events.json').write_text(json.dumps(events,indent=2));print('EVENT '+label,flush=True)
    def put(host,path,value,mode='644',owner='root:root'):
        tmp=a.output/'upload';tmp.write_text(value if isinstance(value,str) else json.dumps(value));tmp.chmod(0o600)
        run('docker','cp',str(tmp),host+':'+path);ex(host,'chown',owner,path);ex(host,'chmod',mode,path);tmp.unlink()
    def start(host,mode,role):
        run('docker','exec','-d','-u','worker',host,'python3','/opt/lab/worker.py',mode,role)
    def stop(host,role):ex(host,'kill','-TERM',ex(host,'cat','/data/'+role+'.pid').stdout.decode().strip())
    def readstatus(name):return ex(hosts['relay'],'cat','/web/'+name).stdout
    def val(role):return json.loads(readstatus(role+'.json'))
    def await_test(fn,label,seconds=80):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            try:
                if fn():ok(True,label);return
            except (FileNotFoundError,json.JSONDecodeError):pass
            time.sleep(2)
        raise AssertionError(label)
    def health(role):return json.loads(readstatus(role+'-transfer.json'))['state']
    def relay_start(role):
        run('docker','exec','-d','-u','worker',hosts['relay'],'sh','-c','echo $$ > /data/'+role+'.pid; exec python3 /opt/owr/tools/observer-status-relay.py --config /data/'+role+'.json --interval 2')
    def screen(browser,label,source,receiver):
        response=run('docker','exec',browser,'python3','/lab/preflight-observer-relay-browser.py',label,json.dumps(dict(source=source,receiver=receiver)),timeout=120)
        event(label,browser=json.loads(response.stdout));run('docker','cp',browser+':/tmp/relay-'+label+'.png',str(a.output/(label+'.png')))
    def expected(report='current',transfer='ok',text=None):return dict(report=report,transfer=transfer,text=text or [])
    try:
        ids=run('docker','network','ls','-q').stdout.decode().split()
        used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in (n['IPAM'].get('Config') or []) if c.get('Subnet')]
        for route in json.loads(run('ip','-j','route').stdout):
            if route.get('dst') and route['dst']!='default':used.append(ipaddress.ip_network(route['dst'],strict=False))
        subnet=next(ipaddress.ip_network('10.253.'+str(i)+'.0/28') for i in range(256) if not any(ipaddress.ip_network('10.253.'+str(i)+'.0/28').overlaps(n) for n in used))
        run('docker','network','create','--internal','--subnet',str(subnet),network)
        for role,host in hosts.items():
            run('docker','run','-d','--name',host,'--network',network,'--memory','384m','-v',str(ROOT/'tools')+':/opt/owr/tools:ro','-v',str(ROOT/'schemas')+':/opt/owr/schemas:ro','-v',str(ROOT/'lab/preflight-observer-relay')+':/opt/lab:ro',*(['-v',str(status)+':/web'] if role=='relay' else []),'--entrypoint','sleep',IMAGE,'infinity');created.append(host)
            ex(host,'useradd','-m','-g','33','-s','/bin/sh','worker');ex(host,'useradd','-m','-g','33','-s','/bin/sh','ingress');ex(host,'usermod','-p','*','ingress')
            ex(host,'mkdir','-p','/data','/public','/etc/owr','/run/sshd');ex(host,'chown','worker:33','/data','/public');ex(host,'chmod','700','/data');ex(host,'chmod','2750','/public')
            if role=='relay':ex(host,'chown','worker:33','/web');ex(host,'chmod','2755','/web')
            key=a.output/(role+'-host');run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(key));run('docker','cp',str(key),host+':/etc/owr/host');ex(host,'chmod','600','/etc/owr/host')
            cfg='\n'.join(['Port 2222','HostKey /etc/owr/host','PidFile /run/sshd/pid','AuthorizedKeysFile /etc/owr/keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','AllowUsers ingress','DisableForwarding yes','PermitTTY no'])+'\n'
            put(host,'/etc/owr/sshd',cfg)
        for role in ('source','receiver'):
            key=a.output/(role+'-probe');run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(key))
            put(hosts[role],'/etc/owr/probe.json',dict(site_id='generated-first-site',monitor_id='preflight-'+role,report_file='/public/report.json',health_file='/public/health.json',config_sha256='a'*64))
            put(hosts[role],'/etc/owr/keys','restrict,command="python3 /opt/owr/tools/preflight-watchdog-probe.py --config /etc/owr/probe.json" '+key.with_suffix('.pub').read_text())
            ex(hosts[role],'/usr/sbin/sshd','-f','/etc/owr/sshd');start(hosts[role],'publish',role)
            put(hosts['observer'],'/data/'+role+'-key',key.read_text(),'600','worker:33')
            put(hosts['observer'],'/data/'+role+'-known','owr-notification-preflight-'+role+' '+(a.output/(role+'-host.pub')).read_text(),'600','worker:33')
            cfg=dict(monitor_id='preflight-'+role,state='/data/'+role+'-state',stale_after_seconds=20,admin_site_id='generated-first-site',public_status_file='/public/'+role+'.json',ssh=dict(site_id='preflight-'+role,host=hosts[role],user='ingress',port=2222,identity_file='/data/'+role+'-key',known_hosts='/data/'+role+'-known'))
            put(hosts['observer'],'/data/'+role+'.json',cfg,'600','worker:33');start(hosts['observer'],'observe',role)
        keys=[]
        for role in ('source','receiver'):
            key=a.output/(role+'-relay');run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(key))
            keys.append('restrict,command="python3 /opt/owr/tools/observer-status.py endpoint --config /etc/owr/'+role+'.json" '+key.with_suffix('.pub').read_text())
            put(hosts['observer'],'/etc/owr/'+role+'.json',dict(site_id='generated-first-site',public_status_file='/public/'+role+'.json'))
            put(hosts['relay'],'/data/'+role+'-key',key.read_text(),'600','worker:33')
            put(hosts['relay'],'/data/'+role+'-known','owr-notification-generated-first-site '+(a.output/'observer-host.pub').read_text(),'600','worker:33')
            cfg=dict(site_id='generated-first-site',monitor_id='preflight-'+role,host=hosts['observer'],user='ingress',port=2222,identity_file='/data/'+role+'-key',known_hosts='/data/'+role+'-known',status_file='/web/'+role+'.json',transfer_health='/web/'+role+'-transfer.json',lock_file='/data/'+role+'-pull.lock',loop_lock='/data/'+role+'-loop.lock')
            put(hosts['relay'],'/data/'+role+'.json',cfg,'600','worker:33')
        put(hosts['observer'],'/etc/owr/keys','\n'.join(keys));ex(hosts['observer'],'/usr/sbin/sshd','-f','/etc/owr/sshd')
        for role in ('source','receiver'):relay_start(role)
        await_test(lambda:all(health(r)=='ok' for r in ('source','receiver')),'both actual observer reports arrive through pinned SSH')
        for role in ('source','receiver'):
            ok(ex(hosts['relay'],'runuser','-u','www-data','--','test','-w','/web/'+role+'.json',check=False).returncode!=0,role+' WordPress cannot write report')
            ok(ex(hosts['relay'],'runuser','-u','www-data','--','test','-r','/data/'+role+'-key',check=False).returncode!=0,role+' WordPress cannot read relay key')
            ok(ex(hosts['relay'],'runuser','-u','worker','--','python3','/opt/owr/tools/observer-status-relay.py','--config','/data/'+role+'.json','--interval','0',check=False).returncode!=0,role+' duplicate loop refused')
        with ui_session(status) as (web,browser):
            time.sleep(8)
            screen(browser,'healthy',expected(),expected())
            # A real monitored source stops publishing; observer and report transfer continue.
            stop(hosts['source'],'source');event('source-publisher-stopped')
            await_test(lambda:'monitor_stopped' in val('source')['targets']['watchdog']['active'],'actual source update stop becomes alarm')
            screen(browser,'source-alarm',expected(text=['期限超過','発生']),expected())
            start(hosts['source'],'publish','source')
            await_test(lambda:not val('source')['targets']['watchdog']['active'],'source recovers after real fresh update')
            screen(browser,'source-recovered',expected(text=['解消']),expected())
            # Actual relay network isolation: last valid reports remain byte-identical.
            run('docker','network','disconnect',network,hosts['relay']);event('relay-network-disconnected')
            await_test(lambda:all(health(r)=='transfer_failed' for r in ('source','receiver')),'SSH outage recorded without replacing snapshots')
            frozen={r:readstatus(r+'.json') for r in ('source','receiver')}
            screen(browser,'transfer-failed',expected(transfer='transfer_failed'),expected(transfer='transfer_failed'))
            started=time.monotonic()
            while any(time.time()-datetime.fromisoformat(json.loads(v)['observed_at']).timestamp()<305 for v in frozen.values()):
                time.sleep(10)
                assert all(readstatus(r+'.json')==v for r,v in frozen.items())
                print('WAIT_TRANSFER_STALE '+str(round(time.monotonic()-started)),flush=True)
            screen(browser,'transfer-stale',expected('stale','transfer_failed'),expected('stale','transfer_failed'))
            run('docker','network','connect',network,hosts['relay']);event('relay-network-restored')
            await_test(lambda:all(health(r)=='ok' for r in ('source','receiver')),'periodic transfer recovers without restart')
            screen(browser,'transfer-recovered',expected(),expected())
            # Stop one observer; stop other pull loop concurrently to distinguish both paths.
            stop(hosts['observer'],'source');stop(hosts['relay'],'receiver');event('source-observer-and-receiver-pull-stopped')
            source_frozen=ex(hosts['observer'],'cat','/public/source.json').stdout
            receiver_frozen=readstatus('receiver-transfer.json');started=time.monotonic()
            while time.monotonic()-started<310:
                time.sleep(10)
                assert source_frozen==ex(hosts['observer'],'cat','/public/source.json').stdout
                assert receiver_frozen==readstatus('receiver-transfer.json')
                print('WAIT_STOPPED '+str(round(time.monotonic()-started)),flush=True)
            await_test(lambda:health('source')=='source_stale','SSH reachable but observer report is stale')
            screen(browser,'stopped',expected('stale','source_stale'),expected('stale','stopped'))
            start(hosts['observer'],'observe','source');relay_start('receiver')
            await_test(lambda:all(health(r)=='ok' for r in ('source','receiver')),'observer and pull restart recover both targets')
            screen(browser,'final-recovered',expected(text=['発生','解消']),expected())
            notifications=ex(hosts['observer'],'cat','/data/notifications.jsonl').stdout.decode().splitlines()
            ok(any(json.loads(x)['transition']=='opened' for x in notifications) and any(json.loads(x)['transition']=='resolved' for x in notifications),'actual observer alarm/recovery dispatch recorded locally')
            ok(not any(json.loads(x)['kind']=='heartbeat_invalid' for x in notifications),'no publication-window invalid alerts in real run')
            (a.output/'notifications.json').write_text(json.dumps([json.loads(x) for x in notifications],indent=2))
    except Exception as e:
        event('failed',error=str(e));raise
    finally:
        if hosts['relay'] in created:ex(hosts['relay'],'chown','-R',str(os.getuid())+':'+str(os.getgid()),'/web',check=False)
        for host in reversed(created):run('docker','rm','-f','-v',host,check=False)
        run('docker','network','rm',network,check=False)
    (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,events=events,containers_removed=True,scope='Dedicated containers, real SSH and observer, local notification callback, real 5-minute freshness waits; no S3/production or 72h observation changes'),indent=2))
    print('ALL_PASS',flush=True)
if __name__=='__main__':main()
