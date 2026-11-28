import subprocess,json,hashlib,sys
from pathlib import Path
b=Path('/tmp/owr-recovery-fields-20261128');docker=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];web='owr-fields-20261128-web'
def run(args):
 p=subprocess.run(docker+['exec',web]+args,capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError((p.stderr+p.stdout)[:4000])
 return p.stdout
for f in ['RecoveryRules.php','RecoveryContent.php','AcfHistory.php','Plugin.php']:
 run(['cp','/lab/'+f,'/var/www/html/wp-content/plugins/ozeki-resilience/src/'+f])
 run(['php','-l','/var/www/html/wp-content/plugins/ozeki-resilience/src/'+f])
for test in ['recovery-field-contract.php','review-safe-content.php']:
 result=run(['php','/tmp/wp.phar','--allow-root','eval-file','/lab/tests/'+test]);(b/(test+'.txt')).write_text(result);print(result,flush=True)
def cli(*args):
 text=run(['php','-d','memory_limit=256M','/lab/fields.php',*args])
 try:return json.loads(text)
 except ValueError:return text.strip()
run(['mkdir','-p','-m','700','/lab/work'])
results=json.loads((b/'results.json').read_text()) if '--second-only' in sys.argv else {}
if '--second-only' not in sys.argv:
 if '--resume' not in sys.argv:cli('seed')
 results['source_revision']=cli('revision')
 results['source_custom']=cli('submit','custom');results['capture']=cli('capture') if '--resume' not in sys.argv else 'Existing captured reference'
originals={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (b/'objects').rglob('*') if f.is_file()}
for stage in (['second'] if '--second-only' in sys.argv else ['first','second']):
 if stage=='second' and '--second-only' not in sys.argv:results['recapture']=cli('capture','second')
 results[stage+'_restore']=cli('restore',stage)
 results[stage+'_revision']=cli('revision')
 assert results[stage+'_revision']['restored_old_markdown'] and results[stage+'_revision']['derived_hash_matches']
 results[stage+'_use']=cli('use')
 assert all(results[stage+'_use'][k] for k in ['instructions_retained','instructions_html_safe','acf_value_unchanged'])
 assert results[stage+'_use']['filename']=='technical-source.md'
 for prefix in ['your','custom']:
  r=cli('submit',prefix);results[stage+'_'+prefix]=r
  assert r['received'] and r['name']=='Fixture Reader' and r['email']=='reader@example.invalid' and r['subject']=='Fixture subject' and r['receipt_subject']=='Fixture subject'
 (b/'results.json').write_text(json.dumps(results,indent=2));print(stage+' recovery/use passed',flush=True)
assert all(Path(f).is_file() and hashlib.sha256(Path(f).read_bytes()).hexdigest()==sha for f,sha in originals.items())
results['existing_trial_originals_unchanged']=True;results['storage']='isolated local SDK transport';results['external_email_sent']=False
(b/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results),flush=True)
