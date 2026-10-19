"""Actual paired restore inside the disposable, network-isolated WordPress lab."""
import copy,importlib.util,json,secrets,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pair',ROOT/'tools/queue-recovery.py')
pair=importlib.util.module_from_spec(spec);spec.loader.exec_module(pair)
def exercise(db,web,broker,worker,php,sql,hold,ready,release,run,check,queue,enqueue,completed,wait_for,mark,ssh_call,s3_lab=False,s3_resume_set=None,daily_s3_stage=None,approved_restore=None):
    run('docker','stop',worker)
    # A real committed job whose ACK never reaches the broker.
    enqueue('recovery-unacked');check(ssh_call('write recovery-unacked').returncode==0,'unacked execution')
    enqueue('recovery-pending')
    # A conflicting effect is deliberately quarantined rather than retried forever.
    check(ssh_call('write recovery-conflict').returncode==0,'conflict seed')
    enqueue('recovery-conflict','deploy')
    checkpoint=secrets.token_hex(16)
    queue('/freeze',{'checkpoint':checkpoint})
    def rejected(path,data):
        try:queue(path,data)
        except RuntimeError:return True
        return False
    check(rejected('/enqueue',{'id':'late','kind':'write'}) and rejected('/ack',{'id':'recovery-unacked'}),'frozen mutation accepted')
    check(queue('/jobs')==[],'frozen dispatch exposed')
    mark('paired_checkpoint_blocks_enqueue_ack_and_delivery')
    sql('CREATE TABLE owr_queue_checkpoint(id INT PRIMARY KEY,checkpoint CHAR(32) NOT NULL) ENGINE=InnoDB;')
    sql("INSERT INTO owr_queue_checkpoint VALUES(1,'"+checkpoint+"');")
    p,token=hold(lease=180);ready(p)
    try:
        dump=run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --skip-lock-tables lab').stdout
        archive=run('docker','exec',web,'tar','-czf','-','-C','/var/www/html','.').stdout
        run('docker','exec',broker,'python3','-c',"import sqlite3;src=sqlite3.connect('/queue/jobs.sqlite');dst=sqlite3.connect('/tmp/checkpoint.sqlite');src.backup(dst);dst.close();src.close()")
        snapshot=run('docker','exec',broker,'cat','/tmp/checkpoint.sqlite').stdout
        check(p.poll() is None and queue('/control')['checkpoint']==checkpoint,'checkpoint expired')
    finally:release(p,token)
    assets={'database':dump,'files':archive,'queue':snapshot}
    handler=pair.digest((ROOT/'lab/consistency/external-job.php').read_bytes())
    manifest={'format':pair.FORMAT,'site_id':'isolated-queue-lab','checkpoint':checkpoint,'handler_sha256':handler,'assets':{k:pair.digest(v) for k,v in assets.items()}}
    check(pair.validate(manifest,assets,manifest['site_id'],handler)==checkpoint,'pair validation')
    mark('database_files_and_queue_captured_as_one_checkpoint')
    def denied(m,a,site=manifest['site_id'],h=handler):
        try:pair.validate(m,a,site,h)
        except ValueError:return True
        return False
    for key in assets:
        altered=dict(assets);altered[key]+=b'changed';check(denied(manifest,altered),'altered '+key+' accepted')
    mixed=copy.deepcopy(manifest);mixed['checkpoint']=secrets.token_hex(16)
    check(denied(mixed,assets) and denied(manifest,assets,'other-site') and denied(manifest,assets,h='0'*64),'mixed recovery accepted')
    mark('mixed_generation_corrupt_assets_wrong_site_and_handler_rejected')
    run('docker','restart',broker)
    wait_for(lambda:run('docker','exec',broker,'python3','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/control')",must=False).returncode==0,'checkpoint broker restart')
    check(queue('/control')['checkpoint']==checkpoint and queue('/jobs')==[],'restart lost freeze')
    check(rejected('/resume',{'checkpoint':secrets.token_hex(16)}),'wrong resume token')
    mark('checkpoint_survives_broker_restart_and_wrong_resume_is_denied')
    if daily_s3_stage is not None:
        spec=importlib.util.spec_from_file_location('daily_publish',ROOT/'tools/daily-s3-publication.py')
        publication=importlib.util.module_from_spec(spec);spec.loader.exec_module(publication)
        saved=publication.publish(assets,manifest,daily_s3_stage,mark)
        return {'format':pair.FORMAT,'saved_set':saved,'manifest':manifest,'production_recovery_approved':False,'restore_performed':False}
    spec=importlib.util.spec_from_file_location('protected_lab',ROOT/('tools/protected-queue-s3-lab.py' if s3_lab else 'tools/protected-queue-lab.py'))
    protected=importlib.util.module_from_spec(spec);spec.loader.exec_module(protected)
    if approved_restore is not None:
        spec=importlib.util.spec_from_file_location('approved_restore_gate',ROOT/'tools/approved-queue-restore.py')
        approved=importlib.util.module_from_spec(spec);spec.loader.exec_module(approved)
        assets,signed_evidence,manifest=approved.fetch(mark=mark,**approved_restore)
        checkpoint=manifest['checkpoint']
    elif s3_lab and s3_resume_set:
        assets,signed_evidence,manifest=protected.resume(s3_resume_set,mark)
        checkpoint=manifest['checkpoint']
    else:
        assets,signed_evidence=protected.exercise(assets,manifest,mark)
    dump,archive,snapshot=assets['database'],assets['files'],assets['queue']
    # Simulate loss of queue storage, DB effects and one file in this disposable lab only.
    run('docker','stop',broker)
    mounts=json.loads(run('docker','inspect',broker).stdout)[0]['Mounts']
    volume=next(m['Name'] for m in mounts if m['Destination']=='/queue')
    image=json.loads(run('docker','inspect',broker).stdout)[0]['Image']
    # Restore is allowed only after all three byte hashes and queue checkpoint pass.
    pair.validate(manifest,assets,manifest['site_id'],handler)
    run('docker','run','--rm','-i','--network','none','--read-only','--cap-drop','ALL','--user','1000:1000','-v',volume+':/queue','--entrypoint','python3',image,'-c',"import sys;from pathlib import Path;p=Path('/queue/jobs.sqlite');p.unlink();p.write_bytes(sys.stdin.buffer.read())",input=snapshot)
    sql("DELETE FROM wp_posts WHERE post_title='External recovery-unacked';DELETE FROM owr_external_jobs WHERE job_id='recovery-unacked';")
    run('docker','exec',web,'rm','/var/www/html/wp-content/uploads/external-recovery-unacked.txt')
    run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot lab',input=dump)
    if s3_resume_set or approved_restore is not None:
        # Remove only this run's disposable site contents before restoring an older set.
        check(web.startswith('owr-consistency-'),'unexpected restore container')
        run('docker','exec',web,'python3','-c',"from pathlib import Path;import shutil;r=Path('/var/www/html');assert r.resolve()==r;[(shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()) for p in r.iterdir()]")
    run('docker','exec','-i',web,'tar','-xzf','-','-C','/var/www/html',input=archive)
    if s3_resume_set or approved_restore is not None:
        import io,tarfile
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
            expected_files={m.name.removeprefix('./'):pair.digest(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
        resumed_file_inventory=json.loads(php("$a=[];$base='/var/www/html/';foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base,FilesystemIterator::SKIP_DOTS)) as $f){if($f->isLink())throw new Exception('link');if($f->isFile())$a[substr($f->getPathname(),strlen($base))]=hash_file('sha256',$f->getPathname());}echo json_encode($a);"))
        check(resumed_file_inventory==expected_files,'restored file set differs from signed archive')
    if approved_restore is not None:
        mark('approved_complete_file_inventory_matches')
        isolated=json.loads(run('docker','inspect',db,web,broker,worker).stdout)
        db_id=isolated[0]['Id']
        check(isolated[0]['HostConfig']['NetworkMode']=='none' and all(not x['HostConfig']['PortBindings'] for x in isolated),'restore network/ports')
        check(all(x['HostConfig']['NetworkMode'] in ('container:'+db,'container:'+db_id) for x in isolated[1:]),'restore network namespace')
        mark('approved_restore_containers_remain_network_isolated')
    check(sql('SELECT checkpoint FROM owr_queue_checkpoint WHERE id=1;').strip().decode()==checkpoint,'restored DB checkpoint mismatch')
    check(php("echo hash_file('sha256','/var/www/html/wp-content/uploads/external-recovery-unacked.txt');").decode()==pair.digest(b'job:recovery-unacked:write'),'restored effect file mismatch')
    run('docker','start',broker)
    wait_for(lambda:run('docker','exec',broker,'python3','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/control')",must=False).returncode==0,'restored broker')
    check(queue('/control')['checkpoint']==checkpoint and queue('/jobs')==[],'restore auto-resumed')
    ledger={row.split('\t')[0]:dict(zip(['kind','path','sha256'],row.split('\t')[1:])) for row in sql('SELECT job_id,kind,path,sha256 FROM owr_external_jobs;').decode().splitlines()}
    inventory=json.loads(php("$a=[];foreach(glob('/var/www/html/wp-content/uploads/external-*.txt') as $f)$a[basename($f)]=hash_file('sha256',$f);echo json_encode($a);"))
    pair.reconcile_done(queue('/status'),ledger,inventory)
    mark('lost_queue_database_and_file_restored_with_consumers_stopped')
    queue('/resume',{'checkpoint':checkpoint});run('docker','start',worker)
    wait_for(lambda:completed('recovery-pending') and queue('/jobs')==[],'restored redelivery',seconds=40)
    states={r['id']:r['state'] for r in queue('/status')}
    check(states['recovery-unacked']=='done' and states['recovery-pending']=='done' and states['recovery-conflict']=='quarantined','recovery states wrong')
    for ident in ['recovery-unacked','recovery-pending','recovery-conflict']:
        check(sql("SELECT COUNT(*) FROM wp_posts WHERE post_title='External "+ident+"';").strip()==b'1','duplicate effect')
    mark('ack_loss_redelivered_once_and_pending_job_recovered')
    mark('conflicting_effect_quarantined_without_blocking_safe_jobs')
    check(rejected('/enqueue',{'id':'recovery-unacked','kind':'deploy'}),'identity reused')
    mark('completed_job_identity_retained_and_conflicting_enqueue_rejected')
    if approved_restore is not None:
        signed_evidence['isolated_restore_verified']=True
    if s3_lab:protected.record_restore_success(signed_evidence)
    return {'format':pair.FORMAT,'tests':13 if approved_restore is not None else (14 if s3_lab else 22),'signed_set':signed_evidence,'manifest':manifest,'production_recovery_approved':False,'delivery':'at-least-once; fixed local idempotent effects only','rpo':'checkpoint; subsequent accepted jobs require separate reconciliation'}
