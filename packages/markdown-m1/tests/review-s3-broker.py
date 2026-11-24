"""Test-only stdin broker. Uses host EC2 role, never exports credentials."""
import sys,json,pathlib,uuid
b=pathlib.Path('/tmp/owr-review-safe-20261124-broker')
sys.path[:0]=[str(b/'python-sdk'),str(b)]
from live import Live
lab=b/('run-'+uuid.uuid4().hex);lab.mkdir(mode=0o700)
x=Live(lab)
print(json.dumps({'scope':x.scope}),flush=True)
try:
 for line in sys.stdin:
  q=json.loads(line)
  try:
   r=x.fingerprint() if q['operation']=='FixtureFingerprint' else x.request(q['operation'],q['args'])
   out={'id':q['id'],'success':True,'result':r}
  except Exception as e:out={'id':q['id'],'success':False,'error':getattr(e,'response',{}).get('Error',{}).get('Code',type(e).__name__)}
  print(json.dumps(out,default=lambda v:v.isoformat()),flush=True)
finally:
 (lab/'final-versions.json').write_text(json.dumps(x.fingerprint(),indent=2))
 x.stop();(lab/'live').unlink(missing_ok=True)
