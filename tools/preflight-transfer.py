"""Pinned SSH transfer of preflight reports, preserving source observation time."""
import argparse,fcntl,importlib.util,json,os,re,secrets,signal,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
s=importlib.util.spec_from_file_location('wire',Path(__file__).with_name('notification-transfer.py'));t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
base=t.command
def command(c):
 a=base(c);a[a.index('HostKeyAlias=owr-notification-'+c['site_id'])]='HostKeyAlias=owr-preflight-'+c['site_id'];a[-1]='preflight-status';return a
t.command=command

def stamp(v):
 if not isinstance(v,str) or len(v)>64:raise ValueError('time')
 d=datetime.fromisoformat(v)
 if not d.tzinfo or d.timestamp()>time.time()+5:raise ValueError('time')
 return d.timestamp()

def clean_review(v):
 try:
  if v['format']!='owr-operator-review-status-v1' or v['state'] not in ('valid','expired','revoked','reconfirmation_required','missing','invalid') or type(v['automatic_checks_passed']) is not bool:raise ValueError()
  reasons=v['reasons']
  if not isinstance(reasons,list) or len(reasons)>8 or any(x not in ('review_missing','review_invalid','review_revoked','review_expired','scope_changed','confirmation_incomplete','automatic_checks_failed') for x in reasons):raise ValueError()
  if v['state'] not in ('missing','invalid'):
   start=stamp(v['reviewed_at']);end=datetime.fromisoformat(v['expires_at'])
   if not end.tzinfo or not 0<end.timestamp()-start<=604800:raise ValueError()
  return {k:v[k] for k in ('format','state','reviewed_at','expires_at','reasons','automatic_checks_passed')}
 except (ValueError,TypeError,KeyError,OverflowError):
  return dict(format='owr-operator-review-status-v1',state='invalid',reviewed_at=None,expires_at=None,reasons=['review_invalid'],automatic_checks_passed=False)

def clean(v,c):
 if v.get('format')!='owr-preflight-admin-v1' or v.get('site_id')!=c['site_id'] or v.get('config_sha256')!=c['config_sha256']:raise ValueError('binding')
 stamp(v['attempted_at']);r=v['result'];h=r.get('host_observation',{})
 if r.get('production_ready') is not False or r.get('state') not in ('needs_configuration','unsupported','eligible_for_dedicated_trial') or h.get('state') not in ('validated_report','unavailable','invalid','probe_failed'):raise ValueError('state')
 issues=r['issues'];unknown=h.get('unverified',[])
 if not isinstance(issues,list) or len(issues)>100 or not isinstance(unknown,list) or len(unknown)>20:raise ValueError('count')
 for i in issues:
  if not re.fullmatch('[a-z0-9_]{1,100}',i['code']) or i['category'] not in ('configuration','environment','operational','unsupported','unclassified'):raise ValueError('issue')
 for x in unknown:
  if not re.fullmatch('[a-z_]{1,80}',x):raise ValueError('scope')
 out=dict(format=v['format'],site_id=v['site_id'],config_sha256=v['config_sha256'],attempted_at=v['attempted_at'],result=dict(production_ready=False,state=r['state'],host_observation=dict(state=h['state'],unverified=unknown),issues=[{k:i[k] for k in ('code','category')} for i in issues]))
 if 'operator_review' in r:out['result']['operator_review']=clean_review(r['operator_review'])
 return out

def serve(c,q):
 if set(q)!={'site_id','config_sha256','nonce'} or q['site_id']!=c['site_id'] or q['config_sha256']!=c['config_sha256'] or not re.fullmatch('[a-f0-9]{32}',q['nonce']):raise ValueError('request')
 r=clean(t.read_file(c['report_file'],65536),c);h=t.read_file(c['health_file'],8192)
 if h.get('site_id')!=c['site_id'] or h.get('config_sha256')!=c['config_sha256'] or h.get('state') not in ('ok','acquisition_failed') or h.get('report_at')!=r['attempted_at'] or h.get('attempted_at')!=r['attempted_at']:raise ValueError('source pair not consistent')
 return dict(nonce=q['nonce'],report=r,source_state=h['state'])

def pull(c,transport=None):
 at=datetime.now(timezone.utc).isoformat();h=dict(format='owr-preflight-transfer-v1',site_id=c['site_id'],config_sha256=c['config_sha256'],attempted_at=at,report_at=None,state='transfer_failed')
 try:
  old=clean(t.read_file(c['report_file'],65536),c) if Path(c['report_file']).exists() else None
  nonce=secrets.token_hex(16);q=dict(site_id=c['site_id'],config_sha256=c['config_sha256'],nonce=nonce)
  v=(transport or t.ssh)(c,q)
  if set(v)!={'nonce','report','source_state'} or v['nonce']!=nonce or v['source_state'] not in ('ok','acquisition_failed'):raise ValueError('reply')
  r=clean(v['report'],c)
  if old and (stamp(r['attempted_at'])<stamp(old['attempted_at']) or r['attempted_at']==old['attempted_at'] and r!=old):raise ValueError('rollback')
  t.atomic(c['report_file'],r);h['report_at']=r['attempted_at'];h['state']='source_stale' if time.time()-stamp(r['attempted_at'])>=300 else v['source_state']
 except Exception:pass
 t.atomic(c['health_file'],h);return h

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['serve','pull']);p.add_argument('--config',required=True);p.add_argument('--interval',type=int,default=60);a=p.parse_args();os.umask(0o027)
 c=t.read_file(a.config,16384)
 if a.action=='serve':
  signal.alarm(10)
  try:
   if os.environ.get('SSH_ORIGINAL_COMMAND')!='preflight-status':raise ValueError('command')
   print(json.dumps(serve(c,t.decode(sys.stdin.buffer.read(1025),1024))));return 0
  except Exception:print('{"state":"unavailable"}');return 2
 if not 0<=a.interval<=240:raise ValueError('interval')
 paths=[Path(c[k]) for k in ('report_file','health_file','lock_file')]
 if len({p.resolve() for p in paths})!=3 or any(p.is_symlink() for p in paths):raise ValueError('separate paths')
 with os.fdopen(os.open(c['lock_file'],os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),'r+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  while True:
   r=pull(c);print(json.dumps(r),flush=True)
   if not a.interval:return 0 if r['state']=='ok' else 2
   time.sleep(a.interval)
if __name__=='__main__':raise SystemExit(main())
