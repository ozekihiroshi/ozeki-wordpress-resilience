"""Independent approval entry for generated RBR S3 kits. No automatic signing/publication."""
import argparse, datetime as dt, importlib.util, json, subprocess, tempfile
from pathlib import Path

def load(name,file):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v=load('approval_primitives','verify-recovery-approval.py')
c=load('current_trust','current-recovery-trust.py')
k=load('kit','rbr-s3-kit.py')

def verify(trust,approval,signature,receipt,site,set_id):
 pin=json.loads((trust/'pin.json').read_bytes());key=trust/'public.pem';raw=approval.read_bytes()
 v.checked(len(raw)<65536,'Approval too large')
 v.checked(v.digest(key.read_bytes())==pin['public_key_sha256'] and pin['status']=='active' and pin['site_id']==site,'Untrusted key/site')
 # Verify the exact bytes, not a reserialized JSON document.
 result=subprocess.run(['openssl','dgst','-sha256','-verify',str(key),'-signature',str(signature),str(approval)],capture_output=True,timeout=10)
 v.checked(result.returncode==0,'Invalid signature')
 a=json.loads(raw)
 v.checked(a['format']=='owr-rbr-kit-approval-v1' and a['algorithm']=='rsa-sha256','Approval format')
 v.checked(a['site_id']==site and a['set_id']==set_id,'Wrong target')
 v.checked(a['scope']=='generated-private-reconstruction' and a['public_activation'] is False,'Scope mismatch')
 now=dt.datetime.now(dt.timezone.utc);issued=c.timestamp(a['issued_at']);expires=c.timestamp(a['expires_at'])
 v.checked(issued<=now<expires and dt.timedelta(0)<expires-issued<=dt.timedelta(days=7),'Invalid approval time')
 v.checked(type(a['sequence']) is int and a['sequence']>=pin['minimum_sequence'],'Stale approval')
 v.checked(v.digest(raw)==pin['approved_document_sha256'],'Unapproved document')
 v.checked(a['root_receipt']==json.loads(receipt.read_bytes()),'Root fixed version mismatch')
 return c.current(trust,approval,site,set_id)

def verify_received(work,receipt):
 root_raw=(work/'root-manifest.json').read_bytes();ref=json.loads(receipt.read_bytes())
 v.checked(len(root_raw)==ref['size_bytes'] and v.digest(root_raw)==ref['sha256'],'Root changed after fetch')
 root=json.loads(root_raw);seen=set();archives=[]
 v.checked(not any(p.is_symlink() for p in work.rglob('*')),'Symlink in received kit')
 def visit(ref):
  raw=(work/'bundle/cache'/(ref['sha256']+'.blob')).read_bytes()
  v.checked(len(raw)==ref['size_bytes'] and v.digest(raw)==ref['sha256'],'Received asset changed')
  if ref['sha256'] in seen:return raw
  seen.add(ref['sha256'])
  try:value=json.loads(raw)
  except (ValueError,UnicodeError):return raw
  def walk(value):
   if isinstance(value,dict):
    if {'locator','sha256','size_bytes'}<=set(value):visit(value)
    else:
     for _,x in k.dependency_items(value):walk(x)
   elif isinstance(value,list):
    for x in value:walk(x)
  walk(value)
  if isinstance(value,dict) and value.get('kind')=='docker-save-gzip-chunks-v1':archives.append(value)
  return raw
 v.checked((work/'bundle/definition.json').read_bytes()==visit(root['definition_ref']),'Definition changed')
 k.verify_bound_root(root,visit)
 expected=set()
 for item in root['code']:
  expected.add(item['path']);path=work/'kit'/item['path']
  v.checked(not path.is_symlink() and path.read_bytes()==visit(item['ref']),'Execution code changed')
 actual={p.relative_to(work/'kit').as_posix() for p in (work/'kit').rglob('*') if p.is_file()}
 v.checked(actual==expected,'Unexpected execution code')
 images=json.loads((work/'images.json').read_bytes());v.checked(len(images)==len(archives),'Image inventory changed')
 for index,(item,descriptor) in enumerate(zip(images,archives)):
  v.checked(item=={'path':str(work/('image-'+str(index)+'.tar.gz')),'image_id':descriptor['image_id'],'sha256':descriptor['archive_sha256'],'size_bytes':descriptor['archive_size_bytes']},'Image binding changed')
 with tempfile.TemporaryDirectory(prefix='owr-recheck-plan-') as tmp:
  generated=Path(tmp)/'plan.json'
  subprocess.run(['php',str(work/'kit/tools/rbr-plan.php'),'--definition='+str(work/'bundle/definition.json'),'--objects='+str(work/'bundle/cache'),'--output='+str(generated)],check=True,stdout=subprocess.DEVNULL)
  v.checked(generated.read_bytes()==(work/'bundle/plan.json').read_bytes(),'Plan changed')

def execute(trust,approval,signature,receipt,site,set_id,work,output,received=False):
 work=work.resolve();output=output.resolve()
 v.checked((work.is_dir() if received else not work.exists()) and not output.exists(),'Fresh output and appropriate input required')
 for path in (trust,approval,signature,receipt,Path(__file__)):
  v.checked(not path.resolve().is_relative_to(work) and not path.resolve().is_relative_to(output),'Independent trust required')
 checkpoint=verify(trust,approval,signature,receipt,site,set_id)
 if not received:
  # fetch verifies all fixed references before executing the pinned planner.
  with tempfile.TemporaryDirectory(prefix='owr-approved-receipt-') as tmp:
   pinned=Path(tmp)/'receipt.json'
   signed=json.loads(approval.read_bytes())['root_receipt'];pinned.write_bytes(k.canonical(signed))
   v.checked(json.loads(receipt.read_bytes())==signed,'Receipt changed')
   k.fetch(pinned,work,lambda: v.checked(verify(trust,approval,signature,receipt,site,set_id)==checkpoint,'Trust changed during transfer'))

 v.checked(verify(trust,approval,signature,receipt,site,set_id)==checkpoint,'Trust changed during transfer')
 verify_received(work,receipt)
 # Only a fully revalidated private kit reaches image loading; no prior success flag is trusted.
 for item in json.loads((work/'images.json').read_bytes()):
  path=Path(item['path']);v.checked(path.stat().st_size==item['size_bytes'] and v.digest(path.read_bytes())==item['sha256'],'Image changed')
  subprocess.run(['docker','load','--input',str(path)],check=True,stdout=subprocess.DEVNULL)
  actual=subprocess.run(['docker','image','inspect',item['image_id'],'--format','{{.Id}}'],check=True,capture_output=True,text=True).stdout.strip()
  v.checked(actual==item['image_id'],'Image identity mismatch')
 v.checked(verify(trust,approval,signature,receipt,site,set_id)==checkpoint,'Trust changed before reconstruction')
 verify_received(work,receipt)
 subprocess.run(['python3','-B',str(work/'kit/tools/rbr-reconstruct-lab.py'),'--allow-disposable-lab','--bundle',str(work/'bundle'),'--output',str(output)],check=True)
 result=json.loads((output/'result.json').read_bytes());v.checked(result['state']=='PASS','Reconstruction failed')
 (output/'approval-verification.json').write_bytes(k.canonical({'state':'PASS','approval_sha256':v.digest(approval.read_bytes()),'root_receipt':json.loads(receipt.read_bytes()),'authority':checkpoint,'public_activation':False}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['trust','approval','signature','receipt','work','output']:p.add_argument('--'+name,type=Path,required=True)
 for name in ['site-id','set-id']:p.add_argument('--'+name,required=True)
 p.add_argument('--received',action='store_true',help='Revalidate a complete received kit; never resume a partial WordPress target')
 p.add_argument('--allow-disposable-lab',action='store_true');a=p.parse_args()
 if not a.allow_disposable_lab:p.error('Explicit generated lab opt-in required')
 execute(a.trust,a.approval,a.signature,a.receipt,a.site_id,a.set_id,a.work,a.output,a.received)
