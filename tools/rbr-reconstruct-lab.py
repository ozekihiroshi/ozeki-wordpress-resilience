"""Opt-in disposable Docker experiment, no published ports, internal network, generated data only."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, tempfile, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,check=True):
    p=subprocess.run(args,input=input,capture_output=True,timeout=180)
    if check and p.returncode:raise RuntimeError(str(args[:4])+': '+p.stderr.decode(errors='replace')[-1800:]+p.stdout.decode(errors='replace')[-800:])
    return p

def canon(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def lit(s):
    import base64
    return "base64_decode('"+base64.b64encode(s.encode()).decode()+"')"
def digest(b):return hashlib.sha256(b).hexdigest()
def main(out, prepare_only=False):
    out.mkdir(mode=0o700);bundle=out/'bundle'
    run('php',str(ROOT/'tools/rbr-create-plan-fixture.php'),'--output='+str(bundle))
    def put(raw):
        sha=digest(raw);(bundle/'cache'/f'{sha}.blob').write_bytes(raw)
        return {'locator':{'kind':'s3','bucket':'owr-offline-rbr-test','region':'ap-northeast-1','key':'definitions/'+sha,'version_id':'fixture-'+sha},'sha256':sha,'size_bytes':len(raw)}
    def read(ref):return json.loads((bundle/'cache'/(ref['sha256']+'.blob')).read_bytes())
    d=json.loads((bundle/'definition.json').read_bytes());e=read(d['environment_ref']);e['mode']='pinned-runtime'
    wp=run('docker','image','inspect','wordpress:php8.3-apache','--format','{{.Id}}').stdout.decode().strip()
    db=run('docker','image','inspect','mariadb:11.8','--format','{{.Id}}').stdout.decode().strip()
    # Image IDs are immutable local OCI configuration digests. Their layers are checked by Docker.
    for k,image in [('wordpress',wp),('php',wp),('database',db)]:e['packages'][k]={'version':'oci-'+image[7:19],'artifact_ref':put(canon({'kind':'local-oci-image-v1','image_id':image}))}
    theme={p.name:p.read_text() for p in sorted((ROOT/'tests/fixtures/rbr-theme').iterdir())}
    e['packages']['theme']={'version':'1.0.0','artifact_ref':put(canon(theme))};e['settings']['image_handler']='original-bytes-v1'
    d['environment_ref']=put(canon(e));c=read(d['comparison_ref']);c['extractor_ref']=put((ROOT/'tools/rbr-compare.py').read_bytes());d['comparison_ref']=put(canon(c))
    (bundle/'definition.json').write_bytes(canon(d));(bundle/'SYNTHETIC-ONLY.txt').write_text('Generated corporate data; E references pinned local real OCI runtime and lab theme. No cloud storage proof.\n')
    run('php',str(ROOT/'tools/rbr-plan.php'),'--definition='+str(bundle/'definition.json'),'--objects='+str(bundle/'cache'),'--output='+str(bundle/'plan.json'))
    q=read(d['expected_ref']);(out/'expected.json').write_bytes(canon(q))
    # No original intake files / local S3-double state in mounted bundle.
    inputs=out/'inputs';inputs.mkdir();shutil.copytree(bundle/'cache',inputs/'cache')
    for name in ['definition.json','plan.json']:shutil.copyfile(bundle/name,inputs/name)
    os.chmod(inputs,0o755);os.chmod(inputs/'cache',0o755)
    for p in inputs.rglob('*'):
        if p.is_file():p.chmod(0o444)
    if not prepare_only: execute(out,inputs)

def execute(out,inputs):
    def read(ref):return json.loads((inputs/'cache'/(ref['sha256']+'.blob')).read_bytes())
    d=json.loads((inputs/'definition.json').read_bytes());e=read(d['environment_ref']);c=read(d['comparison_ref']);q=read(d['expected_ref'])
    wp=read(e['packages']['wordpress']['artifact_ref'])['image_id'];db=read(e['packages']['database']['artifact_ref'])['image_id'];theme=read(e['packages']['theme']['artifact_ref'])
    (out/'expected.json').write_bytes(canon(q))
    assert (ROOT/'tools/rbr-compare.py').read_bytes()==(inputs/'cache'/(c['extractor_ref']['sha256']+'.blob')).read_bytes()
    spec=importlib.util.spec_from_file_location('comparison',ROOT/'tools/rbr-compare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    results=[];states=[];negative=[]
    for iteration in [1,2]:
        prefix='owr-rbr-'+uuid.uuid4().hex[:10];network=prefix+'-net';dbn=prefix+'-db';web=prefix+'-wp';origin='http://'+web
        folder=out/('run'+str(iteration));folder.mkdir();created=[]
        try:
            import ipaddress
            ids=run('docker','network','ls','-q').stdout.decode().split()
            used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in (n['IPAM']['Config'] or []) if 'Subnet' in c]
            subnet=next(str(n) for n in ipaddress.ip_network('10.253.0.0/16').subnets(new_prefix=28) if not any(n.overlaps(u) for u in used if n.version==u.version))
            run('docker','network','create','--internal','--subnet',subnet,network);created.append(('network',network))
            run('docker','run','-d','--name',dbn,'--network',network,'--memory','512m','--cpus','1','--pids-limit','256','--tmpfs','/var/lib/mysql:rw','-e','MARIADB_ROOT_PASSWORD=lab-only','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress','-e','MARIADB_PASSWORD=lab-only',db);created.append(('container',dbn))
            run('docker','run','-d','--name',web,'--network',network,'--memory','512m','--cpus','1','--pids-limit','256','--tmpfs','/var/www/html:rw','-e','OWR_RBR_DISPOSABLE=1','-e','WORDPRESS_DB_HOST='+dbn,'-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD=lab-only','-e','WORDPRESS_DB_NAME=wordpress','-e','WORDPRESS_DB_COLLATE=utf8mb4_unicode_ci','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true); define('WP_HTTP_BLOCK_EXTERNAL',true); define('DISALLOW_FILE_MODS',true); define('WP_POST_REVISIONS',false);",'-v',str(ROOT)+':/kit:ro','-v',str(inputs)+':/bundle:ro',wp);created.append(('container',web))
            def php(code,check=True):return run('docker','exec','-i',web,'php',input=('<?php '+code).encode(),check=check)
            for attempt in range(60):
                ready=php("$m=@new mysqli(getenv('WORDPRESS_DB_HOST'),'wordpress','lab-only','wordpress');exit($m->connect_errno?1:0);",False)
                if ready.returncode==0 and run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode==0:break
                time.sleep(1)
            else:raise RuntimeError('Lab readiness timeout')
            # Check actual immutable images and absence of host ports before enabling application writes.
            for name,image in [(web,wp),(dbn,db)]:
                info=json.loads(run('docker','inspect',name).stdout)[0];assert info['Image']==image and not info['HostConfig']['PortBindings'];assert set(info['NetworkSettings']['Networks'])=={network}
            assert json.loads(run('docker','network','inspect',network).stdout)[0]['Internal']
            routes=run('docker','exec',web,'cat','/proc/net/route').stdout.decode()
            assert not any(line.split()[1]=='00000000' for line in routes.splitlines()[1:] if line.split()), 'Unexpected default route'
            (folder/'routes.txt').write_text(routes)
            run('docker','exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins','/var/www/html/wp-content/themes/rbr-lab')
            for name,content in theme.items():php('file_put_contents('+json.dumps('/var/www/html/wp-content/themes/rbr-lab/'+name)+','+lit(content)+');')
            guard=folder/'guard.php';guard.write_text("<?php function rbr_block(){update_option('rbr_side_effect_attempts',1+(int)get_option('rbr_side_effect_attempts',0));update_option('rbr_attempt_trace',array_column(debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS),'function'));} add_filter('pre_wp_mail',function(){rbr_block();return false;}); add_filter('pre_http_request',function(){rbr_block();return new WP_Error('blocked');});")
            php('file_put_contents("/var/www/html/wp-content/mu-plugins/rbr-guard.php",'+lit(guard.read_text())+');')
            install=php("""define('WP_INSTALLING',true);require '/var/www/html/wp-load.php';require ABSPATH.'wp-admin/includes/upgrade.php';wp_install('RBR private lab','operator','operator@example.invalid',false,'','lab-only-password');global $wpdb;foreach($wpdb->get_col("SELECT ID FROM {$wpdb->posts}")as $id)wp_delete_post($id,true);$wpdb->query('ALTER TABLE '.$wpdb->posts.' AUTO_INCREMENT = '. """+str(iteration*100)+""" );update_option('home',"""+repr(origin)+""");update_option('siteurl',"""+repr(origin)+""");update_option('timezone_string','UTC');update_option('active_plugins',[]);update_option('cron',[]);update_option('rbr_bootstrap_attempts',(int)get_option('rbr_side_effect_attempts',0));update_option('rbr_side_effect_attempts',0);update_option('rbr_attempt_trace',[]);switch_theme('rbr-lab');""")
            # Installation mail is deliberately blocked; reset above separates bootstrap from F's effect window.
            apply=run('docker','exec',web,'php','/kit/tools/rbr-wordpress-apply.php');(folder/'receipt.json').write_bytes(apply.stdout);assert json.loads(apply.stdout)['state']=='applied-private'
            duplicate=run('docker','exec',web,'php','/kit/tools/rbr-wordpress-apply.php',check=False);assert duplicate.returncode!=0
            obs=json.loads(run('docker','exec',web,'php','/kit/tools/rbr-wordpress-observe.php').stdout)
            # WordPress authentication cookie is generated through WordPress, never a public preview bypass.
            cookie=php("require '/var/www/html/wp-load.php';echo LOGGED_IN_COOKIE.'='.wp_generate_auth_cookie(1,time()+600,'logged_in');").stdout.decode()
            def http(path,authenticated=True):
                code="$c=curl_init("+lit(origin+path)+");curl_setopt($c,CURLOPT_RETURNTRANSFER,true);"+("curl_setopt($c,CURLOPT_COOKIE,"+lit(cookie)+");" if authenticated else '')+"$b=curl_exec($c);echo json_encode(['status'=>curl_getinfo($c,CURLINFO_HTTP_CODE),'body'=>base64_encode($b)]);"
                import base64
                v=json.loads(php(code).stdout);return v['status'],base64.b64decode(v['body'])
            htmls={};media={}
            for row in obs['rows']:
                if row['type']=='page':
                    path='/?page_id='+str(row['id']);status,body=http(path);assert status==200,(status,body[:200]);htmls[row['asset_id']]=body.decode();assert http(path,False)[0]==403
                else:
                    from urllib.parse import urlsplit
                    status,body=http(urlsplit(row['url']).path);assert status==200;media[row['asset_id']]=body
            status,landing=http('/');assert status==200 and landing.decode()==htmls[obs['landing']]
            # Read again after serving: no unexpected WP HTTP/mail attempts or execution state changes.
            obs=json.loads(run('docker','exec',web,'php','/kit/tools/rbr-wordpress-observe.php').stdout)
            (folder/'observation.json').write_bytes(canon(obs));(folder/'served.json').write_bytes(canon(htmls));assert obs['runtime']['collation']==e['settings']['collation'] and obs['runtime']['timezone']==e['settings']['timezone'] and obs['runtime']['locale']==e['settings']['locale'];logical=module.compare(obs,htmls,media,q,origin);states.append(logical)
            (folder/'observation.json').write_bytes(canon(obs));(folder/'logical.json').write_bytes(canon(logical));(folder/'served.json').write_bytes(canon(htmls))
            for asset,raw in media.items():(folder/(asset+'.image')).write_bytes(raw)
            # Mutate actual stored DB/media and render again; a comparator that copies P/Q cannot pass these controls.
            if iteration==1:
                mutations=[('contact-character',"UPDATE {p} SET post_content=REPLACE(post_content,'TEST-0001','TEST-0002') WHERE ID="+str(obs['map']['contact'])),('paragraph-order',"UPDATE {p} SET post_content='<p>Telephone: TEST-0001</p><p>Email: contact@example.invalid</p><nav class=related></nav>' WHERE ID="+str(obs['map']['contact'])),('link-target',"UPDATE {p} SET post_content=REPLACE(post_content,'page_id="+str(obs['map']['services'])+"','page_id="+str(obs['map']['contact'])+"') WHERE ID="+str(obs['map']['company']))]
                for name,sql in mutations:
                    php("require '/var/www/html/wp-load.php';global $wpdb;$wpdb->query(str_replace('{p}',$wpdb->posts,"+lit(sql)+"));")
                    bad=json.loads(run('docker','exec',web,'php','/kit/tools/rbr-wordpress-observe.php').stdout);bh={a:http('/?page_id='+str(row['id']))[1].decode() for a,row in [(x['asset_id'],x) for x in bad['rows'] if x['type']=='page']}
                    try:module.compare(bad,bh,media,q,origin)
                    except (AssertionError,KeyError,ValueError):negative.append(name)
                    else:raise RuntimeError('Negative control accepted: '+name)
                    for row in obs['rows']:
                        if row['type']=='page':php("require '/var/www/html/wp-load.php';global $wpdb;$wpdb->update($wpdb->posts,['post_content'=>"+lit(row['body'])+"],['ID'=>"+str(row['id'])+"]);")
                php("require '/var/www/html/wp-load.php';unlink(get_attached_file("+str(obs['map']['logo'])+"));")
                imageurl=next(x['url'] for x in obs['rows'] if x['type']=='attachment');assert http(urlsplit(imageurl).path)[0]!=200;negative.append('missing-image-http')
            results.append({'run':iteration,'matched_Q':True,'logical_sha256':digest(canon(logical)),'actual_runtime':obs['runtime'],'private_routes':True,'duplicate_rejected':True,'side_effect_attempts':obs['side_effect_attempts']})
        finally:
            for kind,name in reversed(created):
                if kind=='container':run('docker','rm','-f','-v',name)
                else:run('docker','network','rm',name)
    assert states[0]==states[1] and results[0]['actual_runtime']==results[1]['actual_runtime']
    report={'state':'PASS','scope':'generated-only, local pinned OCI, no S3 calls or production','runs':results,'negative_controls':negative,'definition_sha256':digest((inputs/'definition.json').read_bytes()),'plan_sha256':digest((inputs/'plan.json').read_bytes()),'images':{'wordpress_php':wp,'database':db},'resources_removed':True,'public_activation':False}
    (out/'result.json').write_bytes(canon(report));print(json.dumps(report))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-disposable-lab',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--bundle',type=Path);a=p.parse_args()
    if not a.allow_disposable_lab:p.error('Explicit disposable lab opt-in required')
    try:
        if a.bundle:
            a.output.resolve().mkdir(mode=0o700);execute(a.output.resolve(),a.bundle.resolve())
        else:main(a.output.resolve(),a.prepare_only)
    except Exception as exc:
        if a.output.is_dir(): (a.output/'failure.json').write_text(json.dumps({'state':'FAIL','error_type':type(exc).__name__,'error':str(exc)}))
        raise
