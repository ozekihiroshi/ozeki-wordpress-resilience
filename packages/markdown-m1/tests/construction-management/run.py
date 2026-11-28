"""Dedicated dm fixture; synthetic WordPress only, no S3 or production mounts."""
import argparse, importlib.util, json, os, pathlib, subprocess, time, traceback, urllib.error
a=argparse.ArgumentParser();a.add_argument('--stage',required=True);a=a.parse_args();b=pathlib.Path(a.stage).resolve()
name='construction-managed-20261129';label='ozeki.isolation='+name
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];owned=[];result={};start=time.monotonic()
def d(*args,raw=None):
    r=subprocess.run(D+list(args),input=raw,capture_output=True,timeout=180)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-1500:])
    return r.stdout
def wp(site,*args):return d('exec',name+'-'+site,'php','/tmp/wp.phar','--allow-root',*args).decode()
try:
    d('network','create','--internal','--label',label,name);owned.append(('network',name))
    d('run','-d','--name',name+'-db','--network',name,'--label',label,'--memory','384m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');owned.append(('container',name+'-db'))
    for _ in range(60):
        try:d('exec',name+'-db','healthcheck.sh','--connect','--innodb_initialized');break
        except RuntimeError:time.sleep(1)
    spec=importlib.util.spec_from_file_location('managed_http',b/'product/tools/reconstruct-markdown.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    clients={}
    for site in ['source','target']:
        web=name+'-'+site;d('volume','create','--label',label,web);owned.append(('volume',web))
        d('run','-d','--name',web,'--network',name,'--label',label,'--memory','384m','-v',web+':/var/www/html','-v',str(b)+':'+str(b),'-e','WORDPRESS_DB_HOST='+name+'-db','-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+site+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');owned.append(('container',web))
        for _ in range(60):
            try:d('exec',web,'test','-f','/var/www/html/wp-config.php');break
            except RuntimeError:time.sleep(1)
        core=pathlib.Path('/tmp/owr-community-rc23-roundtrip-20261128')
        d('cp',str(core/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(core/'wp.phar'),web+':/tmp/wp.phar')
        user=site+'-operator';wp(site,'core','install','--url=http://'+web+'.invalid','--title=Managed fixture','--admin_user='+user,'--admin_password=isolated-only-123','--admin_email='+user+'@example.invalid','--skip-email')
        ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][name]['IPAddress'];wp(site,'option','update','home','http://'+ip);wp(site,'option','update','siteurl','http://'+ip)
        config={'bucket':'synthetic','region':'ap-northeast-1','prefix':'isolated/','owner':'000000000000','setup_role':'source' if site=='source' else 'recovery','protect':False}
        wp(site,'option','update','ozeki_resilience_m1_config',json.dumps(config),'--format=json')
        d('exec',web,'mkdir','-p','/tmp/product','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'product')+'/.',web+':/tmp/product/');d('cp',str(b/'product/tests/construction-management/fixture.php'),web+':/var/www/html/wp-content/mu-plugins/managed.php')
        d('exec',web,'chown','-R','www-data:www-data','/var/www/html');clients[site]=m.NormalMarkdownClient('http://'+ip,user,'isolated-only-123',True)
    c=clients['source'];path='/wp-admin/tools.php?page=ozeki-construction'
    markup=c.request(path)[0].decode();assert 'Construction preservation (isolated)' in markup
    denied=False
    try:c.request('/wp-admin/admin-post.php',{'action':'ozeki_construction','operation':'initial','trust_initial':'1','_wpnonce':'invalid'})
    except urllib.error.HTTPError as e:denied=e.code==403
    assert denied;result['bad_nonce_rejected']=True
    nonce=m.Fields(markup).values['_wpnonce']
    c.request('/wp-admin/admin-post.php',{'action':'ozeki_construction','operation':'initial','trust_initial':'1','_wpnonce':nonce})
    state=json.loads(wp('source','option','get','ozeki_resilience_construction_preservation_v1','--format=json'));result['initial_confirmed']=state['through']==0
    p=c.rest('pages',{'title':'Managed material','content':'Ordinary content','status':'publish'})
    c.rest('pages/'+str(p['id']),{'content':'Ordinary content with follow-up'})
    markup=c.request(path)[0].decode();nonce=m.Fields(markup).values['_wpnonce'];assert 'pending' in markup
    c.request('/wp-admin/admin-post.php',{'action':'ozeki_construction','operation':'flush','_wpnonce':nonce})
    state=json.loads(wp('source','option','get','ozeki_resilience_construction_preservation_v1','--format=json'));result['formal_through']=state['through'];assert state['through']==2
    # This transfer copies synthetic object-store bytes, never supplies maps or recipes.
    objects=b/('objects-'+str(time.time_ns()));objects.mkdir(mode=0o700);d('cp',name+'-source:/tmp/construction-objects/.',str(objects));d('cp',str(objects),name+'-target:/tmp/construction-objects');d('exec',name+'-target','chown','-R','www-data:www-data','/tmp/construction-objects')
    c=clients['target'];markup=c.request(path)[0].decode();nonce=m.Fields(markup).values['_wpnonce']
    c.request('/wp-admin/admin-post.php',{'action':'ozeki_construction','operation':'queue','commit':json.dumps(state['commit']),'_wpnonce':nonce})
    job=json.loads(wp('target','option','get','ozeki_resilience_construction_job_v1','--format=json'));assert job['state']=='queued'
    runner=b/'runner.json';runner.write_text(json.dumps(D+['exec',name+'-target']))
    command=['python3','-B',str(b/'product/tools/construction-worker.py'),'--wordpress','/var/www/html','--wp-cli','/tmp/wp.phar','--user','target-operator','--allow-root','--local-runner',str(runner),'--private-work-parent',str(b)]
    r=subprocess.run(command,input='isolated-only-123\n',capture_output=True,text=True,timeout=180);result['worker_exit']=r.returncode
    if r.returncode:raise RuntimeError(r.stderr[-1800:]+'\n'+r.stdout[-800:])
    pages=c.rest('pages?context=edit');pages=[x for x in pages if x['title']['raw']=='Managed material'];assert len(pages)==1 and pages[0]['content']['raw']=='Ordinary content with follow-up'
    c.rest('pages/'+str(pages[0]['id']),{'title':'Ordinary destination edit'})
    job=json.loads(wp('target','option','get','ozeki_resilience_construction_job_v1','--format=json'));assert job['state']=='registered_pending_use_check'
    wp('source','user','meta','update','source-operator','locale','ja')
    japanese=clients['source'].request(path)[0].decode();assert '構築記録の保全（隔離環境）' in japanese and '保存先で確定済み' in japanese
    result['japanese_management']=True
    r=subprocess.run(command,input='isolated-only-123\n',capture_output=True,text=True,timeout=40);assert r.returncode!=0
    result.update(passed=True,ordinary_edit=True,no_duplicate_retry=True,management_to_worker=True)
except Exception as e:
    result.update(passed=False,error=str(e),traceback=traceback.format_exc())
    try:result['source_status']=json.loads(wp('source','eval','echo wp_json_encode(OzekiResilience\\M1\\ConstructionJournal::status());'))
    except Exception:pass
finally:
    result['cleanup_errors']=[]
    for kind,item in sorted(owned,key=lambda x:{'container':0,'volume':1,'network':2}[x[0]]):
        try:
            info=json.loads(d('inspect',item) if kind=='container' else d(kind,'inspect',item))[0]
            labels=info.get('Config',{}).get('Labels',{}) if kind=='container' else info.get('Labels',{})
            if labels.get('ozeki.isolation')!=name:raise RuntimeError('Ownership label mismatch')
            if kind=='container':d('rm','-f',item)
            else:d(kind,'rm',item)
        except Exception as e:result['cleanup_errors'].append(str(e))
    result['seconds']=round(time.monotonic()-start,3);(b/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
