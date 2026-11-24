"""Disposable dm test runner; only communicates with its fresh scoped broker."""
import sys,json,pathlib,subprocess,threading,time
b=pathlib.Path('/tmp/owr-review-safe-20261124')
scope=json.loads(sys.stdin.readline())['scope']
(b/'aws.json').write_text(json.dumps(scope));(b/'ipc').mkdir(exist_ok=True)
d=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock']
def run(args):
 r=subprocess.run(d+args,capture_output=True,text=True,timeout=120)
 if r.returncode:raise RuntimeError(r.stderr[-1200:])
wp=['exec','owr-review-20261124-php','php','/lab/wp.phar','--allow-root']
run(['exec','owr-review-20261124-db','mariadb','-uroot','-pisolated-review-only','--socket=/socket/mysql.sock','-e','DROP DATABASE IF EXISTS review; CREATE DATABASE review;'])
run(wp+['core','install','--url=http://isolated-review.invalid','--title=Isolated Review','--admin_user=review','--admin_password=isolated-review-only','--admin_email=review@example.invalid','--skip-email'])
run(wp+['plugin','activate','ozeki-resilience','ozeki-markdown-documents','contact-form-7','flamingo','tablepress','wp-members','advanced-custom-fields'])
def replies():
 for line in sys.stdin:
  r=json.loads(line);key=r.pop('id')
  assert len(key)==24 and all(c in '0123456789abcdef' for c in key)
  p=b/'ipc'/(key+'.reply-tmp');p.write_text(json.dumps(r));p.rename(p.with_suffix('.response'))
threading.Thread(target=replies,daemon=True).start()
done={p.name for p in (b/'ipc').glob('*.request')}
(b/'live').write_text(scope['prefix'])
out=(b/'real-s3-result.json').open('w');err=(b/'real-s3-stderr.txt').open('w')
p=subprocess.Popen(d+['exec','owr-review-20261124-php','php','/lab/tests/review-roundtrip.php'],stdout=out,stderr=err)
start=time.monotonic()
try:
 while p.poll() is None:
  if time.monotonic()-start>1200:raise TimeoutError('Isolated S3 trial timed out')
  for f in (b/'ipc').glob('*.request'):
   if f.name in done:continue
   done.add(f.name);q=json.loads(f.read_text());q['id']=f.stem;print(json.dumps(q),flush=True)
  time.sleep(.025)
 out.close();err.close()
 print(json.dumps({'done':True,'exit':p.returncode,'result':(b/'real-s3-result.json').read_text(),'stderr':(b/'real-s3-stderr.txt').read_text()}),flush=True)
finally:(b/'live').unlink(missing_ok=True)
