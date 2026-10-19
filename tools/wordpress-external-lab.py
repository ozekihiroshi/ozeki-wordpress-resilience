"""Restricted SSH and independent durable-queue lab; administrative bypass remains excluded."""
import copy,hashlib,importlib.util,io,json,secrets,subprocess as sp,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WRITERS=['php-http','php-cli-file','database-direct','ssh-forced-command','external-queue','managed-child']

def run_external(db,web,php,sql,hold,ready,release,results,run,check,image,prior,s3_lab=False,s3_resume_set=None,daily_s3_stage=None,approved_restore=None):
    extra=[]
    def mark(name,**data):
        results.append({'case':name,'passed':True,**data});print('PASS '+name,flush=True)
    def wait_for(fn,label,seconds=20):
        deadline=time.monotonic()+seconds
        while not fn():
            check(time.monotonic()<deadline,label+' timed out');time.sleep(.1)
    def inventory():
        return json.loads(php("$a=[];$base='/var/www/html/';foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base,FilesystemIterator::SKIP_DOTS)) as $f){if($f->isLink())throw new Exception('link');if($f->isFile()){$h=hash_file('sha256',$f->getPathname());if($h===false)throw new Exception('unreadable');$a[substr($f->getPathname(),strlen($base))]=$h;}}ksort($a);echo json_encode($a);"))
    def active(job):return php(f"echo file_exists('/tmp/owr-external-active-{job}')?'yes':'no';")==b'yes'
    def generation():return int(php("echo file_get_contents('/tmp/owr-route-generation');"))
    def completed(job):return sql("SELECT COUNT(*) FROM owr_external_jobs WHERE job_id='"+job+"' AND sha256<>'';").strip()==b'1'
    def queue(path,data=None):
        # The test driver talks to the broker's real HTTP endpoint inside the isolated namespace.
        code="import sys,json;sys.path.insert(0,'/lab');from importlib.machinery import SourceFileLoader;m=SourceFileLoader('queue_api','/lab/external-queue.py').load_module();print(json.dumps(m.api(sys.argv[1],None if sys.argv[2]=='null' else json.loads(sys.argv[2]))))"
        return json.loads(run('docker','exec',broker,'python3','-c',code,path,json.dumps(data)).stdout)
    def enqueue(id,kind='write'):return queue('/enqueue',{'id':id,'kind':kind})
    def drained_queue():return queue('/jobs')==[]

    try:
        sql('CREATE TABLE owr_external_jobs(job_id VARCHAR(48) PRIMARY KEY,kind VARCHAR(16) NOT NULL,path TEXT NOT NULL,sha256 CHAR(64) NOT NULL) ENGINE=InnoDB;')
        run('docker','exec',web,'chmod','750','/var/www/html')
        run('docker','exec',web,'mkdir','-p','/run/owr-ssh','/run/sshd')
        run('docker','exec',web,'chmod','700','/run/owr-ssh')
        for key in ['host','client']:
            run('docker','exec',web,'ssh-keygen','-q','-t','ed25519','-N','','-f','/run/owr-ssh/'+key)
        # Authorized public key must be readable by the restricted account, private keys stay root-only.
        run('docker','exec',web,'cp','/run/owr-ssh/client.pub','/etc/ssh/owr-authorized-keys')
        run('docker','exec',web,'chmod','644','/etc/ssh/owr-authorized-keys')
        hostpub=run('docker','exec',web,'cat','/run/owr-ssh/host.pub').stdout.split()
        known=b'[127.0.0.1]:2222 '+b' '.join(hostpub[:2])+b'\n'
        run('docker','exec','-i',web,'sh','-c','cat > /run/owr-ssh/known_hosts',input=known)
        config='''Port 2222
ListenAddress 127.0.0.1
HostKey /run/owr-ssh/host
PidFile /run/owr-ssh/pid
AuthorizedKeysFile /etc/ssh/owr-authorized-keys
AllowUsers owr-operator
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
UsePAM no
DisableForwarding yes
PermitTTY no
PermitUserEnvironment no
ForceCommand /usr/bin/python3 /lab/external-client.py
Subsystem sftp internal-sftp
'''
        run('docker','exec','-i',web,'sh','-c','cat > /run/owr-ssh/config',input=config.encode())
        run('docker','exec',web,'/usr/sbin/sshd','-t','-f','/run/owr-ssh/config')
        effective=run('docker','exec',web,'/usr/sbin/sshd','-T','-f','/run/owr-ssh/config').stdout
        restricted=b'disableforwarding yes' in effective and b'forcecommand /usr/bin/python3 /lab/external-client.py' in effective
        check(restricted,'SSH policy missing')
        run('docker','exec','-d','-u','www-data',web,'python3','/lab/external-dispatch.py')
        wait_for(lambda:run('docker','exec',web,'test','-S','/run/owr-dispatch/service.sock',must=False).returncode==0,'dispatch socket')
        run('docker','exec',web,'/usr/sbin/sshd','-f','/run/owr-ssh/config')
        ssh=['docker','exec',web,'ssh','-T','-p','2222','-i','/run/owr-ssh/client','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/run/owr-ssh/known_hosts','owr-operator@127.0.0.1']
        def ssh_call(command,async_=False):
            if async_:return sp.Popen(ssh+[command],stdout=sp.PIPE,stderr=sp.PIPE)
            return run(*(ssh+[command]),must=False)
        for kind in ['write','deploy']:
            result=ssh_call(kind+' ssh-'+kind)
            check(result.returncode==0 and completed('ssh-'+kind),'SSH job failed: '+result.stderr.decode()[-300:])
        check(ssh_call('deploy ssh-write').returncode!=0,'conflicting job identity accepted')
        mark('restricted_real_ssh_jobs_write_database_and_files')
        for command in ['','sh','php -r "echo 1;"','scp -t /var/www/html','write ../../escape','write ok; touch /tmp/escape']:
            result=ssh_call(command)
            check(result.returncode!=0 and b'command_denied' in result.stdout,'SSH shell escape accepted')
        subsystem=run(*(ssh[:-1]+['-s',ssh[-1],'sftp']),must=False)
        check(subsystem.returncode!=0 and b'command_denied' in subsystem.stdout,'SFTP accepted')
        forwarding=run(*(ssh[:-1]+['-W','127.0.0.1:3306',ssh[-1]]),must=False)
        check(forwarding.returncode!=0 and b'administratively prohibited' in forwarding.stderr,'forwarding accepted')
        read=run('docker','exec','-u','owr-operator',web,'test','-r','/var/www/html/wp-config.php',must=False)
        write=run('docker','exec','-u','owr-operator',web,'touch','/var/www/html/wp-content/uploads/bypass.txt',must=False)
        check(read.returncode!=0 and write.returncode!=0,'operator has direct site access')
        mark('ssh_shell_sftp_forwarding_and_direct_site_access_denied')

        mounts=json.loads(run('docker','inspect',web).stdout)[0]['Mounts']
        volume=next(m['Name'] for m in mounts if m['Destination']=='/run/owr-dispatch')
        broker=web+'-queue';worker=web+'-consumer'
        run('docker','run','-d','--name',broker,'--network','container:'+db,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000','--tmpfs','/tmp','-v','/queue','-v',str(ROOT/'lab/consistency')+':/lab:ro','--entrypoint','python3',image,'/lab/external-queue.py','broker');extra.append(broker)
        wait_for(lambda:run('docker','exec',broker,'python3','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/jobs')",must=False).returncode==0,'broker')
        run('docker','run','-d','--name',worker,'--network','container:'+db,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000','--tmpfs','/tmp','-v',volume+':/run/owr-dispatch:ro','-v',str(ROOT/'lab/consistency')+':/lab:ro','--entrypoint','python3',image,'/lab/external-queue.py','worker');extra.append(worker)
        inspected=json.loads(run('docker','inspect',worker,broker).stdout)
        check(all(x['HostConfig']['ReadonlyRootfs'] and not x['HostConfig']['PortBindings'] and x['HostConfig']['NetworkMode'].startswith('container:') for x in inspected),'queue isolation missing')
        check(not any(m['Destination']=='/var/www/html' and m.get('Type')=='bind' for m in inspected[0]['Mounts']),'site bind exposed to worker')
        enqueue('queue-first');wait_for(lambda:completed('queue-first') and drained_queue(),'first queue job')
        enqueue('queue-first');wait_for(drained_queue,'duplicate acknowledgment')
        check(sql("SELECT COUNT(*) FROM wp_posts WHERE post_title='External queue-first';").strip()==b'1','duplicate delivery created second post')
        mark('independent_durable_queue_acknowledges_only_completed_idempotent_job')

        enqueue('queue-active','slow');wait_for(lambda:active('queue-active'),'queue child active')
        start=time.monotonic();p,token=hold(wait=10,lease=180);ready(p)
        elapsed=time.monotonic()-start
        check(elapsed>1 and completed('queue-active'),'queue/child not drained')
        wait_for(drained_queue,'active job acknowledgment')
        mark('queue_worker_and_real_child_process_drained',wait_seconds=round(elapsed,3))
        blocked=ssh_call('write ssh-blocked');check(blocked.returncode==3 and b'fenced' in blocked.stdout,'SSH write admitted')
        gen_before=generation();before=inventory()
        schema_before=sql("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='lab' ORDER BY TABLE_NAME;")
        transactional=all(row.endswith(b'\tInnoDB') for row in schema_before.splitlines())
        check(transactional,'unsupported table engine')
        enqueue('queue-pending');time.sleep(.5)
        pending=queue('/jobs');check(pending==[{'id':'queue-pending','kind':'write'}] and not completed('queue-pending'),'queued job lost or applied while fenced')
        mark('ssh_rejected_and_queue_retained_while_fenced')
        run('docker','restart',broker)
        wait_for(lambda:run('docker','exec',broker,'python3','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/jobs')",must=False).returncode==0,'broker restart')
        check(queue('/jobs')==pending and not completed('queue-pending'),'broker restart lost or applied pending job')
        mark('broker_restart_preserves_fenced_pending_job')

        dump=run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --skip-lock-tables lab').stdout
        archive=run('docker','exec',web,'tar','-czf','-','-C','/var/www/html','.').stdout
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
            captured={m.name.removeprefix('./'):hashlib.sha256(tar.extractfile(m).read()).hexdigest() for m in tar.getmembers() if m.isfile()}
        rows=sql('SELECT path,sha256 FROM owr_external_jobs ORDER BY job_id;').decode().splitlines()
        references=all(captured.get('wp-content/uploads/'+r.split('\t')[0])==r.split('\t')[1] for r in rows) and bool(rows)
        media=sql("SELECT meta_value FROM wp_postmeta WHERE meta_key='_wp_attached_file' ORDER BY meta_value;").decode().splitlines()
        references=references and all('wp-content/uploads/'+path in captured for path in media)
        after=inventory();gen_after=generation();end_token=php("echo file_get_contents('/tmp/owr-gate.fence');").decode();held=p.poll() is None and end_token==token
        schema_after=sql("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='lab' ORDER BY TABLE_NAME;")
        actors_alive=all(x['State']['Running'] for x in json.loads(run('docker','inspect',worker,broker).stdout))
        check(queue('/jobs')==pending,'queue mutated during capture')
        release(p,token)
        record=copy.deepcopy(prior['observation']);attempt='lab-external-'+secrets.token_hex(8)
        record.update(attempt_id=attempt,site_id='isolated-external-writer-lab',generation_before=gen_before,generation_after=gen_after,
                      file_inventory_before=before,file_inventory_after=after,captured_file_inventory=captured,end_token=end_token,
                      references_match=references,release_confirmed=not php("echo file_exists('/tmp/owr-gate.fence')?'yes':'';"),scope_profile='isolated-mediated-writers-v1',schema_stable=schema_before==schema_after,db_snapshot_consistent=transactional)
        record['assets']={key:{'site_id':record['site_id'],'attempt_id':attempt,'completed':True,'exit_code':0,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for key,data in [('database',dump),('files',archive)]}
        record['barrier']={'scope_complete':restricted and actors_alive,'writers':{name:{'fenced':True,'inflight':0} for name in WRITERS},'token':token,'held_through_verification':held}
        sql('CREATE DATABASE external_restored;')
        run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot external_restored',input=dump)
        restored=sql('SELECT path,sha256 FROM external_restored.owr_external_jobs ORDER BY job_id;').decode().splitlines()
        restored_media=sql("SELECT meta_value FROM external_restored.wp_postmeta WHERE meta_key='_wp_attached_file' ORDER BY meta_value;").decode().splitlines()
        record['references_match']=references and rows==restored and media==restored_media
        spec=importlib.util.spec_from_file_location('assessor',ROOT/'tools/capture-consistency.py');assessor=importlib.util.module_from_spec(spec);spec.loader.exec_module(assessor)
        assessment=assessor.assess(record,WRITERS);check(assessment['state']=='consistent','external capture failed: '+str(assessment))
        mark('external_writer_capture_and_restore_assessed_consistent',assessment=assessment,files=len(captured),job_references=len(rows))
        wait_for(lambda:completed('queue-pending') and drained_queue(),'queue resume')
        check(ssh_call('write ssh-resumed').returncode==0 and completed('ssh-resumed'),'SSH did not resume')
        mark('ssh_and_pending_queue_job_resume_after_release')

        p,token=hold(lease=2);ready(p);enqueue('queue-after-expiry')
        p.wait(timeout=8);events=[json.loads(line)['state'] for line in p.stdout.read().splitlines()]
        check(events==['lease_expired','released'],'expiry not observed')
        wait_for(lambda:completed('queue-after-expiry') and drained_queue(),'queue expiry recovery')
        expired=copy.deepcopy(record);expired['barrier']['held_through_verification']=False
        check(assessor.assess(expired,WRITERS)['state']=='unverified','expired external capture accepted')
        mark('queue_resumes_after_expiry_without_accepting_expired_capture')

        run('docker','stop',worker);enqueue('offline-pending')
        running=json.loads(run('docker','inspect',worker).stdout)[0]['State']['Running']
        missing=copy.deepcopy(record);missing['barrier']['scope_complete']=running
        check(assessor.assess(missing,WRITERS)['state']=='unverified','missing worker confirmation accepted')
        unknown=assessor.assess(record,WRITERS+['unmanaged-root-shell']);check(unknown['state']=='unverified','root bypass accepted')
        check(queue('/jobs')==[{'id':'offline-pending','kind':'write'}],'offline queue not durable')
        run('docker','start',worker);wait_for(lambda:completed('offline-pending') and drained_queue(),'worker restart')
        mark('worker_unavailable_and_unknown_privileged_writer_not_accepted')
        spec=importlib.util.spec_from_file_location('queue_recovery_lab',ROOT/'tools/wordpress-queue-recovery-lab.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        queue_recovery=module.exercise(db,web,broker,worker,php,sql,hold,ready,release,run,check,queue,enqueue,completed,wait_for,mark,ssh_call,s3_lab=s3_lab,s3_resume_set=s3_resume_set,daily_s3_stage=daily_s3_stage,approved_restore=approved_restore)
        return {'expected_writers':WRITERS,'observation':record,'assessment':assessment,'production_scope_complete':False,
                'scope_profile':'isolated-mediated-writers-v1','excluded':['root/Docker administrator','arbitrary SSH shell/SFTP/deploy commands','unregistered workers','detached or escaping child processes','external storage'],
                'queue_contract':'single consumer; paired checkpoint; retained ACK ledger; fixed jobs idempotent', 'queue_recovery':queue_recovery}
    finally:
        for name in reversed(extra):run('docker','rm','-f','-v',name)
