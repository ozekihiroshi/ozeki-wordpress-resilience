import datetime,gzip,hashlib,importlib.util,json,os,shutil,subprocess,tarfile
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--allow-synthetic-s3',action='store_true')
parser.add_argument('--work',required=True)
parser.add_argument('--project-prefix',default='owr-core-e3')
parser.add_argument('--subnet-base',type=int,default=112)
parser.add_argument('--set-id',required=True)
parser.add_argument('--source-run',default='.local/e3-run-2')
parser.add_argument('--source-network',default='owr-m1-e3-2_recovery')
parser.add_argument('--baseline-bundle',default='.local/independent-download')
a=parser.parse_args()
parser.error('Unsigned derived recovery is retired. Publish and independently approve the derived set, then use tools/run-independent-recovery.py.')
if not a.allow_synthetic_s3:parser.error('Explicit synthetic S3 test flag required')
R=Path(__file__).resolve().parents[1];W=(R/a.work).resolve()
if not W.is_relative_to(R/'.local'):parser.error('Work must be inside .local')
source=(R/a.source_run).resolve();baseline=(R/a.baseline_bundle).resolve()
if not source.is_relative_to(R/'.local') or not baseline.is_relative_to(R/'.local'):parser.error('Local fixture paths required')
composition=json.loads((source/'compose.json').read_text())
if composition['services']['source']['environment'].get('OWR_FIXTURE')!='1':parser.error('Synthetic fixture required')
W.mkdir(exist_ok=False)
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
report={'kind':'shared_core_recovery','started_at':now(),'core_version':'0.1.0','wordpress_loaded_by_collector':False,'status':'running'}
(W/'progress.json').write_text(json.dumps(report))
config=json.loads((R/'.local/live-target.json').read_text());config['set_id']=a.set_id
(W/'live-target.json').write_text(json.dumps(config));os.chmod(W/'live-target.json',0o600)
secret=dict(l.split('=',1) for l in (source/'runtime.env').read_text().splitlines() if '=' in l)
env=os.environ.copy();env['OWR_DB_PASSWORD']=secret['RECOVERY_DB_PASSWORD']
images=json.loads((baseline/'bootstrap/images.json').read_text())
args=['docker','run','--rm','--pull=never','--network',a.source_network,'-v',str(R)+':/work:ro','--entrypoint','php','-e','OWR_DB_HOST=db','-e','OWR_DB_NAME=owr_recovery','-e','OWR_DB_USER=owr_recovery','-e','OWR_DB_PASSWORD',images['wordpress'],'/work/tools/dump-database.php']
with (W/'database-core.sql.gz').open('xb') as raw:
 with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as compressed:
  proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
  shutil.copyfileobj(proc.stdout,compressed)
  error=proc.stderr.read();assert proc.wait()==0,'Standalone dump failed'
report['captured_at']=now()
# Transfer only new DB, other immutable M1 assets remain from independent S3 download.
with tarfile.open(W/'transport-code.tar.gz','w:gz') as t:
 for name in ['src','tools/versioned-s3-transfer.php','tools/temporary-role-auth.php','tools/aws-autoload.php','tools/live-target.php']:
  t.add(R/name,arcname=name)
 t.add(R/'vendor',arcname='vendor')
os.environ['OWR_LIVE_CONFIG']=str(W/'live-target.json');os.environ['OWR_BUNDLE_DIR']=str(W)
spec=importlib.util.spec_from_file_location('storage',R/'tools/m1-live-storage.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
s.setup();receipt=s.upload(W/'database-core.sql.gz','database-core.sql.gz');observed=s.download_dm(receipt,'database-core.sql.gz')
(W/'external-observation.json').write_text(json.dumps(observed,indent=2))
# Stop synthetic source before creating the recovery input directory.
cli=['docker','compose','--env-file',str(source/'runtime.env'),'-f',str(source/'compose.json')]
report['source_stop_at']=now();subprocess.run(cli+['stop'],check=True)
try:
 bundle=W/'bundle';shutil.copytree(baseline,bundle)
 for obsolete in ('anchor.json','bootstrap.tar.gz'):
  (bundle/obsolete).unlink(missing_ok=True)
 s.run(['scp','-q',s.READER+':'+s.DM+'/database-core.sql.gz',str(bundle/'database.bin')])
 assert s.hash_file(bundle/'database.bin')==receipt['sha256']
 ram=json.loads((bundle/'ram.json').read_text());ram['set_id']=config['set_id'];ram['created_at']=now()
 for a in ram['assets']:
  if a['role']=='database':a.update(locator={**receipt['locator'],'credential_ref':'shared-role-test'},sha256=receipt['sha256'],size_bytes=receipt['size_bytes'])
 (bundle/'ram.json').write_text(json.dumps(ram,indent=2)+'\n')
 record=json.loads((bundle/'recovery-set.json').read_text());record['set_id']=ram['set_id'];record['ram_sha256']=s.hash_file(bundle/'ram.json')
 (bundle/'recovery-set.json').write_text(json.dumps(record,indent=2)+'\n')
 # Local derived test metadata is not a newly published full S3 recovery set.
 report['metadata_scope']='locally composed derived test set; new DB uploaded and retrieved by fixed Version ID; other assets from previous independent S3 fetch; no full-set publication claim'
 shutil.copy2(R/'tools/run-independent-recovery.py',bundle/'bootstrap/run-independent-recovery.py')
 report['restore_started_at']=now()
 result=subprocess.run(['python3',str(bundle/'bootstrap/run-independent-recovery.py'),'--bundle',str(bundle),'--output',str(W/'restore'),'--run','1','--project-prefix',a.project_prefix,'--subnet-base',str(a.subnet_base)])
 report['restore_exit']=result.returncode;report['finished_at']=now();report['status']='passed' if result.returncode==0 else 'failed'
 report['restore_result']=json.loads((W/'restore/result.json').read_text())
 (W/'result.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
 restored=W/'restore'
 if (restored/'compose.json').exists():
  subprocess.run(['docker','compose','--env-file',str(restored/'runtime.env'),'-f',str(restored/'compose.json'),'stop'],check=False)
 subprocess.run(cli+['up','-d','--wait'],check=True)
print(json.dumps(report,indent=2));raise SystemExit(result.returncode)
