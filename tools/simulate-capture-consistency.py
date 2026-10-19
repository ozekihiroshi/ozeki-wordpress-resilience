"""Local synthetic SQLite/files race lab; no WordPress, AWS, Docker or credentials."""
import hashlib,importlib.util,json,sqlite3,tempfile,threading,uuid,argparse
from pathlib import Path
spec=importlib.util.spec_from_file_location('consistency',Path(__file__).with_name('capture-consistency.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
WRITERS=['web','cron','cli']
SCENARIOS={'quiescent':'consistent','concurrent_writer_blocked':'consistent',
           'unfenced_stable':'unverified','update_between_assets':'inconsistent',
           'aba_update':'inconsistent','unknown_writer':'unverified',
           'inflight_writer':'unverified','snapshot_failure':'capture_failed',
           'file_stream_failure':'capture_failed','lease_lost':'unverified',
           'release_failure':'capture_failed','schema_change':'unverified'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run_scenario(name):
    if name not in SCENARIOS:raise ValueError('Unknown scenario')
    with tempfile.TemporaryDirectory(prefix='owr-consistency-') as directory:
        root=Path(directory);media=root/'source';media.mkdir();file=media/'image.bin';file.write_bytes(b'old image')
        db=sqlite3.connect(root/'source.sqlite');db.execute('CREATE TABLE media(path TEXT, sha256 TEXT)')
        db.execute('INSERT INTO media VALUES (?,?)',('image.bin',sha(file)));db.commit()
        lock=threading.Lock();generation=0;blocked=[];attempt_id=uuid.uuid4().hex
        def inventory():return {p.name:sha(p) for p in media.iterdir() if p.is_file()}
        def update():
            nonlocal generation
            generation+=1;file.write_bytes(b'new image')
            db.execute('UPDATE media SET sha256=?',(sha(file),));db.commit();generation+=1
        before=inventory();initial_generation=generation
        fenced=name!='unfenced_stable';token=uuid.uuid4().hex
        if fenced:lock.acquire()
        try:
            # Backup API creates a real consistent synthetic database snapshot.
            snapshot=sqlite3.connect(root/'snapshot.sqlite');db.backup(snapshot);snapshot.close()
            if name=='concurrent_writer_blocked':
                def writer():
                    acquired=lock.acquire(blocking=False);blocked.append(not acquired)
                    if acquired:lock.release()
                thread=threading.Thread(target=writer);thread.start();thread.join()
            if name in ('update_between_assets','aba_update'):update() # simulated bypass writer
            if name=='aba_update':
                generation+=1;file.write_bytes(b'old image');db.execute('UPDATE media SET sha256=?',(sha(file),));db.commit();generation+=1
            copy=root/'copied';copy.mkdir()
            for f in media.iterdir():(copy/f.name).write_bytes(f.read_bytes())
            if name=='file_stream_failure':(copy/'image.bin').write_bytes(b'partial')
            with sqlite3.connect(root/'snapshot.sqlite') as captured:
                references=all((copy/path).is_file() and sha(copy/path)==digest for path,digest in captured.execute('SELECT path,sha256 FROM media'))
            def asset(path):return {'attempt_id':attempt_id,'site_id':'synthetic-consistency','completed':True,'exit_code':0,'bytes':path.stat().st_size,'sha256':sha(path)}
            record={'format':'owr-capture-consistency-v1','attempt_id':attempt_id,'site_id':'synthetic-consistency',
                    'assets':{'database':asset(root/'snapshot.sqlite'),'files':asset(copy/'image.bin')},
                    'file_inventory_before':before,'file_inventory_after':inventory(),
                    'captured_file_inventory':{p.name:sha(p) for p in copy.iterdir()},
                    'generation_before':initial_generation,'generation_after':generation,'references_match':references,
                    'barrier':{'scope_complete':name!='unknown_writer','writers':{w:{'fenced':fenced,'inflight':0} for w in WRITERS},
                               'token':token,'held_through_verification':name!='lease_lost'},
                    'end_token':token if name!='lease_lost' else 'different-token',
                    'phases':['fence','drain','snapshot','copy','verify','release'],
                    'db_snapshot_consistent':True,'schema_stable':name!='schema_change','release_confirmed':name!='release_failure'}
            if name=='inflight_writer':record['barrier']['writers']['cli']['inflight']=1
            if name=='snapshot_failure':record['assets']['database'].update(completed=False,exit_code=1)
            if name=='file_stream_failure':record['assets']['files'].update(completed=False,exit_code=1)
        finally:
            if lock.locked():lock.release()
            db.close()
        result=gate.assess(record,WRITERS)
        if result['state']!=SCENARIOS[name]:raise RuntimeError('Unexpected result for '+name)
        if name=='concurrent_writer_blocked' and blocked!=[True]:raise RuntimeError('Writer was not blocked')
        return {'scenario':name,'expected':SCENARIOS[name],'assessment':result,'observation':record,
                'writer_blocked':blocked==[True],'temporary_resources_released':True}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    # Reserve output before any work. Never overwrite previous observations.
    with a.output.open('x') as f:
        cases=[run_scenario(n) for n in SCENARIOS]
        json.dump({'kind':'capture_consistency_synthetic_lab','passed':True,'production_capture_integrated':False,
                   'database_backend':'SQLite synthetic fixture; not MariaDB validation','cases':cases},f,indent=2);f.write('\n')
    print(json.dumps({'passed':True,'scenarios':len(cases),'cloud_operations':False}))
if __name__=='__main__':main()
