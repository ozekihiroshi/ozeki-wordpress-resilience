"""Generated two-asset capture -> real fixed S3 versions -> operator signature -> offline restore."""
import importlib.util,json,secrets,subprocess,tempfile,time,hashlib,tarfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(db,web,php,sql,hold,ready,release,run,check,results,output):
    capture=load('capture','first-site-capture.py');g=load('first_gate','protected-first-site-set.py');t=load('transport','queue-s3-adapter.py')
    # Capture generated assets once; unrelated negative cases use the separate capture lab.
    load('capture_cases','first-site-s3-capture.py').exercise(db,web,php,sql,hold,ready,release,run,check,results,output)
    root=output.parent/(output.stem+'-private')
    accepted=[p for p in root.glob('*/result.json') if json.loads(p.read_text())['state']=='consistent']
    check(len(accepted)==1,'ambiguous captured generation')
    c=json.loads(accepted[0].read_text());work=accepted[0].parent
    assets={k:(work/v['path']).read_bytes() for k,v in c['assets'].items()}
    g.validate_capture(c,assets);check(sum(map(len,assets.values()))<=128*1024**2,'transfer budget')
    set_id='AWS-'+secrets.token_hex(8);site='isolated-queue-lab';prefix=f'sites/{site}/sets/{set_id}/'
    report={'set_id':set_id,'source_site':c['site_id'],'passed':False,'production_data':False,'production_key':False,'stages':[]}
    def save():capture.write_json(root/'s3-result.json',report)
    def passed(case):report['stages'].append(case);save();results.append({'case':case,'passed':True});print(case,flush=True)
    save();report['preflight']=t.preflight();save()
    adapter=t.S3Adapter(root/'s3-receipts')
    manifest=g.build(assets,c,site,set_id,t.BUCKET,t.REGION,'my-ssm-role','OwrM1RecoveryReader',adapter.put,adapter.get)
    passed('two_assets_fixed_versions_reader_retention_35_days')
    candidate=root/'candidate.json';candidate.write_bytes(g.encode(manifest))
    operator=Path.home()/'.local/share/owr-first-site-s3-operator'/set_id
    subprocess.run(['python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',str(candidate),'--operator',str(operator)],check=True,timeout=60,capture_output=True)
    doc=operator/'approved.json';sig=operator/'approved.sig';g.authorize(operator,doc,sig,site,set_id)
    pin=json.loads((operator/'pin.json').read_text())
    for role,path,name in [('document',doc,'recovery-set.json'),('signature',sig,'recovery-set.sig')]:
        body=path.read_bytes();loc={'bucket':t.BUCKET,'region':t.REGION,'key':prefix+name,'version_id':adapter.put(t.BUCKET,prefix+name,body),'size_bytes':len(body),'sha256':g.sha(body),'writer_identity':'my-ssm-role'}
        observed=g.observe('database',body,loc,adapter.get(loc),'OwrM1RecoveryReader');pin['envelope'][role]={'locator':loc,'retention':observed['retention']}
    capture.write_json(operator/'pin.json',pin)
    passed('separate_operator_process_signed_and_pinned_envelope')
    doc,sig=g.fetch_envelope(operator,adapter.get,root/'downloaded-envelope')
    bad=root/'bad.sig';bad.write_bytes(b'invalid');before=adapter.request_count
    try:g.fetch_verified(operator,doc,bad,site,set_id,c['config_sha256'],adapter.get)
    except ValueError:pass
    else:raise ValueError('bad signature accepted')
    check(adapter.request_count==before,'download before signature rejection')
    passed('bad_signature_rejected_before_asset_download')
    fetched,verified=g.fetch_verified(operator,doc,sig,site,set_id,c['config_sha256'],adapter.get)
    check(fetched==assets,'bytes differ')
    restored=root/'verified-assets';restored.mkdir(mode=0o700)
    for role,name in g.NAMES.items():(restored/name).write_bytes(fetched[role])
    check(capture.digest(capture.archive_inventory(restored/g.NAMES['files'],512*1024**2))==c['inventory_sha256'],'archive capture inventory mismatch')
    passed('signed_fixed_versions_and_capture_binding_verified')
    # Restore only after both assets pass; source data are never mounted into target.
    names=[];rdb='owr-first-restore-'+secrets.token_hex(5)+'-db';rweb=rdb[:-3]+'-web'
    images=dict(x.split('=',1) for x in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in x)
    env=json.loads(run('docker','inspect',db).stdout)[0]['Config']['Env']
    try:
        with tempfile.TemporaryDirectory(prefix='owr-restore-env-') as tmp:
            e=Path(tmp)/'env';e.write_text('\n'.join(x for x in env if x.startswith(('MARIADB_','WORDPRESS_','LAB_')))+'\n');e.chmod(0o600)
            run('docker','run','-d','--name',rdb,'--label','owr.first-site-s3=generated','--network','none','--memory','512m','--env-file',str(e),images['OWR_DB_IMAGE']);names.append(rdb)
            end=time.monotonic()+90
            while run('docker','exec',rdb,'healthcheck.sh','--connect','--innodb_initialized',must=False).returncode:
                check(time.monotonic()<end,'restore DB startup');time.sleep(1)
            run('docker','exec','-i',rdb,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot lab',input=fetched['database'])
            run('docker','run','-d','--name',rweb,'--label','owr.first-site-s3=generated','--network','container:'+rdb,'--memory','512m','--env-file',str(e),images['OWR_WP_IMAGE']);names.append(rweb)
            end=time.monotonic()+90
            while run('docker','exec',rweb,'test','-f','/var/www/html/wp-config.php',must=False).returncode:
                check(time.monotonic()<end,'restore WP startup');time.sleep(1)
            run('docker','exec','-i',rweb,'tar','xzf','-','-C','/var/www/html','--no-same-owner',input=fetched['files'])
            run('docker','exec',rweb,'chown','-R','www-data:www-data','/var/www/html')
            inspected=json.loads(run('docker','inspect',rdb,rweb).stdout)
            check(inspected[0]['HostConfig']['NetworkMode']=='none' and inspected[1]['HostConfig']['NetworkMode'].startswith('container:') and all(not x['HostConfig']['PortBindings'] for x in inspected),'restore isolation')
            code="require '/var/www/html/wp-load.php';global $wpdb;echo json_encode(['post'=>(int)$wpdb->get_var(\"SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_title='First site normal post'\"),'attachment'=>$wpdb->get_var(\"SELECT meta_value FROM {$wpdb->postmeta} WHERE meta_key='_wp_attached_file'\"),'media'=>hash_file('sha256',WP_CONTENT_DIR.'/uploads/one.png')]);"
            v=json.loads(run('docker','exec','-u','www-data',rweb,'php','-r',code).stdout)
            check(v['post']==1 and v['attachment']=='one.png','restored DB semantics')
            inv=capture.archive_inventory(restored/g.NAMES['files'],512*1024**2);check(v['media']==inv['wp-content/uploads/one.png'],'restored media')
            http=run('docker','exec',rweb,'php','-r',"$c=curl_init('http://127.0.0.1/');curl_setopt($c,CURLOPT_RETURNTRANSFER,true);$b=curl_exec($c);echo json_encode(['status'=>curl_getinfo($c,CURLINFO_HTTP_CODE),'post'=>strpos($b,'First site normal post')!==false]);").stdout
            h=json.loads(http);check(h['status']==200 and h['post'],'restored HTTP content')
            passed('fresh_offline_wordpress_database_media_and_http_restored')
    finally:
        for name in reversed(names):run('docker','rm','-f','-v',name)
    report.update(passed=True,verification=verified,requests=adapter.request_count,retention_until=manifest['minimum_retention_until'],operator_trust=str(operator),resources_removed=all(run('docker','inspect',n,must=False).returncode!=0 for n in names),signer_boundary='separate process/directory and separate EC2 transport roles; same WSL user, not host isolation',production_recovery_approved=False)
    save()
