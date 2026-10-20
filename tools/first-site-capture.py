"""First-site capture contract. No S3, signing, or production deployment entry."""
import argparse, copy, fcntl, hashlib, json, os, re, shutil, subprocess, tarfile, time, uuid
from pathlib import Path, PurePosixPath

WRITERS = {'http','wp_cron','system_cron','cli','deploy','direct_db','direct_files'}
class Rejected(ValueError): pass

def require(condition, reason):
    if not condition: raise Rejected(reason)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def keys(value, expected):
    require(isinstance(value,dict) and set(value)==set(expected),'invalid_fields')

def text(value):
    return isinstance(value,str) and bool(value.strip()) and len(value)<=256 and not any(ord(c)<32 for c in value)

def validate(c):
    keys(c,['format','site_id','revision','wordpress','database','files','writers','queue','dependencies','operations','storage','trust','runtime'])
    require(c['format']=='owr-first-site-profile-v1','invalid_format')
    require(isinstance(c['site_id'],str) and re.fullmatch('[a-z][a-z0-9-]{0,47}',c['site_id']),'invalid_site')
    require(type(c['revision']) is int and c['revision']>0,'invalid_revision')
    keys(c['wordpress'],['multisite','uploads']);require(c['wordpress']['multisite'] is False and c['wordpress']['uploads']=='wp-content/uploads','unsupported_wordpress')
    keys(c['database'],['name','prefix','engines']);require(c['database']['engines']==['InnoDB'],'unsupported_engine')
    require(all(isinstance(c['database'][x],str) and re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}',c['database'][x]) for x in ['name','prefix']),'invalid_database')
    keys(c['files'],['root','exclusions']);require(c['files']['root']=='/var/www/html' and c['files']['exclusions']==[],'unsupported_file_scope')
    require(isinstance(c['writers'],dict) and set(c['writers'])==WRITERS,'writer_scope_incomplete')
    for w in c['writers'].values():
        keys(w,['mode','owner','evidence']);require(w['mode'] in ['fenced','disabled'] and text(w['owner']) and text(w['evidence']),'invalid_writer')
    keys(c['queue'],['state','evidence']);require(c['queue']['state']=='absent' and text(c['queue']['evidence']),'unsupported_queue')
    require(c['dependencies']==[],'unsupported_dependencies')
    keys(c['operations'],['owner','alternate','window','schedule','max_stop_seconds','drain_seconds','rpo_seconds','rto_seconds','max_bytes','reserve_bytes'])
    o=c['operations'];require(all(text(o[x]) for x in ['owner','alternate','window','schedule']),'missing_operator_input')
    for k in ['max_stop_seconds','drain_seconds','rpo_seconds','rto_seconds','max_bytes','reserve_bytes']:
        require(type(o[k]) is int and o[k]>0,'invalid_limit')
    require(o['drain_seconds']+4<o['max_stop_seconds']<=600 and o['max_bytes']<=512*1024**2,'unsupported_limits')
    keys(c['storage'],['destination_ref','writer_ref','reader_ref','retention_days']);require(c['storage']['retention_days']==35 and all(text(c['storage'][x]) for x in ['destination_ref','writer_ref','reader_ref']),'invalid_storage_ref')
    require(c['storage']['writer_ref']!=c['storage']['reader_ref'],'roles_not_separated')
    keys(c['trust'],['operator','public_pin_ref']);require(all(text(x) for x in c['trust'].values()),'invalid_trust_ref')
    keys(c['runtime'],['wordpress_ref','database_ref']);require(all(text(x) for x in c['runtime'].values()),'missing_runtime')
    return {'valid':True,'config_sha256':digest(c),'scope':'dedicated first-site capture; production deployment unsupported'}

def safe_name(name):
    p=PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and '\\' not in name and '\x00' not in name

def archive_inventory(path,limit):
    values={}; seen=set(); total=0
    with tarfile.open(path,'r:gz') as t:
        for m in t:
            name=m.name.removeprefix('./').rstrip('/')
            if not name or name=='.':continue
            require(safe_name(name) and name not in seen,'unsafe_archive')
            seen.add(name);require(len(seen)<=20000,'archive_entry_limit')
            require(m.isdir() or m.isfile(),'unsupported_archive_member')
            if m.isdir():continue
            total+=m.size; require(0<=m.size<=limit and total<=limit,'archive_expansion_limit')
            h=hashlib.sha256()
            with t.extractfile(m) as f:
                while b:=f.read(65536):h.update(b)
            values[name]=h.hexdigest()
    require(bool(values),'empty_archive');return values

def write_json(path,value):
    tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    tmp.replace(path)

def capture(config, expected_config_hash, backend, state_root):
    c=copy.deepcopy(config);validate(c)
    require(digest(c)==expected_config_hash,'configuration_pin_mismatch')
    root=Path(state_root);require(root.is_dir() and not root.is_symlink(),'invalid_state_root')
    require(root.stat().st_uid==os.getuid() and root.stat().st_mode & 0o077==0,'state_root_not_private')
    lock=root/(c['site_id']+'.lock')
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'a') as owner:
        try:fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Rejected('site_busy')
        active=root/(c['site_id']+'.active.json')
        require(not active.exists(),'prior_attempt_requires_reconciliation')
        attempt=uuid.uuid4().hex;work=root/attempt;work.mkdir(mode=0o700)
        result={'format':'owr-first-site-capture-v1','attempt_id':attempt,'site_id':c['site_id'],'config_sha256':digest(c),'state':'capture_failed','eligible_for_consistency_acceptance':False,'storage_complete':False,'signed':False,'restore_verified':False,'production_recovery_approved':False,'queue':c['queue'],'assets':{},'release_confirmed':False,'phases':[]}
        write_json(active,{'attempt_id':attempt,'config_sha256':digest(c),'state':'in_progress'})
        token=uuid.uuid4().hex;attempted_fence=False
        def measured(operation, fn, *args):
            started=time.monotonic()
            try:return fn(*args)
            except subprocess.TimeoutExpired as exc:
                # Never persist command text, stdout or stderr (may contain secrets).
                result['timeout']={'operation':operation,'limit_seconds':exc.timeout,'elapsed_seconds':time.monotonic()-started}
                raise
            finally:
                elapsed=time.monotonic()-started
                item=result.setdefault('timings',{}).setdefault(operation,{'calls':0,'seconds':0.0,'max_seconds':0.0})
                item['calls']+=1;item['seconds']+=elapsed;item['max_seconds']=max(item['max_seconds'],elapsed)
        def observed_stream(stream,asset):
            while True:
                try:chunk=measured('stream.'+asset+'.read',next,stream)
                except StopIteration:return
                yield chunk
        try:
            measured('preflight',backend.preflight,c)
            o=c['operations'];require(shutil.disk_usage(root).free>=o['max_bytes']*getattr(backend,'staging_copies',1)+o['reserve_bytes'],'insufficient_space')
            if hasattr(backend,'set_staging'):backend.set_staging(work)
            attempted_fence=True;wall_start=time.time();wall_deadline=wall_start+o['max_stop_seconds'];deadline=time.monotonic()+o['max_stop_seconds']
            measured('fence',backend.fence,token,o['drain_seconds'],o['max_stop_seconds']);result['phases']+=['fence','drain']
            require(measured('held',backend.held,token),'fence_not_held')
            before=measured('inventory',backend.inventory,o['max_bytes']);schema=measured('schema',backend.schema)
            require(bool(schema) and all(x[1]=='InnoDB' for x in schema),'unsupported_live_schema')
            refs=measured('references',backend.references);used=0
            for asset,filename,phase in [('database','database.sql','snapshot'),('files','files.tar.gz','copy')]:
                h=hashlib.sha256();size=0
                stream=backend.stream(asset,deadline)
                next_fence_check=0.0
                try:
                    with (work/filename).open('xb') as f:
                        os.chmod(work/filename,0o600)
                        for chunk in observed_stream(stream,asset):
                            now=time.monotonic()
                            require(now<deadline and wall_start<=time.time()<wall_deadline,'capture_window_lost')
                            if now>=next_fence_check:
                                require(measured('held',backend.held,token),'capture_window_lost')
                                # Schedule from completion, not from before a potentially slow probe.
                                next_fence_check=time.monotonic()+0.5
                                require(next_fence_check-0.5<deadline and wall_start<=time.time()<wall_deadline,'capture_window_lost')
                            size+=len(chunk);used+=len(chunk);require(used<=o['max_bytes'],'capture_size_limit')
                            f.write(chunk);h.update(chunk)
                        f.flush();os.fsync(f.fileno())
                finally:stream.close()
                require(size>0,'empty_stream')
                result['assets'][asset]={'path':filename,'bytes':size,'sha256':h.hexdigest(),'attempt_id':attempt}
                result['phases'].append(phase)
            captured=archive_inventory(work/'files.tar.gz',o['max_bytes'])
            require(before==measured('inventory',backend.inventory,o['max_bytes'])==captured,'source_or_archive_changed')
            require(schema==measured('schema',backend.schema),'schema_changed')
            require(refs==measured('references',backend.references),'references_changed')
            require(all(safe_name(n) and 'wp-content/uploads/'+n in captured for n in refs),'attachment_reference_missing')
            require(time.monotonic()<deadline and wall_start<=time.time()<wall_deadline and measured('held',backend.held,token),'capture_window_lost')
            result.update(state='consistent',references_checked=len(refs),inventory_sha256=digest(captured),tables=len(schema))
            result['phases'].append('verify')
        except Exception as e:
            reason=str(e) if isinstance(e,Rejected) else type(e).__name__
            result['reason']=reason
            result['state']='inconsistent' if reason in ['source_or_archive_changed','schema_changed','references_changed','attachment_reference_missing'] else 'unverified' if reason in ['capture_window_lost','unsupported_live_schema','fence_not_held','runtime_scope_mismatch'] else 'capture_failed'
        finally:
            if attempted_fence:
                try:result['release_confirmed']=measured('release',backend.release,token) is True
                except Exception:result['release_confirmed']=False
            else:result['release_confirmed']=True
            if not result['release_confirmed']:
                result['capture_state_before_release']=result['state'];result['state']='capture_failed';result['release_error']='source_release_unconfirmed'
            result['phases'].append('release')
            result['eligible_for_consistency_acceptance']=result['state']=='consistent' and result['release_confirmed']
            write_json(work/'result.json',result)
            if result['release_confirmed']:active.unlink()
            else:write_json(active,{'attempt_id':attempt,'state':'release_unconfirmed'})
        return work,result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['validate']);p.add_argument('--config',type=Path,required=True)
    a=p.parse_args()
    try:result=validate(json.loads(a.config.read_text()));code=0
    except (ValueError,OSError,TypeError) as e:result={'valid':False,'reason':str(e) if isinstance(e,Rejected) else type(e).__name__};code=1
    print(json.dumps(result));return code
if __name__=='__main__':raise SystemExit(main())
