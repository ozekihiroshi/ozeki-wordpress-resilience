"""Site-scoped settings inbox; atomic cutover preserving existing deliveries."""
import argparse,hashlib,importlib.util,json,os,re,secrets,sqlite3,sys,time
from pathlib import Path
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('notification-transfer');live=load('notification-live');bridge=load('notification-admin-bridge')
KINDS={'monitor_stopped','heartbeat_invalid','notification_delivery_failed'}
def request(v,site):
 if len(t.body(v))>4096:raise ValueError('request size')
 if isinstance(v,dict) and v.get('format')=='owr-observer-test-request-v1':
  if set(v)!={'format','site_id','request_id','expected_hash','created_at','revision','revision_token','channel_id'} or v['site_id']!=site:raise ValueError('test scope')
  for key in ('site_id','revision_token','channel_id'):t.ident(v[key])
  if not re.fullmatch(t.UUID,v['request_id']) or not re.fullmatch('[a-f0-9]{64}',v['expected_hash']):raise ValueError('test identity')
  if type(v['created_at']) is not int or v['created_at']>time.time()+5 or type(v['revision']) is not int or not 1<=v['revision']<=1000000000:raise ValueError('test metadata')
  return v
 if not isinstance(v,dict) or set(v)!={'format','request_id','expected_hash','created_at','settings'} or v['format']!='owr-observer-settings-request-v1':raise ValueError('request fields')
 if not re.fullmatch(t.UUID,v['request_id']) or not re.fullmatch('[a-f0-9]{64}',v['expected_hash']):raise ValueError('request identity')
 if type(v['created_at']) is not int or v['created_at']>time.time()+5:raise ValueError('request time')
 s=v['settings']
 if set(s)!={'format','site_id','revision','revision_token','channels'} or s['format']!='owr-notification-settings-v1' or s['site_id']!=site:raise ValueError('settings scope')
 t.ident(site);t.ident(s['revision_token'])
 if type(s['revision']) is not int or not 1<=s['revision']<=1000000000 or not isinstance(s['channels'],list) or not 1<=len(s['channels'])<=20:raise ValueError('settings bounds')
 ids=set()
 for c in s['channels']:
  if not isinstance(c,dict) or set(c)-{'id','label','provider','profile','recipient','enabled','kinds','retry','expire'}:raise ValueError('channel fields')
  t.ident(c['id']);t.ident(c['profile'])
  if c['id'] in ids:raise ValueError('duplicate channel')
  ids.add(c['id'])
  if type(c['enabled']) is not bool or c['provider'] not in ('pushover','smtp_tls','smtp_starttls'):raise ValueError('provider')
  for key,limit in [('recipient',254),('label',160)]:
   if not isinstance(c.get(key),str) or not 1<=len(c[key])<=limit or any(ord(ch)<32 or ch in '<>' for ch in c[key]):raise ValueError('text')
  if not isinstance(c['kinds'],list) or not c['kinds'] or any(not isinstance(k,str) or k not in KINDS for k in c['kinds']) or len(set(c['kinds']))!=len(c['kinds']):raise ValueError('alarm selection')
 return v
def receive(c,p):
 if set(p)!={'site_id','nonce','requests'} or p['site_id']!=c['site_id'] or not re.fullmatch('[a-f0-9]{32}',p['nonce']) or not isinstance(p['requests'],list) or len(p['requests'])>1:raise ValueError('envelope')
 values=[request(v,c['site_id']) for v in p['requests']]
 with sqlite3.connect(c['inbox_db'],timeout=2) as db:
  db.execute('PRAGMA synchronous=FULL');db.execute('CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');db.execute('BEGIN IMMEDIATE')
  count=db.execute('SELECT count(*) FROM inbox').fetchone()[0];acks=[]
  for v in values:
   raw=t.body(v).decode();old=db.execute('SELECT payload FROM inbox WHERE id=?',(v['request_id'],)).fetchone()
   if old and old[0]!=raw:raise ValueError('request conflict')
   if not old:
    if count>=1000:raise ValueError('inbox full')
    db.execute('INSERT INTO inbox VALUES(?,?)',(v['request_id'],raw));count+=1
   acks.append(dict(request_id=v['request_id'],sha256=t.digest(v)))
 return dict(nonce=p['nonce'],acknowledgements=acks)
original=t.command
def command(c):
 args=original(c);args[-1]='observer-settings';return args
t.command=command
def exchange(c,transport=None):
 import fcntl
 with Path(c['lock_file']).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  paths=sorted(Path(c['requests_dir']).glob('*.json'))
  if len(paths)>100:raise ValueError('spool full')
  values=[]
  for path in paths[:1]:
   v=request(t.read_file(path,16384),c['site_id'])
   if path.stem!=v['request_id']:raise ValueError('filename binding')
   values.append(v)
  packet=dict(site_id=c['site_id'],nonce=secrets.token_hex(16),requests=values)
  r=(transport or t.ssh)(c,packet)
  if set(r)!={'nonce','acknowledgements'} or r['nonce']!=packet['nonce'] or r['acknowledgements']!=[dict(request_id=v['request_id'],sha256=t.digest(v)) for v in values]:raise ValueError('acknowledgement')
  for path in paths[:1]:path.unlink()
  return dict(stored=len(values))
def status(c):
 active=live.current(c['delivery_state']);binding=active.get('admin_binding',{})
 result=dict(active_hash=bridge.digest(active),revision=binding.get('revision',0),revision_token=binding.get('revision_token',''),last_request=None)
 path=Path(c['state'])/'requests.sqlite'
 if path.exists():
  with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
   row=db.execute('SELECT result FROM results ORDER BY rowid DESC LIMIT 1').fetchone()
   if row:result['last_request']=json.loads(row[0])
 with sqlite3.connect((Path(c['delivery_state'])/'dispatch.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
  result['tests']=[]
  if db.execute("SELECT 1 FROM sqlite_master WHERE name='observer_tests'").fetchone():
   result['tests']=[dict(request_id=r[0],channel_id=r[1],revision=r[2],revision_token=r[3],status=r[4]) for r in db.execute("SELECT id,channel,revision,revision_token,CASE WHEN status='sending' THEN 'unknown' ELSE status END FROM observer_tests ORDER BY rowid DESC LIMIT 20")]
 return result
def apply_pending(c):
 import fcntl
 directory=Path(c['state']);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (directory/'apply.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with sqlite3.connect(directory/'requests.sqlite') as db:
   db.execute('PRAGMA synchronous=FULL');db.execute('CREATE TABLE IF NOT EXISTS results(id TEXT PRIMARY KEY,digest TEXT,result TEXT)')
   with sqlite3.connect(Path(c['inbox_db']).resolve().as_uri()+'?mode=ro',uri=True) as inbox:rows=inbox.execute('SELECT id,payload FROM inbox ORDER BY rowid LIMIT 1001').fetchall()
   if len(rows)>1000:raise ValueError('inbox limit')
   for rid,raw in rows:
    digest=hashlib.sha256(raw.encode()).hexdigest();old=db.execute('SELECT digest FROM results WHERE id=?',(rid,)).fetchone()
    if old:
     if old[0]!=digest:raise ValueError('stored request changed')
     continue
    v=request(t.decode(raw.encode(),16384),c['site_id'])
    if rid!=v['request_id']:raise ValueError('inbox identity')
    if v['format']=='owr-observer-test-request-v1':continue
    s=v['settings'];result=dict(request_id=rid,revision=s['revision'],revision_token=s['revision_token'],outcome='rejected',reason='policy')
    try:
     policy=t.read_file(c['policy_file'],65536);coverage=set()
     for channel in s['channels']:
      if channel['profile'] not in policy['profiles']:raise ValueError('unapproved profile')
      if channel['provider']!='pushover' and channel['recipient'] not in policy.get('allowed_recipients',{}).get(channel['profile'],[]):raise ValueError('unapproved recipient')
      if channel['enabled']:coverage.update(channel['kinds'])
     required=policy.get('required_kinds',sorted(KINDS))
     if not required or set(required)-KINDS or not set(required)<=coverage:raise ValueError('required alarms uncovered')
     active=live.current(c['delivery_state'])
     candidate,binding=bridge.compile_settings(s,policy['profiles'],active['source_outbox'],active['state'],include_existing=True,migration=True)
     prior=active.get('admin_binding')
     if prior==binding:
      result.update(outcome='applied',reason='applied') # Recover a crash after SQLite cutover, before this ledger commit.
     elif time.time()-v['created_at']>86400:result['reason']='expired'
     elif bridge.digest(active)!=v['expected_hash'] or (prior and s['revision']<=prior['revision']):result.update(outcome='conflict',reason='conflict')
     else:
      live.apply(candidate,binding,v['expected_hash']);result.update(outcome='applied',reason='applied')
    except BlockingIOError:break # Retain request for retry; do not suppress normal delivery.
    except (ValueError,KeyError,TypeError,OSError):pass
    db.execute('INSERT INTO results VALUES(?,?,?)',(rid,digest,json.dumps(result)));db.commit()
 return status(c)
def tests(c,factory=None,now=None):
 """Fixed-body normal-priority tests; at most one send per monitoring cycle."""
 import fcntl
 from datetime import datetime,timezone
 dispatch=bridge.dispatch;now=time.time() if now is None else now
 directory=Path(c['delivery_state'])
 with (directory/'dispatch.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with sqlite3.connect(directory/'dispatch.sqlite') as db:
   db.execute('PRAGMA synchronous=FULL')
   db.execute('CREATE TABLE IF NOT EXISTS observer_tests(id TEXT PRIMARY KEY,digest TEXT,channel TEXT,revision INTEGER,revision_token TEXT,status TEXT,created REAL)')
   db.execute("UPDATE observer_tests SET status='unknown' WHERE status='sending'");db.commit()
   active=json.loads(db.execute('SELECT binding FROM settings').fetchone()[0]);binding=active.get('admin_binding',{})
   with sqlite3.connect(Path(c['inbox_db']).resolve().as_uri()+'?mode=ro',uri=True) as inbox:rows=inbox.execute('SELECT id,payload FROM inbox ORDER BY rowid LIMIT 1001').fetchall()
   if len(rows)>1000:raise ValueError('inbox limit')
   processed=0
   for rid,raw in rows:
    v=request(t.decode(raw.encode(),16384),c['site_id'])
    if rid!=v['request_id']:raise ValueError('inbox identity')
    if v['format']!='owr-observer-test-request-v1':continue
    digest=hashlib.sha256(raw.encode()).hexdigest();prior=db.execute('SELECT digest FROM observer_tests WHERE id=?',(rid,)).fetchone()
    if prior:
     if prior[0]!=digest:raise ValueError('test identity conflict')
     continue
    route=next((r for r in active['channels'] if r.get('active') and r.get('logical_id')==v['channel_id']),None)
    valid=route is not None and v['expected_hash']==bridge.digest(active) and all(v[k]==binding.get(k) for k in ('site_id','revision','revision_token')) and 0<=now-v['created_at']<=300
    recent=db.execute("SELECT 1 FROM observer_tests WHERE channel=? AND created>? AND status IN ('sending','accepted','unknown','retry','rejected')",(v['channel_id'],now-60)).fetchone()
    state='sending' if valid and not recent else 'blocked'
    db.execute('INSERT INTO observer_tests VALUES(?,?,?,?,?,?,?)',(rid,digest,v['channel_id'],v['revision'],v['revision_token'],state,now));db.commit();processed+=1
    if state=='sending':
     event=dict(event_id=rid.replace('-',''),site=c['site_id'],domain='observer-test',subject=v['channel_id'],kind='notification_test',transition='resolved',observed_at=datetime.fromtimestamp(now,timezone.utc).isoformat())
     try:(factory or dispatch.adapter)(route['provider']).send(event);state='accepted'
     except Exception as exc:state=exc.outcome if isinstance(exc,dispatch.push.DeliveryError) and exc.outcome in ('retry','rejected','unknown') else 'unknown'
     db.execute('UPDATE observer_tests SET status=? WHERE id=?',(state,rid));db.commit();break
    if processed>=20:break
 return status(c)['tests']
def enable(c):
 # Explicit one-time adoption changes only the observer's configuration binding.
 # Existing heartbeat, incidents, outboxes, receipts and delivery DB are untouched.
 watch=load('monitor-runtime-lab');root=Path(c['state']);cc=c['configuration']
 if cc['site_id']!=c['admin_site_id'] or cc['delivery_state']!=c['alerts']['state']:raise ValueError('binding')
 with watch.locked(root):
  path=root/'binding.json';old=t.read_file(path,32768)
  if old==c:return dict(enabled=True)
  if 'configuration' in old or old!={k:v for k,v in c.items() if k!='configuration'}:raise ValueError('only configuration adoption allowed')
  active=live.current(cc['delivery_state'])
  if active['source_outbox']!=c['alerts']['source_outbox']:raise ValueError('source changed')
  t.read_file(cc['policy_file'],65536)
  t.atomic(path,c,0o600)
 return dict(enabled=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['receive','exchange','apply','enable']);p.add_argument('--config',required=True);a=p.parse_args();os.umask(0o027)
 try:
  c=t.read_file(a.config,16384)
  if a.action=='receive':
   import resource,signal
   resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024));signal.alarm(10)
   if os.environ.get('SSH_ORIGINAL_COMMAND')!='observer-settings':raise ValueError('forced command only')
   result=receive(c,t.decode(sys.stdin.buffer.read(98305),98304))
  elif a.action=='exchange':result=exchange(c)
  elif a.action=='enable':result=enable(c)
  else:result=apply_pending(c)
  print(json.dumps(result));return 0
 except Exception as e:print(json.dumps(dict(error_type=type(e).__name__)));return 1
if __name__=='__main__':raise SystemExit(main())
