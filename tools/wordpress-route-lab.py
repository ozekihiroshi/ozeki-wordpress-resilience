"""Dedicated lab route coverage and evidence adapter; never a production scope declaration."""
import copy
import hashlib
import importlib.util
import io
import json
import secrets
from pathlib import Path
import subprocess as sp
import tarfile
import time

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_WRITERS=['php-http','php-cli-file','database-direct']

def run_routes(db,web,php,sql,hold,ready,release,results,run,check):
    def client(action, asynchronous=False):
        cmd=['docker','exec','-u','www-data','-e','OWR_ROUTE_ACTION='+action,web,'php','-r',"require '/lab/route-client.php';"]
        if asynchronous:return sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.PIPE)
        return json.loads(run(*cmd).stdout)

    def inventory():
        return json.loads(php("$a=[]; $base='/var/www/html/'; foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base,FilesystemIterator::SKIP_DOTS)) as $f) { if($f->isLink()) throw new Exception('unsupported link'); if($f->isFile()) { $v=hash_file('sha256',$f->getPathname()); if($v===false) throw new Exception('unreadable file'); $a[substr($f->getPathname(),strlen($base))]=$v; }} ksort($a); echo json_encode($a);"))

    def generation():return int(php("echo file_get_contents('/tmp/owr-route-generation');"))
    def token_now():return php("echo file_get_contents('/tmp/owr-gate.fence');").decode()
    def schema():return sql("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='lab' ORDER BY TABLE_NAME;")
    def mark(name,**data):results.append({'case':name,'passed':True,**data})
    def await_file(path):
        deadline=time.monotonic()+10
        while php(f"echo file_exists('{path}') ? 'yes' : 'no';")!=b'yes':
            check(time.monotonic()<deadline,'active request not observed');time.sleep(.05)

    # Configure before starting any route writers. Helper PHP -r is a privileged lab observer.
    sql("UPDATE wp_options SET option_value='http://127.0.0.1' WHERE option_name IN ('siteurl','home');")
    run('docker','exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins')
    for source,target in [('route-fixture.php','/var/www/html/wp-content/mu-plugins/route-fixture.php'),('route-nonce.php','/var/www/html/route-nonce.php')]:
        run('docker','exec',web,'cp','/lab/'+source,target)
    run('docker','exec',web,'sh','-c',"printf 'auto_prepend_file=/lab/route-prepend.php\n' > /usr/local/etc/php/conf.d/owr-route-gate.ini")
    run('docker','exec',web,'apachectl','-k','graceful')
    # Graceful restart may briefly serve an old worker. Observe configured HTTP SAPI before proceeding.
    deadline=time.monotonic()+15
    while client('setup').get('prepend')!='/lab/route-prepend.php':
        check(time.monotonic()<deadline,'Apache prepend not active');time.sleep(.2)
    cli_config=php("echo ini_get('auto_prepend_file');")==b'/lab/route-prepend.php'
    check(cli_config,'CLI prepend missing')
    for action,status in [('admin',302),('rest',201),('media',201),('ajax',200)]:
        response=client(action);check(response['status']==status,f'{action} failed: {response}')
    check(int(sql("SELECT COUNT(*) FROM wp_posts WHERE post_title='Admin route' AND post_status='publish';"))==1,'admin form did not write')
    check(int(sql("SELECT COUNT(*) FROM wp_posts WHERE post_title='REST route' AND post_status='publish';"))==1,'REST did not write')
    check(int(sql("SELECT COUNT(*) FROM wp_terms WHERE name LIKE 'Route %';"))==1,'AJAX did not write')
    check(int(sql("SELECT COUNT(*) FROM wp_posts WHERE post_type='attachment';"))==1,'media upload did not write')
    check(run('docker','exec','-u','www-data',web,'php','/lab/route-cli.php').stdout==b'written','CLI failed')
    mark('real_admin_rest_media_ajax_cli_writes')

    php("require '/var/www/html/wp-load.php'; wp_schedule_single_event(time()-1,'owr_route_tick');")
    active=client('cron',True);await_file('/tmp/owr-route-cron-active')
    start=time.monotonic();p,token=hold(wait=10,lease=180)
    # Reject a new request while the older cron request is still draining.
    rejected=client('rest');check(rejected['status']==503 and rejected['fenced'],'REST admitted during drain')
    ready(p);elapsed=time.monotonic()-start
    out,err=active.communicate(timeout=10);check(active.returncode==0,'cron client failed')
    check(sql("SELECT option_value FROM wp_options WHERE option_name='owr_route_cron_count';").strip()==b'1','cron callback did not finish')
    check(elapsed>1,'did not drain actual cron')
    mark('real_cron_drained_new_rest_rejected',wait_seconds=round(elapsed,3))

    gen_before=generation();before=inventory();schema_before=schema()
    check(all(line.endswith(b'\tInnoDB') for line in schema_before.splitlines()),'unsupported table engine')
    observed=[]
    for action in ['admin','rest','media','ajax','cron','public']:
        response=client(action)
        check(response['status']==503 and response['fenced'],f'{action} not fenced')
        observed.append(action)
    cli=run('docker','exec','-u','www-data',web,'php','/lab/route-cli.php',must=False)
    check(cli.returncode==3 and b'fenced' in cli.stdout,'CLI not fenced')
    ddl=run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot lab',input=b'SET SESSION lock_wait_timeout=1; CREATE TABLE owr_forbidden_ddl(id INT);',must=False)
    check(ddl.returncode!=0 and b'1205' in ddl.stderr,'DDL not blocked')
    mark('all_real_php_routes_and_ddl_fenced',http_routes=observed)
    other_routes=['xmlrpc','comments','admin-post','async-upload','login','update']
    for action in other_routes:
        response=client(action)
        check(response['status']==503 and response['fenced'],action+' entrypoint escaped gate')
    mark('additional_php_entrypoints_rejected_before_wordpress',routes=other_routes)

    dump=run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --skip-lock-tables lab').stdout
    archive=run('docker','exec',web,'tar','-czf','-','-C','/var/www/html','.').stdout
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
        captured={m.name.removeprefix('./'):hashlib.sha256(tar.extractfile(m).read()).hexdigest() for m in tar.getmembers() if m.isfile()}
    after=inventory();gen_after=generation();schema_after=schema()
    attachment_paths=sql("SELECT meta_value FROM wp_postmeta WHERE meta_key='_wp_attached_file' ORDER BY meta_value;").decode().splitlines()
    references=bool(attachment_paths) and all('wp-content/uploads/'+name in captured for name in attachment_paths)
    end_token=token_now();held=p.poll() is None and end_token==token
    release(p,token)
    # Restore the captured DB into a distinct schema, and compare its media references after release.
    sql('CREATE DATABASE route_restored;')
    run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot route_restored',input=dump)
    restored=sql("SELECT meta_value FROM route_restored.wp_postmeta WHERE meta_key='_wp_attached_file' ORDER BY meta_value;").decode().splitlines()
    references=references and attachment_paths==restored
    attempt='lab-route-'+secrets.token_hex(8);site='isolated-wordpress-route-lab'
    record={'format':'owr-capture-consistency-v1','attempt_id':attempt,'site_id':site,
       'generation_before':gen_before,'generation_after':gen_after,'file_inventory_before':before,
       'file_inventory_after':after,'captured_file_inventory':captured,
       'assets':{key:{'site_id':site,'attempt_id':attempt,'completed':True,'exit_code':0,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for key,data in [('database',dump),('files',archive)]},
       'release_confirmed':not php("echo file_exists('/tmp/owr-gate.fence') ? 'yes' : '';"),
       'references_match':references,'barrier':{'scope_complete':cli_config and len(observed)==6,
          'writers':{name:{'fenced':True,'inflight':0} for name in EXPECTED_WRITERS},'token':token,'held_through_verification':held},
       'end_token':end_token,'phases':['fence','drain','snapshot','copy','verify','release'],
       'db_snapshot_consistent':True,'schema_stable':schema_before==schema_after,
       'scope_profile':'isolated-lab-controlled-php-v1'}
    spec=importlib.util.spec_from_file_location('assessor',ROOT/'tools/capture-consistency.py')
    assessor=importlib.util.module_from_spec(spec);spec.loader.exec_module(assessor)
    assessment=assessor.assess(record,EXPECTED_WRITERS)
    check(assessment['state']=='consistent',f'capture rejected: {assessment}')
    mark('real_capture_connected_to_consistency_assessor',assessment=assessment,files=len(captured),restored_media_references=len(restored))

    # Real unmanaged file write under the DB/PHP barrier must invalidate acceptance.
    p,token=hold(lease=60);ready(p)
    negative=copy.deepcopy(record);negative['file_inventory_before']=inventory()
    run('docker','exec',web,'sh','-c',"printf 'unmanaged write' > /var/www/html/wp-content/uploads/unmanaged.txt")
    negative['file_inventory_after']=inventory()
    release(p,token)
    changed=assessor.assess(negative,EXPECTED_WRITERS)
    check(changed['state']=='inconsistent','unmanaged file mutation accepted')
    unknown=assessor.assess(record,EXPECTED_WRITERS+['unmanaged-ssh'])
    check(unknown['state']=='unverified','unknown writer accepted')
    missing=copy.deepcopy(record);missing['barrier']['scope_complete']=False
    unconfigured=assessor.assess(missing,EXPECTED_WRITERS)
    check(unconfigured['state']=='unverified','incomplete route coverage accepted')
    mark('negative_file_mutation_and_unknown_writer_rejected',mutation=changed['state'],unknown_writer=unknown['state'],missing_gate=unconfigured['state'])

    p,token=hold(lease=2);ready(p)
    p.wait(timeout=8)
    events=[json.loads(line)['state'] for line in p.stdout.read().splitlines()]
    check(events==['lease_expired','released'],'lease expiry not observed')
    expired=copy.deepcopy(record);expired['barrier']['held_through_verification']=False
    expired_assessment=assessor.assess(expired,EXPECTED_WRITERS)
    check(expired_assessment['state']=='unverified','expired capture accepted')
    check(client('rest')['status']==201,'REST did not resume after lease expiry')
    mark('real_route_lease_expiry_releases_and_rejects_acceptance',assessment=expired_assessment)

    # PHP shutdown work is still in-flight even after WordPress has emitted its response.
    active=client('shutdown',True);await_file('/tmp/owr-route-shutdown-active')
    start=time.monotonic();p,token=hold(wait=10,lease=60);ready(p)
    elapsed=time.monotonic()-start;active.communicate(timeout=10)
    check(active.returncode==0 and elapsed>1,'shutdown callback escaped drain')
    check(sql("SELECT option_value FROM wp_options WHERE option_name='owr_route_shutdown_done';").strip()==b'yes','shutdown write not completed')
    release(p,token);mark('php_shutdown_callback_drained',wait_seconds=round(elapsed,3))
    for action,status in [('admin',302),('rest',201),('media',201),('ajax',200)]:
        check(client(action)['status']==status,action+' did not resume')
    php("require '/var/www/html/wp-load.php'; wp_schedule_single_event(time()-1,'owr_route_tick');")
    check(client('cron')['status']==200,'cron did not resume')
    deadline=time.monotonic()+10
    while sql("SELECT option_value FROM wp_options WHERE option_name='owr_route_cron_count';").strip()!=b'2':
        check(time.monotonic()<deadline,'resumed cron not completed');time.sleep(.1)
    check(run('docker','exec','-u','www-data',web,'php','/lab/route-cli.php').stdout==b'written','CLI did not resume')
    mark('real_routes_resume_after_release')
    return {'assessment':assessment,'observation':record,'expected_writers':EXPECTED_WRITERS,
       'scope_profile':'isolated-lab-controlled-php-v1','production_scope_complete':False,
       'excluded':['php -r/-n/config overrides','SSH/deployment/file writers','arbitrary plugin subprocesses','external storage/queues'],
       'note':'Admission pauses all PHP HTTP including GET. This is a lab-scoped evidence adapter, not production approval.'}
