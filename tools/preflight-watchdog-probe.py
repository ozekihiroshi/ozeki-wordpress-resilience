"""Read-only preflight completion endpoint for an independent observer."""
import argparse,importlib.util,json,os,re,signal,sys,resource
from pathlib import Path
s=importlib.util.spec_from_file_location('preflight',Path(__file__).with_name('preflight-transfer.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
def endpoint(c,q):
 if set(q)!={'format','nonce'} or q['format']!='owr-watchdog-probe-v1' or not isinstance(q['nonce'],str) or not re.fullmatch('[a-f0-9]{32}',q['nonce']):raise ValueError('request')
 p.t.ident(c['monitor_id'])
 status='missing';value=None
 try:
  r=p.clean(p.t.read_file(c['report_file'],65536),c);h=p.t.read_file(c['health_file'],8192)
  if h.get('format')!='owr-preflight-transfer-v1' or h.get('site_id')!=c['site_id'] or h.get('config_sha256')!=c['config_sha256'] or h.get('state') not in ('ok','acquisition_failed','source_stale'):raise ValueError('health')
  at=h['attempted_at'];committed=h['report_at'];p.stamp(at);p.stamp(committed)
  if p.stamp(committed)>p.stamp(r['attempted_at']):raise ValueError('health ahead of report')
  # Health is published after the report. During publication, retain the last
  # committed completion; never credit a newer report or the current probe time.
  # A stalled health file therefore ages naturally into monitor_stopped.
  completed=min((at,committed),key=p.stamp)
  value=dict(format='owr-monitor-heartbeat-v1',monitor_id=c['monitor_id'],completed_at=completed,undelivered=0,open_incidents=0);status='present'
 except FileNotFoundError:pass
 except Exception:status='invalid'
 return dict(format='owr-watchdog-probe-result-v1',nonce=q['nonce'],monitor_id=c['monitor_id'],status=status,heartbeat=value)
def main():
 a=argparse.ArgumentParser();a.add_argument('--config',required=True);c=a.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024));signal.alarm(10)
 if os.environ.get('SSH_ORIGINAL_COMMAND')!='watchdog-probe':raise ValueError('forced command only')
 print(json.dumps(endpoint(p.t.read_file(c.config,4096),p.t.decode(sys.stdin.buffer.read(1025),1024))))
if __name__=='__main__':main()
