"""Allowlisted observer snapshot and fixed-command SSH read-only transfer."""
import argparse,importlib.util,json,os,re,secrets,sys
from datetime import datetime,timezone
from pathlib import Path
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('notification-transfer')
KINDS={'monitor_stopped','heartbeat_invalid','notification_delivery_failed'}
def instant(value):
 if not isinstance(value,str) or len(value)>64:raise ValueError('timestamp')
 stamp=datetime.fromisoformat(value)
 if stamp.tzinfo is None or stamp.timestamp()>datetime.now(timezone.utc).timestamp()+5:raise ValueError('timestamp')
 return stamp
def count(value):
 if type(value)is not int or not 0<=value<=1000000000:raise ValueError('count')
 return value
def clean(v,site):
 if v['format']!='owr-observer-status-v1' or v['site_id']!=site:raise ValueError('site binding')
 t.ident(site);t.ident(v['monitor_id']);observed=instant(v['observed_at'])
 if type(v['simulated']) is not bool:raise ValueError('simulation')
 targets={}
 for key in ('reachability','watchdog'):
  item=v['targets'][key];seen=item['last_seen']
  if seen is not None and instant(seen).timestamp()>observed.timestamp()+5:raise ValueError('last seen')
  if not isinstance(item['active'],list) or len(item['active'])>3 or any(x not in KINDS for x in item['active']):raise ValueError('alarm')
  if item['observation'] not in ('confirmed','unavailable','invalid','missing'):raise ValueError('observation')
  targets[key]=dict(last_seen=seen,active=item['active'],pending=count(item['pending']),observation=item['observation'])
 delivery=v['delivery']
 if delivery['state'] not in ('ok','failed','unknown'):raise ValueError('delivery')
 history=[]
 if not isinstance(v['history'],list) or len(v['history'])>20:raise ValueError('history')
 for e in v['history']:
  if e['target'] not in targets or e['kind'] not in KINDS or e['transition'] not in ('opened','resolved') or instant(e['at'])>observed:raise ValueError('history event')
  history.append({k:e[k] for k in ('target','kind','transition','at')})
 result=dict(format=v['format'],site_id=site,monitor_id=v['monitor_id'],observed_at=v['observed_at'],simulated=v['simulated'],targets=targets,delivery=dict(state=delivery['state'],pending=count(delivery['pending'])),history=history)
 if 'configuration' in v:
  c=v['configuration']
  if not re.fullmatch('[a-f0-9]{64}',c['active_hash']) or not isinstance(c['revision_token'],str) or len(c['revision_token'])>64 or type(c.get('processing_error',False)) is not bool:raise ValueError('configuration report')
  if c['revision_token']:t.ident(c['revision_token'])
  clean=dict(active_hash=c['active_hash'],revision=count(c['revision']),revision_token=c['revision_token'],last_request=None,processing_error=c.get('processing_error',False))
  if type(c.get('test_processing_error',False)) is not bool:raise ValueError('test processing flag')
  clean['test_processing_error']=c.get('test_processing_error',False);clean['tests']=[]
  if not isinstance(c.get('tests',[]),list) or len(c.get('tests',[]))>20:raise ValueError('test results')
  for r in c.get('tests',[]):
   if not re.fullmatch(t.UUID,r['request_id']) or r['status'] not in ('accepted','unknown','rejected','retry','blocked'):raise ValueError('test result')
   t.ident(r['channel_id']);t.ident(r['revision_token']);count(r['revision'])
   clean['tests'].append({k:r[k] for k in ('request_id','channel_id','revision','revision_token','status')})
  if c.get('last_request') is not None:
   r=c['last_request']
   if not re.fullmatch(t.UUID,r['request_id']) or r['outcome'] not in ('applied','rejected','conflict') or r['reason'] not in ('applied','policy','expired','conflict'):raise ValueError('apply result')
   t.ident(r['revision_token']);count(r['revision']);clean['last_request']={k:r[k] for k in ('request_id','revision','revision_token','outcome','reason')}
  result['configuration']=clean
 return result
def endpoint(c,p):
 if set(p)!={'site_id','nonce'} or p['site_id']!=c['site_id'] or not re.fullmatch('[a-f0-9]{32}',p['nonce']):raise ValueError('request')
 return dict(nonce=p['nonce'],report=clean(t.read_file(c['public_status_file'],32768),c['site_id']))
original=t.command
def command(c):
 args=original(c);args[-1]='observer-status';return args
t.command=command
def pull(c,transport=None):
 with Path(c['lock_file']).open('a') as lock:
  import fcntl
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  p=dict(site_id=c['site_id'],nonce=secrets.token_hex(16));r=(transport or t.ssh)(c,p)
  if set(r)!={'nonce','report'} or r['nonce']!=p['nonce']:raise ValueError('response binding')
  report=clean(r['report'],c['site_id']);target=Path(c['status_file'])
  if target.exists():
   old=clean(t.read_file(target,32768),c['site_id'])
   if old['monitor_id']!=report['monitor_id'] or instant(old['observed_at'])>instant(report['observed_at']) or (old['observed_at']==report['observed_at'] and old!=report):raise ValueError('report rollback')
  t.atomic(target,report)
  return report
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['endpoint','pull']);p.add_argument('--config',required=True);a=p.parse_args();os.umask(0o027)
 try:
  c=t.read_file(a.config,16384)
  if a.action=='endpoint':
   import resource,signal
   resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024));signal.alarm(10)
   if os.environ.get('SSH_ORIGINAL_COMMAND')!='observer-status':raise ValueError('forced command only')
   print(json.dumps(endpoint(c,t.decode(sys.stdin.buffer.read(1025),1024))))
  else:pull(c);print('{"stored":true}')
  return 0
 except Exception as e:print(json.dumps(dict(error_type=type(e).__name__)));return 1
if __name__=='__main__':raise SystemExit(main())
