"""Dedicated actual SSH registry -> real recovery entry -> offline WP/MariaDB.
Storage GET defaults to a local fixture; --real-s3 uses the existing reader through a test broker. Docker socket grants
host-daemon authority: run only on the dedicated development Docker host.
"""
import argparse,base64,datetime as dt,hashlib,importlib.util,json,os,secrets,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--execute-lab',action='store_true');p.add_argument('--real-s3',action='store_true');a=p.parse_args()
 if not a.execute_lab:p.error('--execute-lab required')
 out=a.output.resolve();out.mkdir(parents=True,mode=0o700,exist_ok=False)
 r=load('lab_restore','first-site-daily-restore.py');g=r.g
 previous=json.loads((a.fixture/'trust-snapshot/approved.json').read_bytes());assert previous['paired']['site_id']=='generated-first-site'
 assets={role:(a.fixture/'verified-assets'/name).read_bytes() for role,name in g.NAMES.items()};paired=previous['paired'];g.validate_capture(paired,assets)
 for role,data in assets.items():(out/g.NAMES[role]).write_bytes(data)
 now=g.now();until=(now+dt.timedelta(days=36)).isoformat();modified=now.isoformat();store={}
 def put(bucket,key,body):store[key]=body;return 'dedicated-version-one'
 def get(loc):return dict(body=store[loc['key']],version_id='dedicated-version-one',reader_identity='OwrM1RecoveryReader',mode='GOVERNANCE',last_modified=modified,retain_until=until)
 m=previous if a.real_s3 else g.build(assets,paired,r.d.SITE,'AWS-'+'7'*16,r.d.transport.BUCKET,r.d.transport.REGION,'my-ssm-role','OwrM1RecoveryReader',put,get)
 def run(*args,data=None,check=True,timeout=120):
  q=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
  if check and q.returncode:raise RuntimeError(q.stderr.decode()[-1200:]+q.stdout.decode()[-1200:])
  return q
 pub=out/'publisher';pub.mkdir();bundles={}
 for name,seq,setid in [('old',1,m['set_id']),('latest',2,m['set_id']),('revoked',1,'AWS-'+'8'*16)]:
  doc=dict(m,sequence=seq,set_id=setid)
  if name=='revoked':
   doc=json.loads(json.dumps(doc))
   for e in doc['assets']:e['locator']['key']=e['locator']['key'].replace(m['set_id'],setid)
  f=pub/(name+'.json');f.write_bytes(g.encode(doc));trust=out/name
  run('python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',str(f),'--operator',str(trust))
  bundles[name]={'trust':str(trust),'set_id':setid,'config_hash':paired['config_sha256'],'document_hash':g.sha(f.read_bytes()),'key_hash':g.sha((trust/'public.pem').read_bytes())}
 entries=[dict(site_id=r.d.SITE,set_id=bundles[n]['set_id'],status='revoked' if n=='revoked' else 'active',minimum_sequence=2 if n=='latest' else 1,public_key_sha256=bundles[n]['key_hash'],approved_document_sha256=bundles[n]['document_hash']) for n in ['latest','revoked']]
 registry=dict(format='owr-current-recovery-trust-v1',revision=1,issued_at=modified,expires_at=(now+dt.timedelta(hours=1)).isoformat(),revoked_key_sha256=[],sets=entries)
 raw=json.dumps(registry).encode();(out/'registry.json').write_bytes(raw)
 settings=dict(real_s3=a.real_s3,bundles=bundles,modified=modified,until=until,registry_sha256=g.sha(raw));(out/'settings.json').write_text(json.dumps(settings))
 for key in ['deploy','host']:run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(out/key))
 prefix='owr-trust-entry-'+secrets.token_hex(5);receiver=prefix+'-receiver';sender=prefix+'-sender';created=[]
 def ex(name,*args,**kw):return run('docker','exec',*(['-i'] if kw.get('data') is not None else []),name,*args,**kw)
 def write(path,text,mode='644'):
  local=out/'upload';local.write_text(text);run('docker','cp',str(local),receiver+':'+path);ex(receiver,'chown','root:root',path);ex(receiver,'chmod',mode,path)
 broker=None
 try:
  if a.real_s3:
   r.d.transport.preflight()
   broker=load('trust_real_broker','trust-recovery-s3-broker.py').Broker(out,m)
  created.append(receiver);run('docker','run','-d','--name',receiver,'--network','none','--memory','512m','-e','TMPDIR='+str(out/'tmp'),'-v',str(out)+':'+str(out),'-v',str(ROOT)+':/repo:ro','-v','/var/run/docker.sock:/var/run/docker.sock','-v','/usr/bin/docker:/usr/bin/docker:ro','--entrypoint','sleep','owr-external-lab:local','infinity')
  (out/'tmp').mkdir()
  created.append(sender);run('docker','run','-d','--name',sender,'--network','container:'+receiver,'--memory','256m','-v',str(out)+':'+str(out),'-v',str(ROOT)+':/repo:ro','--entrypoint','sleep','owr-external-lab:local','infinity')
  ex(receiver,'mkdir','-p','/opt/owr/tools','/etc/owr-trust','/run/sshd')
  for file in ['trust-registry-ssh.py','notification-transfer.py','update-current-recovery-trust.py','current-recovery-trust.py']:run('docker','cp',str(ROOT/'tools'/file),receiver+':/opt/owr/tools/'+file)
  ex(receiver,'chown','-R','root:root','/opt/owr');ex(receiver,'chmod','-R','go-w','/opt/owr')
  write('/etc/ssh/lab-host',(out/'host').read_text(),'600')
  write('/etc/ssh/lab-keys','restrict,command="/usr/bin/python3 -B /opt/owr/tools/trust-registry-ssh.py endpoint" '+(out/'deploy.pub').read_text())
  ex(receiver,'usermod','-p','*','root')
  write('/etc/ssh/lab-config','\n'.join(['Port 2222','HostKey /etc/ssh/lab-host','AuthorizedKeysFile /etc/ssh/lab-keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin forced-commands-only','DisableForwarding yes','PermitTTY no','PidFile /run/sshd/lab.pid'])+'\n')
  ex(receiver,'/usr/sbin/sshd','-f','/etc/ssh/lab-config')
  (out/'known').write_text('owr-trust-entry '+(out/'host.pub').read_text())
  conn=dict(site_id='entry',host='127.0.0.1',port=2222,user='root',identity_file=str(out/'deploy'),known_hosts=str(out/'known'));(out/'conn.json').write_text(json.dumps(conn))
  args=['python3','/repo/tools/trust-registry-ssh.py','apply','--connection',str(out/'conn.json'),'--candidate',str(out/'registry.json'),'--candidate-sha256',g.sha(raw),'--expected-current-sha256','absent']
  deployed=json.loads(ex(sender,*args).stdout);assert deployed['state']=='applied';print('SSH_REGISTRY_APPLIED',flush=True)
  inspected=json.loads(ex(sender,'python3','/repo/tools/trust-registry-ssh.py','inspect','--connection',str(out/'conn.json')).stdout);assert inspected['sha256']==g.sha(raw)
  result=json.loads(ex(receiver,'python3','/repo/tools/trust-ssh-recovery-cases.py','--workspace',str(out),timeout=420).stdout)
  result.update(ssh_deployment=deployed,ssh_inspection=inspected,storage='real experimental S3 fixed versions via allow-listed test broker' if a.real_s3 else 'local generated fixed-version adapter; no real S3',receiver='dedicated container filesystem; shared WSL kernel',docker_daemon='dedicated development daemon shared with lab orchestration; no claim of daemon independence')
  if broker:
   assert len(broker.events)==2 and all(e['state']=='received' for e in broker.events)
   assert broker.adapter.request_count==2
   result['real_s3']={'requests':broker.adapter.request_count,'operations':broker.adapter.operations,'no_put':True}
  (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 finally:
  if broker:broker.close()
  if (out/'result.json').exists():
   for name in reversed(created):run('docker','rm','-f',name,check=False)
   for key in ['deploy','host']:(out/key).unlink(missing_ok=True)
  else:
   (out/'incomplete.json').write_text(json.dumps({'state':'inspect_before_retry','containers':created}))
 if (out/'result.json').exists():
  result=json.loads((out/'result.json').read_text());result['dedicated_ssh_containers_removed']=all(run('docker','inspect',n,check=False).returncode!=0 for n in created);(out/'result.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
