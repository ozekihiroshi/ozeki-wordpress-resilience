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
    prefix='owr-observer-relay-ui-'+secrets.token_hex(5);db=prefix+'-db';web=prefix+'-web';browser=prefix+'-browser';created=[];checks=[]
    try:
        with tempfile.TemporaryDirectory(prefix='owr-observer-relay-ui-') as temp:
            work=Path(temp);work.chmod(0o755)
            requests=work/'requests';requests.mkdir(mode=0o770)
            plugin=work/'plugin';(plugin/'src').mkdir(parents=True)
            shutil.copy2(ROOT/'ozeki-wordpress-resilience.php',plugin/'ozeki-wordpress-resilience.php')
            shutil.copy2(ROOT/'src/NotificationAdmin.php',plugin/'src/NotificationAdmin.php')
            shutil.copy2(ROOT/'src/ObserverAdmin.php',plugin/'src/ObserverAdmin.php')
            shutil.copy2(ROOT/'src/DailyAdmin.php',plugin/'src/DailyAdmin.php')
            shutil.copy2(ROOT/'src/DailyWatchdogAdmin.php',plugin/'src/DailyWatchdogAdmin.php')
            shutil.copy2(ROOT/'src/ObserverSettings.php',plugin/'src/ObserverSettings.php')
            for n in ('PreflightAdmin.php','PreflightWatchdogAdmin.php'):shutil.copy2(ROOT/'src'/n,plugin/'src'/n)
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
    prefix='owr-preflight-observer-vm-'+secrets.token_hex(5);network=prefix;created=[];checks=[];events=[]
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
    def readstatus(name):
        p=ex(hosts['relay'],'cat','/web/'+name,check=False)
        if p.returncode:raise FileNotFoundError(name)
        return p.stdout
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
        response=run('docker','exec',browser,'python3','/lab/preflight-observer-relay-vm-browser.py',label,json.dumps(dict(source=source,receiver=receiver)),timeout=210)
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
        import shlex
        vmout=a.output/'vm';env=os.environ.copy();env.update(OWR_VM_LAB_OUTPUT=str(vmout),OWR_VM_OBSERVER=hosts['observer'],OWR_VM_REPORTS=str(status))
        hostboot=Path('/proc/sys/kernel/random/boot_id').read_text()
        p=subprocess.run(['python3',str(ROOT/'lab/observer-relay-vm/start.py')],env=env,capture_output=True,timeout=400)
        if p.returncode:raise RuntimeError('VM setup '+p.stderr.decode()[-1500:])
        vm=(vmout/'container-name').read_text();ssh=json.loads((vmout/'ssh-command.json').read_text())
        event('guest-booted')
        def remote(command,data=None,check=True,timeout=90):
            p=subprocess.run(['docker','exec',*(['-i'] if data is not None else []),vm,*ssh,command],input=data,capture_output=True,timeout=timeout)
            if check and p.returncode:raise RuntimeError(p.stderr.decode()[-1500:]+p.stdout.decode()[-1000:])
            return p
        def write(path,value,mode=0o600,owner=None):
            code='from pathlib import Path;import sys,subprocess;p=Path('+repr(path)+');p.write_bytes(sys.stdin.buffer.read());p.chmod('+str(mode)+')'
            if owner:code+=';subprocess.run(["chown",'+repr(owner)+',str(p)],check=True)'
            remote('sudo python3 -c '+shlex.quote(code),value.encode() if isinstance(value,str) else json.dumps(value).encode())
        setup="""set -eu
sudo mkdir -p /opt/owr /etc/owr /var/lib/owr-observer-relay /var/lib/owr-status-web
sudo tar -xf /tmp/payload.tar -C /opt/owr --strip-components=1
sudo useradd --system --no-create-home --shell /usr/sbin/nologin owr-relay
sudo chown owr-relay:www-data /var/lib/owr-observer-relay
sudo chmod 700 /var/lib/owr-observer-relay
echo 'reports /var/lib/owr-status-web 9p trans=virtio,version=9p2000.L 0 0' | sudo tee -a /etc/fstab >/dev/null
sudo mount /var/lib/owr-status-web
sudo chown owr-relay:www-data /var/lib/owr-status-web
sudo chmod 2755 /var/lib/owr-status-web
sudo chown -R root:root /opt/owr
sudo find /opt/owr -type d -exec chmod 755 {} +
sudo find /opt/owr -type f -exec chmod 644 {} +
sudo cp /opt/owr/examples/observer-status-relay/owr-observer-status@.service /etc/systemd/system/
"""
        remote(setup)
        for role in ('source','receiver'):
            base='/var/lib/owr-observer-relay/'+role
            write(base+'-key',(a.output/(role+'-relay')).read_text(),owner='owr-relay:www-data')
            write(base+'-known','owr-notification-generated-first-site '+(a.output/'observer-host.pub').read_text(),owner='owr-relay:www-data')
            cfg=dict(site_id='generated-first-site',monitor_id='preflight-'+role,host='10.0.2.2',user='ingress',port=2222,identity_file=base+'-key',known_hosts=base+'-known',status_file='/var/lib/owr-status-web/'+role+'.json',transfer_health='/var/lib/owr-status-web/'+role+'-transfer.json',lock_file=base+'-pull.lock',loop_lock=base+'-loop.lock')
            write('/etc/owr/observer-'+role+'.json',cfg,0o640,'root:www-data')
        units='owr-observer-status@source owr-observer-status@receiver'
        remote('sudo systemctl daemon-reload && sudo systemctl enable --now '+units)
        def stamps():return {r:val(r)['observed_at'] for r in ('source','receiver')}
        def boot():
            try:return remote('cat /proc/sys/kernel/random/boot_id',check=False,timeout=12).stdout.decode().strip()
            except subprocess.TimeoutExpired:return ''
        def verify(label):
            info={}
            for role in ('source','receiver'):
                unit='owr-observer-status@'+role
                raw=remote('systemctl show '+unit+' --property=ActiveState,SubState,UnitFileState,User,Group,NoNewPrivileges,ProtectSystem,ProtectHome,PrivateTmp,MainPID').stdout.decode()
                props=dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
                for key,want in [('ActiveState','active'),('SubState','running'),('UnitFileState','enabled'),('User','owr-relay'),('Group','www-data'),('NoNewPrivileges','yes'),('ProtectSystem','strict'),('ProtectHome','yes'),('PrivateTmp','yes')]:assert props[key]==want,(key,props)
                assert remote('sudo -u www-data test -w /var/lib/owr-status-web/'+role+'.json',check=False).returncode!=0
                assert remote('sudo -u www-data test -r /var/lib/owr-observer-relay/'+role+'-key',check=False).returncode!=0
                assert remote('sudo runuser -u owr-relay -g www-data -- python3 /opt/owr/tools/observer-status-relay.py --config /etc/owr/observer-'+role+'.json --interval 0',check=False).returncode!=0
                info[role]=props
            (a.output/(label+'.json')).write_text(json.dumps(info,indent=2));ok(True,label+' service identity hardening permissions and duplicate rejection')
        # Poll through the dedicated relay-container mount only as a read-only test observer.
        await_test(lambda:all(health(r)=='ok' for r in ('source','receiver')),'systemd starts real pinned SSH pulls',180)
        initial=stamps();await_test(lambda:all(stamps()[r]!=initial[r] for r in initial),'both unmodified 60-second services update periodically',180)
        verify('before-stop')
        # Create real alarm/recovery history to prove it survives relay restart and OS reboot.
        stop(hosts['source'],'source');await_test(lambda:'monitor_stopped' in val('source')['targets']['watchdog']['active'],'source alarm reaches VM through service',180)
        start(hosts['source'],'publish','source');await_test(lambda:not val('source')['targets']['watchdog']['active'],'source recovery reaches VM through service',180)
        history=val('source')['history']
        ok(not any(e.get('kind')=='heartbeat_invalid' for e in history),'no publication-window false alarm')
        with ui_session(status) as (web,browser):
            time.sleep(8);screen(browser,'systemd-running',expected(text=['発生','解消']),expected())
            remote('sudo systemctl stop '+units);event('services-stopped')
            frozen={name:readstatus(name) for name in ('source.json','receiver.json','source-transfer.json','receiver-transfer.json')};t0=time.monotonic()
            while time.monotonic()-t0<310:
                time.sleep(10);assert all(readstatus(k)==v for k,v in frozen.items());print('STOPPED_SECONDS '+str(round(time.monotonic()-t0)),flush=True)
            screen(browser,'systemd-stopped',expected('stale','stopped'),expected('stale','stopped'))
            old=stamps();remote('sudo systemctl start '+units)
            await_test(lambda:all(health(r)=='ok' and stamps()[r]!=old[r] for r in old),'explicit service restart refreshes reports',180)
            screen(browser,'systemd-resumed',expected(text=['発生','解消']),expected());verify('before-reboot')
            before=boot();old=stamps();event('guest-reboot-requested',boot_id=before)
            remote('sudo systemctl reboot',check=False,timeout=15)
            await_test(lambda:bool(boot()) and boot()!=before,'guest OS reboot changes Boot ID',240)
            await_test(lambda:all(health(r)=='ok' and stamps()[r]!=old[r] for r in old),'enabled services automatically refresh both reports after reboot',180)
            verify('after-reboot');screen(browser,'systemd-reboot-recovered',expected(text=['発生','解消']),expected())
            ok(all(e in val('source')['history'] for e in history),'alarm and recovery history survives service and OS restart')
            ok(Path('/proc/sys/kernel/random/boot_id').read_text()==hostboot,'WSL observation host not rebooted')
            event('guest-reboot-verified',boot_id=boot())
            (a.output/'service-journal.txt').write_bytes(remote('sudo journalctl -u owr-observer-status@source -u owr-observer-status@receiver --no-pager -n 100').stdout)
            (a.output/'units.txt').write_bytes(remote('systemctl cat '+units).stdout)
            remote('sudo systemctl poweroff',check=False,timeout=15)
    except Exception as e:
        event('failed',error=str(e));raise
    finally:
        vmfile=a.output/'vm/container-name'
        if vmfile.exists():
            vm=vmfile.read_text();assert vm.startswith('owr-production-vm-') and vm.replace('-','').isalnum()
            run('docker','rm','-f','-v',vm,check=False)
        if hosts['relay'] in created:ex(hosts['relay'],'chown','-R',str(os.getuid())+':'+str(os.getgid()),'/web',check=False)
        for host in reversed(created):run('docker','rm','-f','-v',host,check=False)
        run('docker','network','rm',network,check=False)
    (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,events=events,resources_removed=True,interval_seconds=60,real_guest_reboot=True,host_unchanged=True,scope='Dedicated Ubuntu VM runs production systemd template; external independent observer; real SSH; generated preflight reports; WordPress reads guest output through dedicated9p test share; no S3/production/72h observation changes'),indent=2))
    print('ALL_PASS',flush=True)
if __name__=='__main__':main()
