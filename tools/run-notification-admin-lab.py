#!/usr/bin/env python3
"""Disposable real WordPress/MariaDB/Chromium notification admin integration lab."""
import argparse,hashlib,importlib.util,json,os,secrets,shutil,sqlite3,subprocess,tempfile,time
from pathlib import Path
from unittest.mock import MagicMock
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,timeout=90,check=True):
    p=subprocess.run(args,input=input,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError('Command failed: '+args[0]+' '+p.stderr.decode()[-1000:]+p.stdout.decode()[-1000:])
    return p
def module(name):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--plugin-zip',type=Path,help='Install this distribution using WordPress Plugin_Upgrader');args=parser.parse_args()
    if args.output.exists():raise ValueError('new output directory required')
    args.output.mkdir(parents=True)
    images=dict(line.split('=',1) for line in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in line)
    prefix='owr-notification-admin-'+secrets.token_hex(5);db=prefix+'-db';web=prefix+'-web';browser=prefix+'-browser';created=[];checks=[]
    print('LAB_RESOURCE_PREFIX '+prefix,flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix='owr-admin-') as temp:
            work=Path(temp);work.chmod(0o755);statusdir=work/'status';statusdir.mkdir(mode=0o755)
            requests=work/'requests';requests.mkdir(mode=0o770)
            plugin=work/'plugin';(plugin/'src').mkdir(parents=True)
            shutil.copy2(ROOT/'ozeki-wordpress-resilience.php',plugin/'ozeki-wordpress-resilience.php')
            shutil.copy2(ROOT/'src/NotificationAdmin.php',plugin/'src/NotificationAdmin.php')
            shutil.copy2(ROOT/'src/ObserverAdmin.php',plugin/'src/ObserverAdmin.php')
            shutil.copy2(ROOT/'src/ObserverSettings.php',plugin/'src/ObserverSettings.php')
            observer_requests=requests/'observer';observer_requests.mkdir(mode=0o770)
            password=secrets.token_hex(24);env=work/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true); define("OWR_NOTIFICATION_STATUS_FILE","/status/status.json"); define("OWR_NOTIFICATION_REQUEST_DIR","/requests");\n');env.chmod(0o600)
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
            def client(mode):
                p=run('docker','exec',browser,'python3','/lab/http-test.py',mode,timeout=120)
                result=json.loads(p.stdout);checks.extend(result);print(mode+': '+str(len(result))+' checks passed',flush=True)
            client('settings')
            run('docker','cp',browser+':/tmp/owr-settings.json',str(work/'settings.json'))
            settings=json.loads((work/'settings.json').read_text());bridge=module('notification-admin-bridge')
            source=work/'source.sqlite'
            with sqlite3.connect(source) as conn:
                conn.execute('CREATE TABLE outbox(payload TEXT)');conn.execute('INSERT INTO outbox VALUES(?)',(json.dumps(dict(event_id='a'*64,site='admin-lab',domain='daily',kind='backup_missing',subject='fixture',transition='opened',observed_at='2026-10-19T00:00:00+00:00')),))
            credentials=work/'credentials.json';credentials.write_text(json.dumps(dict(token='t'*30,user='u'*30)));credentials.chmod(0o600)
            profiles=dict(push_profile=dict(transport='pushover',credentials_file=str(credentials)),mail_profile=dict(transport='smtp_starttls',host='127.0.0.1',port=1025,**{'from':'lab@example.invalid'}))
            config,binding=bridge.compile_settings(settings,profiles,source,work/'delivery',include_existing=True)
            push=MagicMock();push.send.return_value={'receipt':'r'*30}
            push.poll.return_value=dict(acknowledged=False,expired=False)
            mail=MagicMock();mail.send.side_effect=bridge.dispatch.push.DeliveryError('rejected')
            bridge.dispatch.run(config,factory=lambda c:push if c['transport']=='pushover' else mail)
            report=bridge.status(config,binding,simulated=True)
            report['ignored_secret']='NEVER-RENDER-SECRET'
            def report_write(value):
                (statusdir/'status.json').write_text(json.dumps(value));(statusdir/'status.json').chmod(0o644)
            observer=module('watchdog-observer')
            from datetime import datetime,timezone,timedelta
            def observer_client(mode):
                response=run('docker','exec',browser,'python3','/lab/observer-http-test.py',mode,timeout=60)
                result=json.loads(response.stdout);checks.extend(result);print('observer '+mode+': '+str(len(result))+' checks passed',flush=True)
            observer_client('unavailable')
            oc=dict(state=str(work/'observer'),monitor_id='lab-watchdog',stale_after_seconds=1,ssh={},admin_site_id=settings['site_id'],public_status_file=str(statusdir/'observer.json'),alerts=dict(source_outbox=str(work/'observer-alerts.sqlite'),state=str(work/'observer-delivery'),channels=[config['channels'][0]]))
            oc['alerts']['channels']=[dict(config['channels'][0],kinds=['monitor_stopped','heartbeat_invalid','notification_delivery_failed'])]
            def transport(c,p):
                return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id='lab-watchdog',status='present',heartbeat=dict(format='owr-monitor-heartbeat-v1',monitor_id='lab-watchdog',completed_at=(datetime.now(timezone.utc)-timedelta(seconds=600)).isoformat(),undelivered=0,open_incidents=0))
            observer.observe(oc,transport=transport,factory=lambda c:mail)
            time.sleep(2)
            def disconnected(c,p):raise OSError('isolated fault')
            observer.observe(oc,transport=disconnected,factory=lambda c:mail)
            snapshot=json.loads((statusdir/'observer.json').read_text())
            snapshot['secret']='NEVER-RENDER-SECRET';snapshot['html']='<script>evil</script>'
            def observer_write(value):
                (statusdir/'observer.json').write_text(json.dumps(value));(statusdir/'observer.json').chmod(0o644)
            observer_write(snapshot);observer_client('current')
            stale=json.loads(json.dumps(snapshot));stale['observed_at']='2000-01-01T00:00:00+00:00'
            for target in stale['targets'].values():target['last_seen']=None
            stale['history']=[]
            observer_write(stale);observer_client('stale')
            observer_write(dict(snapshot,site_id='other'));observer_client('invalid')
            observer_write(dict(snapshot,observed_at='2099-01-01T00:00:00+00:00'));observer_client('future')
            negative=json.loads(json.dumps(snapshot));negative['delivery']['pending']=-1
            observer_write(negative);observer_client('negative')
            observer_write(dict(snapshot,extra='x'*40000));observer_client('oversize')
            def fresh(c,p):
                value=transport(c,p);value['heartbeat']['completed_at']=datetime.now(timezone.utc).isoformat();return value
            observer.observe(oc,transport=fresh,factory=lambda c:mail)
            (statusdir/'observer.json').chmod(0o644);observer_client('recovered')
            observer_write(snapshot)
            control=module('observer-settings')
            cc=dict(site_id=settings['site_id'],inbox_db=str(work/'settings-inbox.sqlite'),state=str(work/'settings-control'),delivery_state=oc['alerts']['state'],policy_file=str(work/'observer-policy.json'))
            (work/'observer-policy.json').write_text(json.dumps(dict(profiles=profiles,allowed_recipients=dict(mail_profile=['operator@example.invalid']),required_kinds=sorted(control.KINDS))))
            control.receive(cc,dict(site_id=settings['site_id'],nonce='a'*32,requests=[]))
            oc['configuration']=cc;control.enable(oc)
            observer.observe(oc,transport=fresh,factory=lambda c:mail);(statusdir/'observer.json').chmod(0o644)
            def settings_client(mode):
                r=run('docker','exec',browser,'python3','/lab/observer-settings-http-test.py',mode,timeout=120)
                values=json.loads(r.stdout);checks.extend(values);print('settings '+mode+': '+str(len(values))+' checks passed',flush=True)
            settings_client('request')
            relay=dict(site_id=settings['site_id'],lock_file=str(work/'settings-relay.lock'),requests_dir=str(observer_requests))
            with sqlite3.connect(Path(oc['alerts']['state'])/'dispatch.sqlite') as conn:before_rows=conn.execute('SELECT channel,event,status,receipt,attempts,next_at FROM deliveries ORDER BY rowid').fetchall()
            control.exchange(relay,lambda c,p:control.receive(cc,p))
            control.apply_pending(cc)
            with sqlite3.connect(Path(oc['alerts']['state'])/'dispatch.sqlite') as conn:after_rows=conn.execute('SELECT channel,event,status,receipt,attempts,next_at FROM deliveries ORDER BY rowid').fetchall()
            assert before_rows==after_rows;checks.append('UI cutover preserves existing rejected and undelivered rows')
            observer.observe(oc,transport=fresh,factory=lambda c:mail);(statusdir/'observer.json').chmod(0o644);settings_client('applied')
            settings_client('test-request')
            settings_client('test-waiting')
            control.exchange(relay,lambda c,p:control.receive(cc,p))
            settings_client('test-waiting')
            import fcntl
            with (Path(cc['delivery_state'])/'dispatch.lock').open('a') as stopped:
                fcntl.flock(stopped,fcntl.LOCK_EX|fcntl.LOCK_NB)
                observer.observe(oc,transport=fresh,factory=lambda c:mail)
            (statusdir/'observer.json').chmod(0o644);settings_client('test-worker-stopped')
            test_calls=[]
            class TestAdapter:
                def send(self,event):
                    if event['kind']=='notification_test':test_calls.append(event);return {}
                    return mail.send(event)
                def poll(self,receipt):return mail.poll(receipt)
                def cancel(self,receipt):return mail.cancel(receipt)
            observer.observe(oc,transport=fresh,factory=lambda c:TestAdapter());(statusdir/'observer.json').chmod(0o644)
            settings_client('test-result')
            settings_client('alarm-with-test')
            prior=(statusdir/'observer.json').read_bytes()
            aged=json.loads(prior);aged['observed_at']='2000-01-01T00:00:00+00:00';aged['history']=[]
            for target in aged['targets'].values():target['last_seen']=None
            observer_write(aged);settings_client('test-stale')
            (statusdir/'observer.json').write_bytes(prior)
            observer.observe(oc,transport=fresh,factory=lambda c:TestAdapter());(statusdir/'observer.json').chmod(0o644)
            assert len(test_calls)==1 and test_calls[0]['transition']=='resolved';checks.append('independent test fixed normal priority and never repeated')
            settings_client('disable')
            control.exchange(relay,lambda c,p:control.receive(cc,p));active_before=control.live.current(cc['delivery_state']);control.apply_pending(cc)
            assert control.live.current(cc['delivery_state'])==active_before;checks.append('UI attempt to disable last independent alert route keeps active settings')
            observer.observe(oc,transport=fresh,factory=lambda c:mail);(statusdir/'observer.json').chmod(0o644);settings_client('rejected')
            for image in ('observer-settings-desktop.png','observer-settings-mobile.png'):run('docker','cp',browser+':/tmp/'+image,str(args.output/image))
            report_write(report);client('status')
            run('docker','cp',browser+':/tmp/owr-admin.png',str(args.output/'admin-desktop.png'))
            run('docker','cp',browser+':/tmp/owr-admin-mobile.png',str(args.output/'admin-mobile.png'))
            report_write(dict(report,completed_at='2000-01-01T00:00:00+00:00'));client('stale')
            report_write(dict(report,site_id='other'));client('invalid')
            report_write(dict(report,revision_token='other'));client('pending')
            report_write(report)
            live=module('notification-live')
            # Initial adoption preserves the exact UI revision; no save is implied.
            config=live.apply(config,binding,bridge.digest(config))
            bridge.dispatch.run(config,factory=lambda c:push if c['transport']=='pushover' else mail)
            binding=dict(config['admin_binding'],config_hash=bridge.digest(config))
            report=bridge.status(config,binding,simulated=True);report_write(report)
            client('test-request')
            results=live.tests(config,requests,factory=lambda c:push if c['transport']=='pushover' else mail)
            assert len(results)==1 and results[0]['status']=='accepted'
            assert push.send.call_args.args[0]['kind']=='notification_test' and push.send.call_args.args[0]['transition']=='resolved'
            calls=push.send.call_count;live.tests(config,requests,factory=lambda c:push)
            assert push.send.call_count==calls
            report_write(bridge.status(config,binding,simulated=True));client('test-result')
            checks.extend(['live adoption retains receipt and rejected delivery','test request sent once through external worker','test uses normal priority and fixed body'])
            # Screenshots include actual buttons and returned test acceptance.
            client('status')
            run('docker','cp',browser+':/tmp/owr-admin.png',str(args.output/'admin-desktop.png'))
            run('docker','cp',browser+':/tmp/owr-admin-mobile.png',str(args.output/'admin-mobile.png'))
            assert all(c['provider']['transport'] in ('pushover','smtp_starttls') for c in config['channels'])
            checks.append('saved settings compiled through real dispatcher; mocked sends only')
            if args.plugin_zip:
                def php(code):return run('docker','exec','-u','www-data',web,'php','-r','require "/var/www/html/wp-load.php";require_once ABSPATH."wp-admin/includes/plugin.php";'+code).stdout
                snapshot='echo hash("sha256",serialize([get_option("owr_notification_settings_v1"),get_option("owr_observer_settings_v1")]));'
                before=php(snapshot)
                requests_before={str(f.relative_to(requests)):hashlib.sha256(f.read_bytes()).hexdigest() for f in requests.rglob('*') if f.is_file()}
                php('deactivate_plugins("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");')
                assert php('echo is_plugin_active("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php")?"active":"inactive";')==b'inactive'
                assert php(snapshot)==before
                php('$r=activate_plugin("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");if(is_wp_error($r)){throw new Exception("reactivation failed");}')
                assert php(snapshot)==before
                assert requests_before=={str(f.relative_to(requests)):hashlib.sha256(f.read_bytes()).hexdigest() for f in requests.rglob('*') if f.is_file()}
                client('status')
                checks.extend(['plugin deactivation confirmed','settings retained while inactive and after reactivation','external request files unchanged by plugin stop and restart'])

            try:bridge.compile_settings(settings,profiles,source,work/'delivery')
            except ValueError:checks.append('existing delivery state cannot be silently replaced')
            else:raise AssertionError('migration guard failed')
    finally:
        failures=[]
        for name in reversed(created):
            if run('docker','rm','-f','-v',name,check=False).returncode:failures.append(name)
        if failures:raise RuntimeError('Lab cleanup failed for: '+','.join(failures))
    result=dict(format='owr-notification-admin-lab-v1',checks=checks,passed=len(checks),external_notifications_sent=0,production_deployed=False,containers_removed=True)
    if args.plugin_zip:result.update(plugin_zip_sha256=hashlib.sha256(args.plugin_zip.read_bytes()).hexdigest(),installation_method='WordPress Plugin_Upgrader API; not browser upload',scope='Plugin admin integration with mocked external delivery; not backup product acceptance')
    (args.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
