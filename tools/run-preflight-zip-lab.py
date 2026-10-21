#!/usr/bin/env python3
"""Offline ZIP install/update acceptance; generated reports and isolated WordPress."""
import argparse,hashlib,importlib.util,json,os,secrets,shutil,subprocess,tempfile,time,zipfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,check=True,timeout=120):
 p=subprocess.run(args,input=input,capture_output=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError(p.stderr.decode()[-2000:]+p.stdout.decode()[-1000:])
 return p
def module(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
import contextlib,types
@contextlib.contextmanager
def ui_session(statusdir, plugin_zip):
    args=types.SimpleNamespace(plugin_zip=plugin_zip)
    images=dict(line.split('=',1) for line in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in line)
    prefix='owr-preflight-zip-'+secrets.token_hex(5);db=prefix+'-db';web=prefix+'-web';browser=prefix+'-browser';created=[];checks=[]
    try:
        with tempfile.TemporaryDirectory(prefix='owr-preflight-zip-') as temp:
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
            password=secrets.token_hex(24);env=work/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("OWR_PREFLIGHT_WATCHDOG_REPORTS",["source"=>["path"=>"/status/source.json","monitor_id"=>"preflight-source","transfer_file"=>"/status/source-transfer.json"],"receiver"=>["path"=>"/status/receiver.json","monitor_id"=>"preflight-receiver","transfer_file"=>"/status/receiver-transfer.json"]]); define("OWR_DAILY_TRANSFER_FILE","/status/transfer.json"); define("OWR_DAILY_STATUS_FILE","/status/daily.json"); define("OWR_PREFLIGHT_SITE_ID","generated-first-site"); define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true); define("OWR_NOTIFICATION_STATUS_FILE","/status/status.json"); define("OWR_NOTIFICATION_REQUEST_DIR","/requests");\n');env.chmod(0o600)
            env.write_text(env.read_text().replace('WORDPRESS_CONFIG_EXTRA=', 'WORDPRESS_CONFIG_EXTRA=define("OWR_OBSERVER_STATUS_FILE","/status/observer.json"); '))
            env.write_text(env.read_text().replace('WORDPRESS_CONFIG_EXTRA=', 'WORDPRESS_CONFIG_EXTRA=define("OWR_OBSERVER_REQUEST_DIR","/requests/observer"); '))
            env.write_text(env.read_text().replace('WORDPRESS_CONFIG_EXTRA=', 'WORDPRESS_CONFIG_EXTRA=define("OWR_PREFLIGHT_REPORT","/status/preflight.json"); define("OWR_PREFLIGHT_CONFIG_SHA256","'+('a'*64)+'"); '))
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
 p=argparse.ArgumentParser();p.add_argument('--zip',type=Path,required=True);p.add_argument('--old-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 checks=[];observer=module('watchdog-observer')
 snapshots={}
 for role in ('source','receiver'):
     root=args.output/role;root.mkdir()
     config=dict(state=str(root/'observer'),monitor_id='preflight-'+role,stale_after_seconds=5,ssh={},
         public_status_file=str(root/'public.json'),admin_site_id='generated-first-site')
     alert=json.loads((ROOT/'examples/watchdog-observer/observer.example.json').read_text())['alerts']
     alert['source_outbox']=str(root/'outbox.sqlite');alert['state']=str(root/'delivery')
     config['alerts']=alert
     beginning=datetime.now(timezone.utc)-timedelta(seconds=15)
     stamp=beginning;down=False
     def transport(c,p):
         if down and role=='source':raise OSError('synthetic source outage')
         return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id=config['monitor_id'],status='present',
             heartbeat=dict(format='owr-monitor-heartbeat-v1',monitor_id=config['monitor_id'],
                 completed_at=stamp.isoformat(),undelivered=0,open_incidents=0))
     class Provider:
         def send(self,event):return {}
     def tick(at):
         observer.observe(config,now=at,transport=transport,factory=lambda c:Provider())
         return json.loads((root/'public.json').read_text())
     tick(beginning);down=True
     alarm=tick(beginning+timedelta(seconds=6))
     down=False;stamp=beginning+timedelta(seconds=8)
     recovered=tick(stamp)
     snapshots[role]=dict(alarm=alarm,recovered=recovered)
 status=args.output/'status';status.mkdir(mode=0o755)
 for role in snapshots:
  (status/(role+'.json')).write_text(json.dumps(snapshots[role]['recovered']))
  (status/(role+'-transfer.json')).write_text(json.dumps(dict(format='owr-observer-transfer-v1',site_id='generated-first-site',monitor_id='preflight-'+role,state='ok',attempted_at=datetime.now(timezone.utc).isoformat())))
 def external():return {str(f.relative_to(args.output)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('source','receiver','status') for f in (args.output/folder).rglob('*') if f.is_file()}

 for mode,initial in [('fresh',args.zip),('upgrade',args.old_zip)]:
  # Explicit synthetic fixture refresh before each install, never during preservation checks.
  now=datetime.now(timezone.utc).isoformat()
  for role in snapshots:
   v=snapshots[role]['recovered'];v['observed_at']=now
   (status/(role+'.json')).write_text(json.dumps(v))
   h=json.loads((status/(role+'-transfer.json')).read_text());h['attempted_at']=now
   (status/(role+'-transfer.json')).write_text(json.dumps(h))
  fixture=dict(format='owr-preflight-admin-v1',site_id='generated-first-site',config_sha256='a'*64,attempted_at=now,result=dict(production_ready=False,state='needs_configuration',host_observation=dict(state='validated_report',unverified=['writers','trust']),issues=[dict(code='host_unverified_scope_remaining',category='configuration')]))
  (status/'preflight.json').write_text(json.dumps(fixture))
  preserved=external()
  with ui_session(status,initial) as (web,browser):
   def php(code):return run('docker','exec','-u','www-data',web,'php','-r','require "/var/www/html/wp-load.php";require_once ABSPATH."wp-admin/includes/plugin.php";'+code).stdout
   php('\\Ozeki\\Resilience\\NotificationAdmin::state();\\Ozeki\\Resilience\\ObserverSettings::state();')
   # Populate non-default settings through the existing real browser form.
   run('docker','exec',browser,'python3','/lab/http-test.py','settings',timeout=180)
   snapshot='global $wpdb;echo json_encode($wpdb->get_results("SELECT option_name,option_value FROM {$wpdb->options} WHERE option_name LIKE CONCAT(CHAR(111,119,114,95),CHAR(37)) OR option_name=CHAR(99,114,111,110) ORDER BY option_name",ARRAY_A));'
   # Editor dashboard creates a WordPress auto-draft and schedules its cleanup.
   # Initialize that core behavior before the preservation baseline.
   php('require_once ABSPATH."wp-admin/includes/post.php";wp_set_current_user(get_user_by("login","labeditor")->ID);get_default_post_to_edit("post",true);')
   # Core upgrader init schedules temporary backup cleanup outside WP_INSTALLING.
   php('require_once ABSPATH."wp-admin/includes/class-wp-upgrader.php";$u=new WP_Upgrader(new Automatic_Upgrader_Skin());$u->init();')
   before=php(snapshot)
   def compare():
    after=php(snapshot)
    (args.output/(mode+'-comparison.json')).write_text(json.dumps(dict(before=json.loads(before),after=json.loads(after)),indent=2))
    assert after==before
   config=run('docker','exec',web,'sha256sum','/var/www/html/wp-config.php').stdout
   request_hash='find /requests -type f -exec sha256sum {} +'
   requests=run('docker','exec',web,'sh','-c',request_hash).stdout
   if mode=='upgrade':
    run('docker','cp',str(args.zip.resolve()),web+':/tmp/final.zip')
    php('require_once ABSPATH."wp-admin/includes/file.php";require_once ABSPATH."wp-admin/includes/class-wp-upgrader.php";$u=new Plugin_Upgrader(new Automatic_Upgrader_Skin());$r=$u->install("/tmp/final.zip",["overwrite_package"=>true]);if(is_wp_error($r)||!$r)throw new Exception("update failed");')
    assert php('echo is_plugin_active("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php")?"yes":"no";')==b'yes'
   compare()
   php('deactivate_plugins("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");')
   compare()
   php('$r=activate_plugin("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");if(is_wp_error($r))throw new Exception("activation failed");')
   compare()
   assert config==run('docker','exec',web,'sha256sum','/var/www/html/wp-config.php').stdout
   assert requests==run('docker','exec',web,'sh','-c',request_hash).stdout
   with zipfile.ZipFile(args.zip) as z:
    for name in z.namelist():
     actual=run('docker','exec',web,'cat','/var/www/html/wp-content/plugins/'+name).stdout
     assert actual==z.read(name),name
   expected={role:dict(report='current',transfer='ok',text=[]) for role in snapshots}
   result=run('docker','exec',browser,'python3','/lab/preflight-observer-relay-vm-browser.py',mode,json.dumps(expected),timeout=180)
   assert json.loads(result.stdout)['passed']
   run('docker','cp',browser+':/tmp/relay-'+mode+'.png',str(args.output/(mode+'.png')))
   watch=run('docker','exec',browser,'python3','/lab/preflight-watchdog-browser.py','current',timeout=180)
   (args.output/(mode+'-watchdog-checks.json')).write_bytes(watch.stdout)
   pre=run('docker','exec',browser,'python3','/lab/preflight-browser.py','current',timeout=180)
   assert json.loads(pre.stdout)['checks']
   (args.output/(mode+'-preflight-checks.json')).write_bytes(pre.stdout)
   run('docker','cp',browser+':/tmp/preflight-current.png',str(args.output/(mode+'-preflight.png')))
   after=php(snapshot)
   (args.output/(mode+"-options.json")).write_text(json.dumps(dict(before=json.loads(before),after=json.loads(after)),indent=2))
   assert after==before
   assert external()==preserved
   checks.append(mode+': exact ZIP files, active plugin, browser current reports/history, editor denied, POST405, settings/cron/config/requests/external ledgers preserved through deactivate/reactivate')
   print('PASS '+checks[-1],flush=True)
 result=dict(passed=True,checks=checks,zip_sha256=hashlib.sha256(args.zip.read_bytes()).hexdigest(),old_zip_sha256=hashlib.sha256(args.old_zip.read_bytes()).hexdigest(),containers_removed=True,scope='Generated fixtures; real WordPress Plugin_Upgrader install/overwrite and Chromium; no S3 or external notifications; not a repeat of systemd reboot trial')
 (args.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
