from pathlib import Path
import shutil
exec((Path(__file__).resolve().parent/'run.py').read_text().split('\ntry:\n lab=')[0])
r=json.loads((b/'resources.json').read_text());sites=r['sites'];lab=Path(r['lab'])
assert all(n.startswith('owr-coexist-') for n in sites.values())
for web in sites.values():
 d('cp',str(b/'fixture.php'),web+':/evidence/fixture.php')
 d('cp',str(b/'src')+'/.',web+':/var/www/html/wp-content/plugins/ozeki-resilience/src/')
extra={}
def check(side,case,status):
 v=cli(side,'state',case);url='http://localhost/wp-content/uploads/'+v['ids']['rel'];http=d('exec',sites[side],'curl','-s','-o','/dev/null','-w','%{http_code}',url)
 assert http==status,(side,case,http,status)
 assert not v['pending'] and not v['related_pending']
 if status=='404':assert v['held_hash'] and not v['file_exists']
 return dict(v,image_http=http)
cli('source','release','B')
cli('clean','reset-uploads','B');before=fp();cli('clean','restore','B');assert fp()==before
extra['release']=check('clean','B','200')
cli('source','guard','B')
cli('clean','reset-uploads','B');before=fp();cli('clean','restore','B');assert fp()==before
extra['guard_only']=check('clean','B','404')
# Genuine old WordPress capture + daily histories, copied into new trial prefixes.
old=Path('/tmp/owr-daily-boundary-20261114/lab-owr-coexist-1794635774')
def oldfp():return {str(p.relative_to(old/'objects')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (old/'objects').rglob('*')if p.is_file()}
oldbefore=oldfp()
def fresh(side,label):
 wp(side,'config','set','table_prefix',side+'_'+label+'_','--type=variable')
 wp(side,'core','install','--url=http://'+sites[side],'--title=Legacy recovery fixture','--admin_user=operator','--admin_password=trial-only-password','--admin_email=operator@example.invalid','--skip-email')
 wp(side,'plugin','activate','ozeki-resilience','wp-members')
 cli(side,'reset-uploads','B')
for case in ['B','C']:
 fresh('third','legacy'+case);fresh('clean','legacy'+case)
 prefix='legacy-'+case
 shutil.copytree(old/'objects'/('source-'+case),lab/'objects'/prefix)
 shutil.copy(old/('source-'+case+'-ref.json'),lab/(prefix+'-ref.json'))
 # IDs are original per fixture. Do not derive expected results from restored metadata.
 shutil.copy(old/('case-'+case+'.json'),lab/('case-'+case+'.json'))
 cli('third','reset-uploads',case);before=fp();out=cli('third','restore',case,'legacy');assert fp()==before
 v=check('third',case,'404');extra['legacy_'+case]=v
 assert v['held_hash']=='e9eacd49757cb10851c0bdeb92bec9c58f97e95592158bfdd5673d62969dc41f'
 cli('third','baseline',case,'legacy-next');cli('third','resave',case,'legacy-next')
 # Resave uses a separately created writer prefix in this dedicated trial.
 v=check('third',case,'404');assert 'RESAVED' in v['body'];extra['legacy_resave_'+case]=v
 cli('clean','reset-uploads',case);before=fp();cli('clean','restore',case,'legacy-next');assert fp()==before
 v=check('clean',case,'404');assert 'RESAVED' in v['body'];extra['legacy_second_'+case]=v
assert oldfp()==oldbefore
(b/'results/extended.json').write_text(json.dumps(extra,indent=2));print('PASS release, guard-only recheck, actual legacy capture/history recovery and resave; old objects unchanged')
