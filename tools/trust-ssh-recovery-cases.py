"""Recovery-entry integration cases; actual default offline restore, fixture or allow-listed real S3 storage."""
import argparse,importlib.util,json,shutil,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('recovery',ROOT/'tools/first-site-daily-restore.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspace',required=True,type=Path);a=p.parse_args();w=a.workspace;c=json.loads((w/'settings.json').read_text());counts={'constructed':0,'gets':0};checks=[]
 def factory(path):
  counts['constructed']+=1
  class Reader:
   def get(self,loc):
    counts['gets']+=1
    if c.get('real_s3'):
     with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
      sock.settimeout(360);sock.connect(str(w/'s3-reader.sock'));f=sock.makefile('rwb');f.write(json.dumps(loc).encode()+b'\n');f.flush();response=json.loads(f.readline(8193))
     if 'error' in response:raise RuntimeError(response['error'])
     response['body']=Path(response.pop('body_file')).read_bytes();return response
    return dict(body=(w/Path(loc['key']).name).read_bytes(),version_id='dedicated-version-one',reader_identity='OwrM1RecoveryReader',mode='GOVERNANCE',last_modified=c['modified'],retain_until=c['until'])
  return Reader()
 for name in ['old','revoked']:
  b=c['bundles'][name];out=w/('restore-'+name)
  # These complete bundles are valid under their own independently selected pin/signature.
  r.g.authorize(Path(b['trust']),Path(b['trust'])/'approved.json',Path(b['trust'])/'approved.sig',r.d.SITE,b['set_id'])
  try:r.recover(destination=out,adapter_factory=factory,**b)
  except ValueError:pass
  else:raise AssertionError(name+' was accepted')
  assert counts=={'constructed':0,'gets':0} and not out.exists();checks.append({'name':name+'_complete_bundle_blocked_before_get','passed':True})
  if c.get('real_s3'):assert not (w/'real-get-events.json').exists()
 b=dict(c['bundles']['latest']);altered=w/'tampered';shutil.copytree(b['trust'],altered);(altered/'approved.sig').write_bytes(b'bad');b['trust']=str(altered)
 try:r.recover(destination=w/'restore-tampered',adapter_factory=factory,**b)
 except ValueError:pass
 else:raise AssertionError('invalid signature accepted')
 if c.get('real_s3'):assert not (w/'real-get-events.json').exists()
 assert counts=={'constructed':0,'gets':0};checks.append({'name':'latest_registry_does_not_bypass_signature','passed':True})
 report=r.recover(destination=w/'restore-latest',adapter_factory=factory,**c['bundles']['latest'])
 assert report['passed'] and report['isolated_restore']['http']['status']==200 and report['isolated_restore']['resources_removed']
 assert counts=={'constructed':1,'gets':2} and report['current_trust']['registry_sha256']==c['registry_sha256']
 checks.append({'name':'latest_approved_actual_wordpress_restore','passed':True})
 print(json.dumps({'format':'owr-trust-ssh-recovery-v1','checks':checks,'passed':len(checks),'counts':counts,'isolated_restore':report['isolated_restore'],'registry_sha256':report['current_trust']['registry_sha256'],'production_changes':False,'observation_changes':False}))
if __name__=='__main__':main()
