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
    prefix='owr-daily-admin-'+secrets.token_hex(5);db=prefix+'-db';web=prefix+'-web';browser=prefix+'-browser';created=[];checks=[]
    print('LAB_RESOURCE_PREFIX '+prefix,flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix='owr-admin-') as temp:
            work=Path(temp);work.chmod(0o755);statusdir=work/'status';statusdir.mkdir(mode=0o755)
            requests=work/'requests';requests.mkdir(mode=0o770)
            plugin=work/'plugin';(plugin/'src').mkdir(parents=True)
            shutil.copy2(ROOT/'ozeki-wordpress-resilience.php',plugin/'ozeki-wordpress-resilience.php')
            shutil.copy2(ROOT/'src/NotificationAdmin.php',plugin/'src/NotificationAdmin.php')
            shutil.copy2(ROOT/'src/ObserverAdmin.php',plugin/'src/ObserverAdmin.php')
            shutil.copy2(ROOT/'src/DailyAdmin.php',plugin/'src/DailyAdmin.php')
            shutil.copy2(ROOT/'src/DailyWatchdogAdmin.php',plugin/'src/DailyWatchdogAdmin.php')
            shutil.copy2(ROOT/'src/ObserverSettings.php',plugin/'src/ObserverSettings.php')
            observer_requests=requests/'observer';observer_requests.mkdir(mode=0o770)
            password=secrets.token_hex(24);env=work/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("OWR_DAILY_STATUS_FILE","/status/daily.json"); define("OWR_DAILY_SITE_ID","generated-first-site"); define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true); define("OWR_NOTIFICATION_STATUS_FILE","/status/status.json"); define("OWR_NOTIFICATION_REQUEST_DIR","/requests");\n');env.chmod(0o600)
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

            run('docker','cp',str(ROOT/'lab/notification-admin/daily-http-test.py'),browser+':/tmp/daily-test.py')
            source=Path.home()/'.local/share/owr-recovery-cleanup-20261020-v2'
            state=args.output/'copied-state';shutil.copytree(source,state)
            bridge=module('daily-admin-status')
            def hashes():
                return {str(p.relative_to(state)):hashlib.sha256(p.read_bytes()).hexdigest() for p in state.rglob('*') if p.is_file()}
            before=hashes()
            snapshot=bridge.snapshot(state,'generated-first-site')
            assert before==hashes()
            (args.output/'snapshot.json').write_text(json.dumps(snapshot,indent=2))
            def client(mode,value):
                p=statusdir/'daily.json'
                if value is None:
                    if p.exists():p.unlink()
                else:p.write_text(json.dumps(value))
                run('docker','exec',browser,'python3','/tmp/daily-test.py',mode)
                checks.append(mode)
            client('unavailable',None)
            snapshot['secret']='NEVER-RENDER-SECRET'
            client('current',snapshot)
            stale=dict(snapshot,observed_at='2000-01-01T00:00:00+00:00');client('stale',stale)
            client('wrong_site',dict(snapshot,site_id='other'))
            client('future',dict(snapshot,observed_at='2099-01-01T00:00:00+00:00'))
            client('oversize',dict(snapshot,secret='x'*70000))
            bad=json.loads(json.dumps(snapshot));bad['attempts'][0]['request_id']='<script>evil</script>'
            client('injection',bad)
            client('current',snapshot)
            assert before==hashes()
            checks.append('source ledger and evidence unchanged after export and HTTP GET/POST')
    finally:
        for name in reversed(created):
            run('docker','rm','-f','-v',name)
    result=dict(passed=True,checks=checks,containers_removed=True,production_deployed=False,
                scope='real WordPress authenticated HTTP tests; generated copied daily state; no external notifications or S3 calls')
    (args.output/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
