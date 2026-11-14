import subprocess,os,time,json,zipfile,hashlib,tarfile,urllib.request
from pathlib import Path
b=Path(__file__).resolve().parent;tag='owr-coexist-'+str(int(time.time()));made=[];sites={};e=b/'results';e.mkdir(exist_ok=True)
live=os.getenv('OWR_ATTACHMENT_LIVE')=='1'
aws={'bucket':'ceri-link-resilience-lock-lab-121426368082','owner':'121426368082','prefix':'sites/isolated-queue-lab/delete-validation-20261026/onboarding-20261026/input-audit-20261111/acf-fix-only/attachment-live-'+os.urandom(16).hex()+'/'}
def run(*args,check=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=240)
 if check and p.returncode:raise RuntimeError(str(args[:5])+p.stderr[-1600:]+p.stdout[-2400:])
 return p.stdout
def d(*args):return run('docker',*args)
def wp(side,*args):return d('exec',sites[side],'php','/tmp/wp.phar','--allow-root',*args)
def cli(side,mode,*args):
 raw=d('exec',sites[side],'php','/evidence/fixture.php',mode,*args);v=json.loads(raw);(e/(side+'-'+mode+('-'+'-'.join(args)if args else '').replace('/','_')+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2));assert 'operation_failed' not in v,v;return v
def fp():
 if live:
  v=json.loads(run('/usr/local/bin/aws','s3api','list-object-versions','--bucket',aws['bucket'],'--prefix',aws['prefix'],'--expected-bucket-owner',aws['owner'],'--output','json'))
  assert not v.get('DeleteMarkers');return {x['Key']+'#'+x['VersionId']:[x['ETag'],x['Size'],x['IsLatest']]for x in v.get('Versions',[])}
 return {str(p.relative_to(lab/'objects')):hashlib.sha256(p.read_bytes()).hexdigest()for p in (lab/'objects').rglob('*')if p.is_file()}
def match(a,z):
 keys=['post','page','markdown','acf','receipt','form_title','table','member_first','member_auth','restriction','image']
 differences={k:[a.get(k),z.get(k)]for k in keys if a.get(k)!=z.get(k)}
 assert not differences,differences
 assert not z['pending']and not z['related_pending']
 return True
try:
 lab=b/('lab-'+tag);lab.mkdir(exist_ok=False);os.chmod(lab,0o777);(lab/'control.json').write_text('{}');(lab/'objects').mkdir(exist_ok=True);os.chmod(lab/'objects',0o777)
 if live:
  assert not fp();(lab/'aws.json').write_text(json.dumps(aws));(e/'aws-scope.json').write_text(json.dumps(aws))
 net=tag+'-net';d('network','create',*([]if live else ['--internal']),net);made.append(('network',net))
 db=tag+'-db';dbvol=db+'-volume';d('volume','create',dbvol);made.append(('volume',dbvol));d('run','-d','--name',db,'--memory','768m','--cpus','0.5','--network',net,'-v',dbvol+':/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:11.8');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(['docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 plugins=[]
 for side in ['source','clean','third','legacy']:
  web=tag+'-'+side;sites[side]=web;volume=web+'-volume';d('volume','create',volume);made.append(('volume',volume));d('run','-d','--name',web,'--memory','768m','--cpus','0.5','--network',net,'-v',volume+':/var/www/html','-v',str(lab)+':/lab','-e','TRIAL_SIDE='+side,'-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+side+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
  for _ in range(60):
   if subprocess.run(['docker','exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
   time.sleep(1)
  d('cp',str(b/'wp.phar'),web+':/tmp/wp.phar');d('exec',web,'mkdir','-p','/evidence','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'transport.php'),web+':/var/www/html/wp-content/mu-plugins/trial.php');d('cp',str(b/'fixture.php'),web+':/evidence/fixture.php')
  wp(side,'core','install','--url=http://'+web,'--title=Coexistence fixture','--admin_user=operator','--admin_password=trial-only-password','--admin_email=operator@example.invalid','--skip-email')
  for slug in plugins+['candidate']:
   d('cp',str(b/(slug+'.zip')),web+':/evidence/'+slug+'.zip');wp(side,'plugin','install','/evidence/'+slug+'.zip','--activate')
  if False:
   for slug in ['download-monitor','ozeki-database-backup-for-s3']:
    d('cp',str(b/(slug+'.zip')),web+':/evidence/'+slug+'.zip');wp(side,'plugin','install','/evidence/'+slug+'.zip',*(['--activate']if side=='mixed'else []))
  if side!='legacy':d('cp',str(b/'src')+'/.',sites[side]+':/var/www/html/wp-content/plugins/ozeki-resilience/src/')
  d('exec',web,'mkdir','-p','/tmp/recovery-work');d('exec',web,'chown','-R','www-data:www-data','/var/www/html');print('Created '+side,flush=True)
 (b/'resources.json').write_text(json.dumps({'sites':sites,'created':made,'lab':str(lab)}))
 (lab/'manual.pdf').write_bytes((b/'manual.pdf').read_bytes())
 report={}
 cli('legacy','baseline','legacy')
 cli('legacy','baseline','red')
 cli('legacy','add','red')
 red=cli('legacy','state');assert len(red['attachments'])==2
 # The same real registration path on rc.16 stores rules, but no PDF originals.
 assert not any('/media/'in k or 'image-ingress/'in k for k in fp() if k.startswith((aws['prefix']if live else '')+'red/'))
 report['rc16_registration_gap_reproduced']=True
 cli('source','restore','legacy');report['old_format_read']=True
 cli('source','add','legacy');source=cli('source','state');assert not source['pending'] and not source['queue'],source
 print('PDF bundle saved',flush=True)
 assert len(source['attachments'])==2 and len(source['files'])>=4,source
 before=fp();rejected=cli('legacy','reject','legacy');assert rejected['rejected'] and rejected['unchanged'];assert before==fp();report['old_reader_new_tail_rejected']=rejected
 cli('source','baseline','newfull');before=fp();rejected=cli('legacy','reject','newfull');assert rejected['rejected'] and rejected['unchanged'];assert before==fp();report['old_reader_new_baseline_rejected']=rejected
 cli('source','index','legacy');before=fp();assert cli('legacy','reject-index','legacy')['rejected'];assert before==fp();report['old_reader_new_index_rejected']=True
 cli('clean','restore','legacy');clean=cli('clean','state');assert clean['attachments']==source['attachments']
 def verify_http(side,state):
  for path,v in state['files'].items():
   code=d('exec',sites[side],'curl','-s','-o','/dev/null','-w','%{http_code}','http://localhost/wp-content/'+path)
   assert code==('200' if v['state']=='public' else '404'),(path,code,v)
   if v['state']=='public':
    downloaded=d('exec',sites[side],'php','-r','$b=file_get_contents($argv[1]); if($b===false)exit(1); echo hash("sha256",$b);','http://localhost/wp-content/'+path)
    assert downloaded==v['hash'],(path,'HTTP bytes differ from preserved original')
   assert v['hash'],(path,'Missing original')
  assert not state['pending'] and not state['queue'],state
 verify_http('clean',clean)
 for path,v in source['files'].items():assert v['hash']==clean['files'][path]['hash'] and v['state']==clean['files'][path]['state']
 cli('clean','baseline','second');cli('clean','resave','second');saved=cli('clean','state');verify_http('clean',saved)
 before=fp();assert cli('third','restore','red')['missing']==10;assert before==fp();report['legacy_missing_originals_reported']=True
 before=fp();cli('third','restore','second');third=cli('third','state');assert before==fp();verify_http('third',third)
 assert third['files']==saved['files'] and third['attachments']==saved['attachments']
 report['pdf_roundtrip']={'files':len(third['files']),'attachments':len(third['attachments']),'private_preserved':sum(v['state']=='held'for v in third['files'].values()),'content_metadata_equal':True}
 cli('source','missing','missing');missing=cli('source','state');assert missing['pending'] and missing['errors'];assert cli('source','reject-incomplete')['rejected']
 cli('source','repair','missing');fixed=cli('source','state');assert not fixed['pending'] and not fixed['queue'],fixed
 report['missing_detected_and_retry_passed']=True
 (lab/'control.json').write_text('{"fail":"history"}');cli('clean','touch','second');assert cli('clean','state')['queue'];(lab/'control.json').write_text('{}');cli('clean','resume','second');assert not cli('clean','state')['queue'];report['interrupted_confirmation_resumed']=True
 cli('clean','delete','second');deleted=cli('clean','state');assert not deleted['pending'] and not deleted['queue'];assert len(deleted['attachments'])==1;report['attachment_deletion_confirmed']=True
 report['storage']='AWS S3 with fixed versions' if live else 'file-backed SDK fixture'
 report['s3_versions']=len(fp())
 (e/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
finally:
 for kind,n in reversed(made):subprocess.run(['docker',kind,'rm','-f',n]if kind=='container'else ['docker',kind,'rm',n],capture_output=True)
