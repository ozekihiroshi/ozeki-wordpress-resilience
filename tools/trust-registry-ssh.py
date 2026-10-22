"""Pinned SSH transport for the reviewed fixed-destination registry updater; never retries."""
import argparse,base64,importlib.util,json,os,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('notification-transfer');u=load('update-current-recovery-trust');original=t.command

def command(c):
 args=original(c);args[args.index('HostKeyAlias=owr-notification-'+c['site_id'])]='HostKeyAlias=owr-trust-'+c['site_id'];args[-1]='trust-registry';return args
t.command=command

def endpoint(packet):
 if not isinstance(packet,dict):raise ValueError('packet')
 if packet=={'action':'inspect'}:
  u.protected_parent();raw=u.read_current()
  return {'state':'inspected','sha256':u.sha(raw) if raw is not None else 'absent','revision':u.validate(raw,False)['revision'] if raw is not None else None}
 if set(packet)!={'action','candidate','candidate_sha256','expected_current_sha256'} or packet['action'] not in ('validate','apply'):raise ValueError('packet')
 raw=base64.b64decode(packet['candidate'],validate=True)
 u.g.require(len(raw)<=32768,'SSH candidate limit')
 u.protected_parent()
 fd,path=tempfile.mkstemp(prefix='.incoming-',dir=u.g.AUTHORITY.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(raw)
  return {'state':'applied' if packet['action']=='apply' else 'validated',**u.deploy(path,packet['expected_current_sha256'],packet['candidate_sha256'],packet['action']=='apply')}
 finally:os.unlink(path)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['endpoint','inspect','validate','apply']);p.add_argument('--connection');p.add_argument('--candidate');p.add_argument('--candidate-sha256');p.add_argument('--expected-current-sha256');a=p.parse_args()
 if a.action=='endpoint':
  try:result=endpoint(t.decode(sys.stdin.buffer.read(65537),65536))
  except ValueError:result={'state':'rejected','next':'inspect_before_reviewed_retry'}
  except Exception:result={'state':'unknown','next':'inspect_before_any_retry'}
 else:
  c=t.read_file(a.connection,16384);packet={'action':a.action}
  if a.action!='inspect':
   if not all([a.candidate,a.candidate_sha256,a.expected_current_sha256]):p.error('candidate and reviewed hashes required')
   with Path(a.candidate).open('rb') as f:raw=f.read(32769)
   u.g.require(len(raw)<=32768 and u.sha(raw)==a.candidate_sha256,'candidate size/hash')
   packet.update(candidate=base64.b64encode(raw).decode(),candidate_sha256=a.candidate_sha256,expected_current_sha256=a.expected_current_sha256)
  try:result=t.ssh(c,packet)
  except Exception:result={'state':'unknown','next':'inspect_before_any_retry'}
 print(json.dumps(result));return 0 if a.action=='endpoint' or result.get('state') in ('inspected','validated','applied') else 2
if __name__=='__main__':raise SystemExit(main())
