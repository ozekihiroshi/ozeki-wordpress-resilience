"""Explicit generated-data live S3 and private Docker experiment. No production changes."""
import argparse,base64,copy,hashlib,importlib.util,ipaddress,json,os,secrets,struct,subprocess,time,uuid,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('site_materials','site-materials.py');k=load('generation_kit','rbr-generation-kit.py')
def run(*args,input=None,check=True):
    p=subprocess.run(args,input=input,capture_output=True,timeout=180)
    if check and p.returncode:raise RuntimeError(str(args[:3])+': '+p.stderr.decode(errors='replace')[-1200:]+p.stdout.decode(errors='replace')[-500:])
    return p
def png(color):
    def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(color)*2)*2))+chunk(b'IEND',b'')
def page(id,kind='page',parent=None):return {'id':id,'kind':kind,'title':id+' 試験情報','slug':id,'parent':parent,'nodes':[{'type':'paragraph','text':'試験用の会社情報です。'}]}
def trial_target(folder,bundle,wp,db,sequence=None,validation_checks=True,keep_target=False):
    folder.mkdir();tag='owr-materials-'+uuid.uuid4().hex[:10];net=tag+'-net';web=tag+'-web';dbn=tag+'-db';created=[];completed=False
    (folder/'resources.json').write_bytes(m.canon({'web':web,'database':dbn,'network':net,'private_only':True}))
    try:
        ids=run('docker','network','ls','-q').stdout.decode().split();used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in n['IPAM']['Config'] or [] if 'Subnet'in c]
        subnet=next(str(n) for n in ipaddress.ip_network('10.253.0.0/16').subnets(new_prefix=28) if not any(n.overlaps(u) for u in used if n.version==u.version))
        run('docker','network','create','--internal','--subnet',subnet,net);created.append(('network',net))
        run('docker','run','-d','--name',dbn,'--network',net,'--memory','512m','--cpus','1','--pids-limit','256','--tmpfs','/var/lib/mysql:rw','-e','MARIADB_ROOT_PASSWORD=lab-only','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress','-e','MARIADB_PASSWORD=lab-only',db);created.append(('container',dbn))
        run('docker','run','-d','--name',web,'--network',net,'--memory','512m','--cpus','1','--pids-limit','256','--tmpfs','/var/www/html:rw','-e','OWR_RBR_DISPOSABLE=1','-e','WORDPRESS_DB_HOST='+dbn,'-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD=lab-only','-e','WORDPRESS_DB_NAME=wordpress','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('WP_HTTP_BLOCK_EXTERNAL',true);define('WP_POST_REVISIONS',false);define('DISALLOW_FILE_MODS',true);",'-v',str(ROOT)+':/kit:ro','-v',str(bundle)+':/bundle:ro',wp);created.append(('container',web))
        def php(code,check=True):return run('docker','exec','-i',web,'php',input=('<?php '+code).encode(),check=check)
        for attempt in range(60):
            p=php("$m=@new mysqli(getenv('WORDPRESS_DB_HOST'),'wordpress','lab-only','wordpress');exit($m->connect_errno?1:0);",False)
            if p.returncode==0 and run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('Dedicated WP readiness timeout')
        info=json.loads(run('docker','inspect',web).stdout)[0]
        m.require(info['Image']==wp and not info['HostConfig']['PortBindings'],'Pinned private target')
        m.require(json.loads(run('docker','network','inspect',net).stdout)[0]['Internal'],'Internal network')
        routes=run('docker','exec',web,'cat','/proc/net/route').stdout.decode();m.require(not any(x.split()[1]=='00000000' for x in routes.splitlines()[1:] if x.split()),'No default route')
        guard="<?php add_filter('pre_wp_mail',function(){update_option('rbr_side_effect_attempts',1+(int)get_option('rbr_side_effect_attempts',0));return false;});add_filter('pre_http_request',function(){update_option('rbr_side_effect_attempts',1+(int)get_option('rbr_side_effect_attempts',0));return new WP_Error('blocked');});"
        php("mkdir('/var/www/html/wp-content/mu-plugins',0755,true);file_put_contents('/var/www/html/wp-content/mu-plugins/guard.php',base64_decode('"+base64.b64encode(guard.encode()).decode()+"'));")
        php("define('WP_INSTALLING',true);require '/var/www/html/wp-load.php';require ABSPATH.'wp-admin/includes/upgrade.php';wp_install('Private material trial','operator','operator@example.invalid',false,'','lab-only-password');global $wpdb;foreach($wpdb->get_col(\"SELECT ID FROM {$wpdb->posts}\")as $id)wp_delete_post($id,true);update_option('rbr_side_effect_attempts',0);update_option('cron',[]);")
        sequential=[]
        if sequence:
            for received in sequence:
                (bundle/'received.json').write_bytes(m.canon(received))
                step=json.loads(run('docker','exec','-e','OWR_SITE_INCREMENTAL=1',web,'php','/kit/tools/site-wordpress-apply.php').stdout)
                m.require(step['side_effect_attempts']==0,'No side effects during sequential projection');sequential.append(step)
            prior=php("require '/var/www/html/wp-load.php';global $wpdb;echo json_encode([$wpdb->get_results('SELECT * FROM '.$wpdb->posts,ARRAY_A),get_option('owr_site_projection')]);").stdout
            (bundle/'received.json').write_bytes(m.canon(sequence[0]))
            stale=run('docker','exec','-e','OWR_SITE_INCREMENTAL=1',web,'php','/kit/tools/site-wordpress-apply.php',check=False)
            after=php("require '/var/www/html/wp-load.php';global $wpdb;echo json_encode([$wpdb->get_results('SELECT * FROM '.$wpdb->posts,ARRAY_A),get_option('owr_site_projection')]);").stdout
            m.require(stale.returncode!=0 and prior==after,'Stale generation must not change projected content')
            (bundle/'received.json').write_bytes(m.canon(sequence[-1]))
        result=json.loads(run('docker','exec',web,'php','/kit/tools/site-wordpress-apply.php').stdout)
        replay=json.loads(run('docker','exec',web,'php','/kit/tools/site-wordpress-apply.php').stdout)
        m.require(result==replay and result['side_effect_attempts']==0,'Idempotent private apply')
        if validation_checks:
            good=json.loads((bundle/'received.json').read_bytes());bad=copy.deepcopy(good);bad['parent']=good['receipt'];bad['receipt']=dict(good['receipt'],sha256='0'*64);bad['site']['title']='Must roll back';bad['site']['entries'][0]['title']='Must roll back'
            before=php("require '/var/www/html/wp-load.php';global $wpdb;echo json_encode([$wpdb->get_results('SELECT * FROM '.$wpdb->posts,ARRAY_A),get_option('owr_site_projection'),get_option('blogname')]);").stdout
            (bundle/'received.json').write_bytes(m.canon(bad))
            rejected=run('docker','exec','-e','OWR_SITE_INCREMENTAL=1',web,'php','/kit/tools/site-wordpress-apply.php',check=False)
            after=php("require '/var/www/html/wp-load.php';global $wpdb;echo json_encode([$wpdb->get_results('SELECT * FROM '.$wpdb->posts,ARRAY_A),get_option('owr_site_projection'),get_option('blogname')]);").stdout
            (bundle/'received.json').write_bytes(m.canon(good))
            m.require(rejected.returncode!=0 and before==after,'Failed projection must roll back content and state');result['failed_projection_rolled_back']=True
        if sequence:result.update(sequential_generations=len(sequential),stale_rejected_without_changes=True)
        result['logical_sha256']=m.sha(m.canon(json.loads((bundle/'received.json').read_bytes())['expected']))
        result['target']={'web':web,'database':dbn,'network':net,'retained_private':keep_target}
        (folder/'result.json').write_bytes(m.canon(result));completed=True;return result
    finally:
        if not (completed and keep_target):
            for kind,name in reversed(created):run('docker','rm','-f','-v',name) if kind=='container' else run('docker','network','rm',name)
def main(out):
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    # Read-only account/bucket checks before any PUT. Fresh random prefix is retained in state.
    (out/'preflight.json').write_bytes(m.canon(k.k.transport.preflight()))
    prefix='sites/isolated-queue-lab/sets/AWS-'+secrets.token_hex(8)+'/'
    (out/'scope.json').write_bytes(m.canon({'prefix':prefix,'generated_only':True}))
    store=k.LiveStore(out/'writer');repo=m.Repository(store,out/'journal',prefix)
    site={'schema':'owr-site-materials-v1','title':'素材再構築試験会社','landing':'company','entries':[page('company'),page('services'),page('contact'),page('news','post'),{'id':'logo','kind':'image','mime':'image/png','data':base64.b64encode(png((20,50,90))).decode(),'alt':'試験ロゴ'}]}
    site['entries'][0]['nodes']=[{'type':'paragraph','text':'会社案内の冒頭'},{'type':'image','target':'logo'},{'type':'link','text':'サービスへ','target':'services'},{'type':'paragraph','text':'リンク後の本文'}]
    head=None;receipts=[]
    for i in range(8):
        if i==1:site['entries'].append(page('details','page','services'))
        if i==2:site['entries'].append(page('notice','post'))
        if i==3:site['entries'][3]['nodes']=m.markdown('## お知らせ\n新しいサービスを開始しました。')
        if i==4:site['entries'][4]['data']=base64.b64encode(png((90,20,50))).decode()
        if i==5:site['entries']=[e for e in site['entries'] if e['id']!='notice']
        if i==6:site['entries'][1]['slug']='new-services';site['entries'][1]['title']='更新したサービス'
        site['entries'][2]['nodes']=[{'type':'paragraph','text':'連絡先 第'+str(i)+'版'}]
        head=repo.save('edit-'+str(i),head,site);receipts.append(head)
        print(json.dumps({'saved_generation':i+1}),flush=True)
    (out/'receipts.json').write_bytes(m.canon(receipts))
    # Fresh reader uses fixed S3 references only. No writer cache, source request or DB mounted.
    reader=k.LiveStore(out/'reader');results=[]
    wp=run('docker','image','inspect','wordpress:php8.3-apache','--format','{{.Id}}').stdout.decode().strip();db=run('docker','image','inspect','mariadb:11.8','--format','{{.Id}}').stdout.decode().strip()
    for n,index in enumerate([0,7,7]):
        bundle=out/('received-'+str(n));bundle.mkdir();received=m.receive(reader,receipts[index]);(bundle/'received.json').write_bytes(m.canon(received));print(json.dumps({'received_generation':index+1}),flush=True)
        results.append(trial_target(out/('target-'+str(n)),bundle,wp,db))
    m.require(results[1]['logical_sha256']==results[2]['logical_sha256'],'Repeat reconstruction mismatch')
    report={'state':'PASS','generations':8,'reconstructed_generations':[1,8,8],'results':results,'source_database_used':False,'real_s3':True,'runtime_images':{'wordpress':wp,'database':db},'runtime_images_from_local_cache':True,'public_activation':False,'dedicated_containers_removed':True,'policy':'integrity','native_editor_connected':False}
    (out/'result.json').write_bytes(m.canon(report));print(json.dumps(report),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-generated-live-s3',action='store_true');a=p.parse_args()
    if not a.allow_generated_live_s3:p.error('Explicit generated live-S3 opt-in required')
    main(a.output)
