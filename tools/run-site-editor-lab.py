"""Browser -> S3-first queue -> existing material store -> private WordPress projection."""
import argparse,base64,importlib.util,ipaddress,json,os,secrets,subprocess,threading,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
l=load('material_lab','run-site-materials-lab.py');w=load('editor_worker','site-editor-worker.py');run=l.run

def main(out,live,plugin_zip=None,old_plugin_zip=None,recovery=False):
    out.mkdir(mode=0o700,exist_ok=False);shared=out/'shared';shared.mkdir();bridge=shared/'bridge';(bridge/'requests').mkdir(parents=True);(bridge/'reports').mkdir();operator=out/'operator';operator.mkdir();prefix='sites/isolated-queue-lab/sets/AWS-'+secrets.token_hex(8)+'/' if live else 'dedicated-editor/'
    if live:(out/'preflight.json').write_bytes(w.m.canon(l.k.k.transport.preflight()))
    config={'transport':'experimental-s3' if live else 'filesystem-lab','prefix':prefix,'work':str(operator),'bridge':str(bridge)};(out/'worker.json').write_bytes(w.m.canon(config));(shared/'control.json').write_text('{}')
    site={'schema':'owr-site-materials-v1','title':'編集接続試験','landing':'company','entries':[l.page('company'),l.page('services'),l.page('news','post'),{'id':'logo','kind':'image','mime':'image/png','data':base64.b64encode(l.png((10,40,90))).decode(),'alt':'試験ロゴ'}]}
    transport=w.store(config);repo=w.m.Repository(transport,operator/'journal',prefix);receipt=repo.save('enroll',None,site);received=w.m.receive(transport,receipt);(shared/'received.json').write_bytes(w.m.canon(received));(shared/'normal.png').write_bytes(l.png((20,90,40)));(shared/'replacement.png').write_bytes(l.png((90,40,20)))
    tag='owr-editor-'+uuid.uuid4().hex[:10];net=tag+'-net';db=tag+'-db';web=tag+'-web';browser=tag+'-browser';created=[];stop=threading.Event();worker_thread=None;recovery_thread=None;active_process=[None]
    wpimage=run('docker','image','inspect','wordpress:php8.3-apache','--format','{{.Id}}').stdout.decode().strip();dbimage=run('docker','image','inspect','mariadb:11.8','--format','{{.Id}}').stdout.decode().strip()
    try:
        ids=run('docker','network','ls','-q').stdout.decode().split();used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in n['IPAM']['Config']or[] if'Subnet'in c];subnet=next(str(n) for n in ipaddress.ip_network('10.252.0.0/16').subnets(new_prefix=28) if not any(n.overlaps(u) for u in used if n.version==u.version))
        run('docker','network','create','--internal','--subnet',subnet,net);created.append(('network',net))
        run('docker','run','-d','--name',db,'--network',net,'--memory','512m','--cpus','1','--pids-limit','256','--tmpfs','/var/lib/mysql:rw','-e','MARIADB_ROOT_PASSWORD=lab-only','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress','-e','MARIADB_PASSWORD=lab-only',dbimage);created.append(('container',db))
        run('docker','run','-d','--name',web,'--network',net,'--memory','768m','--cpus','1','--pids-limit','256','--tmpfs','/var/www/html:rw','-e','OWR_RBR_DISPOSABLE=1','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD=lab-only','-e','WORDPRESS_DB_NAME=wordpress','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('WP_HTTP_BLOCK_EXTERNAL',true);define('WP_POST_REVISIONS',false);define('FS_METHOD','direct');define('DISALLOW_FILE_MODS',true);",'-v',str(ROOT)+':/kit:ro','-v',str(shared)+':/bundle','--entrypoint','bash',wpimage,'-c','usermod -u 1000 www-data && exec docker-entrypoint.sh apache2-foreground');created.append(('container',web))
        def php(code,check=True):return run('docker','exec','-i',web,'php',input=('<?php '+code).encode(),check=check)
        for i in range(90):
            p=php("$m=@new mysqli(getenv('WORDPRESS_DB_HOST'),'wordpress','lab-only','wordpress');exit($m->connect_errno?1:0);",False)
            if p.returncode==0 and run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('Dedicated WP startup timeout')
        php("define('WP_INSTALLING',true);require '/var/www/html/wp-load.php';require ABSPATH.'wp-admin/includes/upgrade.php';wp_install('Editor lab','operator','operator@example.invalid',false,'','lab-only-password');global $wpdb;foreach($wpdb->get_col(\"SELECT ID FROM {$wpdb->posts}\")as $id)wp_delete_post($id,true);update_option('home','http://127.0.0.1');update_option('siteurl','http://127.0.0.1');update_option('cron',[]);wp_create_user('subscriber','subscriber-password','subscriber@example.invalid');")
        run('docker','exec',web,'php','/kit/tools/site-wordpress-apply.php')
        run('docker','exec',web,'chown','-R','1000:33','/var/www/html/wp-content/uploads')
        php("require '/var/www/html/wp-load.php';$v=json_decode(file_get_contents('/bundle/received.json'),true);update_option('owr_site_editor',['site'=>$v['site'],'receipt'=>$v['receipt']],false);")
        if plugin_zip:
            import shutil
            shutil.copy2(plugin_zip,shared/'plugin.zip')
            if old_plugin_zip:shutil.copy2(old_plugin_zip,shared/'old-plugin.zip')
            shutil.copy2(ROOT/'lab/site-materials-editor/lifecycle.php',shared/'lifecycle.php')
            first='/bundle/old-plugin.zip' if old_plugin_zip else '/bundle/plugin.zip'
            php("require '/var/www/html/wp-load.php';require '/bundle/lifecycle.php';owr_lab_install('"+first+"');update_option('owr_notification_settings_v1',['enabled'=>false,'retained'=>'generated-setting']);update_option('owr_legacy_history_fixture',['expired'=>true,'pending'=>'do-not-resend']);")
            lifecycle=php("require '/var/www/html/wp-load.php';require '/bundle/lifecycle.php';$before=owr_lab_snapshot();owr_lab_install('/bundle/plugin.zip');if($before!==owr_lab_snapshot())throw new RuntimeException('Lifecycle state changed');if(defined('OWR_SITE_MATERIALS_BRIDGE'))throw new RuntimeException('Automatic enrollment');echo json_encode(['state'=>'PASS','automatic_enrollment'=>false,'settings_history_cron_posts_preserved'=>true]);").stdout
            (out/'lifecycle-initial.json').write_bytes(lifecycle)
            import zipfile,hashlib
            with zipfile.ZipFile(plugin_zip) as archive:
                for name in archive.namelist():
                    if name.endswith('/'):continue
                    raw=run('docker','exec',web,'cat','/var/www/html/wp-content/plugins/'+name).stdout
                    if hashlib.sha256(raw).digest()!=hashlib.sha256(archive.read(name)).digest():raise RuntimeError('Installed ZIP bytes differ')
        if plugin_zip:run('docker','exec',web,'chown','-R','1000:33','/var/www/html/wp-content')
        creds=php("require '/var/www/html/wp-load.php';$u=get_user_by('login','subscriber');wp_set_current_user($u->ID);$token=WP_Session_Tokens::get_instance($u->ID)->create(time()+3600);$cookie=wp_generate_auth_cookie($u->ID,time()+3600,'logged_in',$token);$_COOKIE[LOGGED_IN_COOKIE]=$cookie;echo json_encode(['cookie'=>LOGGED_IN_COOKIE.'='.$cookie,'nonce'=>wp_create_nonce('wp_rest')]);").stdout;(shared/'subscriber.json').write_bytes(creds)
        boot=r"""<?php require_once '/kit/src/SiteMaterialsEditor.php';Owr\SiteMaterialsEditor::boot('/bundle/bridge');add_filter('pre_wp_mail',function(){return false;});add_filter('pre_http_request',function(){return new WP_Error('blocked');});add_action('rest_api_init',function(){register_rest_route('owr-test/v1','/snapshot',['methods'=>'GET','permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function(){global $wpdb;$posts=$wpdb->get_results("SELECT ID AS id,post_type AS type,post_title AS title,post_content AS content,post_status AS status,post_parent AS parent FROM {$wpdb->posts} ORDER BY ID",ARRAY_A);$images=[];foreach($posts as $p){if($p['type']==='attachment'){$images[]=['id'=>$p['id'],'sha256'=>hash_file('sha256',get_attached_file((int)$p['id']))];}}return ['posts'=>$posts,'images'=>$images,'projection'=>get_option('owr_site_projection')];}]);});"""
        if plugin_zip:
            boot=boot.replace("require_once '/kit/src/SiteMaterialsEditor.php';Owr\\SiteMaterialsEditor::boot('/bundle/bridge');","define('OWR_SITE_MATERIALS_BRIDGE','/bundle/bridge');require_once '/bundle/lifecycle.php';owr_lab_routes();")
        php("mkdir('/var/www/html/wp-content/mu-plugins',0755,true);file_put_contents('/var/www/html/wp-content/mu-plugins/editor.php',base64_decode('"+base64.b64encode(boot.encode()).decode()+"'));")
        def workloop():
            while not stop.is_set():
                with (out/'worker.log').open('ab') as log:
                    p=subprocess.Popen(['python3',str(ROOT/'tools/site-editor-worker.py'),'--config',str(out/'worker.json'),'--once','--lab-control',str(shared/'control.json')],stdout=log,stderr=log);active_process[0]=p;code=p.wait();active_process[0]=None
                if code==77:
                    (shared/'worker-paused.json').write_bytes(w.m.canon({'exit_code':code,'head':json.loads((operator/'journal/head.json').read_bytes())}))
                    while not stop.is_set() and json.loads((shared/'control.json').read_text()).get('stop_after_store'):time.sleep(.2)
                if stop.wait(.3):break
        worker_thread=threading.Thread(target=workloop);worker_thread.start()
        if recovery:
            recovery_config=dict(config,target_label='Dedicated private Docker target',wordpress_image=wpimage,database_image=dbimage,recovery_work=str(out/'recovery'))
            (out/'recovery.json').write_bytes(w.m.canon(recovery_config));(shared/'recovery-enabled').write_text('1')
            def recoveryloop():
                while not stop.is_set():
                    if not json.loads((shared/'control.json').read_text()).get('pause_recovery'):
                        with (out/'recovery.log').open('ab') as log:
                            subprocess.run(['python3',str(ROOT/'tools/site-reconstruction-worker.py'),'--config',str(out/'recovery.json'),'--once'],stdout=log,stderr=log,check=True)
                    if stop.wait(2):break
            recovery_thread=threading.Thread(target=recoveryloop);recovery_thread.start()
        run('docker','run','-d','--name',browser,'--network','container:'+web,'--user','1000:1000','--memory','2g','--shm-size','1g','-e','HOME=/tmp','-v',str(ROOT)+':/kit:ro','-v',str(shared)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(('container',browser))
        with (out/'browser.log').open('wb') as log:
            p=subprocess.Popen(['docker','exec',browser,'python3','/kit/lab/site-materials-editor/browser.py'],stdout=log,stderr=log)
            code=p.wait(timeout=2400)
        if code:raise RuntimeError('Browser trial failed; inspect private browser.log')
        result=json.loads((shared/'browser-result.json').read_text());(out/'result.json').write_bytes(w.m.canon({'state':'PASS','browser_checks':len(result['checks']),'real_s3':live,'public_activation':False,'native_entries_redirect_to_protected_editor':True}));print(json.dumps({'state':'PASS','browser_checks':len(result['checks']),'real_s3':live}),flush=True)
    finally:
        stop.set()
        if recovery_thread:recovery_thread.join(timeout=1000)
        if recovery_thread and recovery_thread.is_alive():raise RuntimeError('Recovery worker still active; preserve targets')
        if worker_thread:worker_thread.join(timeout=300)
        if worker_thread and worker_thread.is_alive():raise RuntimeError('Worker still active; preserve resources and inspect before cleanup')
        if recovery:
            for inventory in (out/'recovery').glob('target-*/resources.json'):
                target=json.loads(inventory.read_bytes())
                if not all(str(target[k]).startswith('owr-materials-') for k in ('web','database','network')):raise RuntimeError('Unexpected private target')
                for key in ('web','database'):run('docker','rm','-f','-v',target[key],check=False)
                run('docker','network','rm',target['network'],check=False)
        for kind,name in reversed(created):run('docker','rm','-f','-v',name) if kind=='container' else run('docker','network','rm',name)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--live-s3',action='store_true');p.add_argument('--recovery',action='store_true');p.add_argument('--plugin-zip',type=Path);p.add_argument('--old-plugin-zip',type=Path);p.add_argument('--allow-dedicated-lab',action='store_true');a=p.parse_args()
    if not a.allow_dedicated_lab:p.error('Explicit dedicated lab opt-in required')
    main(a.output,a.live_s3,a.plugin_zip,a.old_plugin_zip,a.recovery)
