from pathlib import Path
import subprocess,json,time,argparse
p=argparse.ArgumentParser();p.add_argument('--reuse',action='store_true');p.add_argument('--keep',action='store_true');a=p.parse_args()
b=Path('/tmp/construction-follow-v2-20261128');core=Path('/tmp/owr-community-rc23-roundtrip-20261128');started=time.monotonic()
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];name='construction-follow-v2';label='ozeki.isolation=construction-follow-v2';result={};owned=False
def run(*args,raw=None):
 r=subprocess.run(D+list(args),input=raw,capture_output=True,timeout=120)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2000:])
 return r.stdout
def wp(site,*args):return run('exec',name+'-'+site,'php','/tmp/wp.phar','--allow-root',*args).decode()
try:
 if not a.reuse:
  run('network','create','--internal','--label',label,name)
  owned=True
  run('run','-d','--name',name+'-db','--network',name,'--label',label,'--memory','384m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11')
  for _ in range(60):
   try:run('exec',name+'-db','healthcheck.sh','--connect','--innodb_initialized');break
   except RuntimeError:time.sleep(1)
  for site in ['source','target']:
   web=name+'-'+site;run('volume','create','--label',label,web)
   run('run','-d','--name',web,'--network',name,'--label',label,'--memory','384m','-v',web+':/var/www/html','-e','WORDPRESS_DB_HOST='+name+'-db','-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+site+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache')
   for _ in range(60):
    try:run('exec',web,'test','-f','/var/www/html/wp-config.php');break
    except RuntimeError:time.sleep(1)
   run('cp',str(core/'core/wordpress')+'/.',web+':/var/www/html/');run('cp',str(core/'wp.phar'),web+':/tmp/wp.phar')
   login='source-operator' if site=='source' else 'destination-admin'
   wp(site,'core','install','--url=http://'+web+'.invalid','--title=Follow fixture','--admin_user='+login,'--admin_password=isolated-only-123','--admin_email='+login+'@example.invalid','--skip-email')
  b.joinpath('seed.sql').write_bytes(run('exec',name+'-db','mariadb-dump','-uroot','-pfixture','--add-drop-table','fixture'));b.joinpath('seed.sql').chmod(0o600)
 else:
  for site in ['source','target','db']:
   info=json.loads(run('inspect',name+'-'+site))[0]
   if info['Config']['Labels'].get('ozeki.isolation')!='construction-follow-v2':raise RuntimeError('Not the dedicated fixture')
  owned=True
  run('exec','-i',name+'-db','mariadb','-uroot','-pfixture','fixture',raw=b.joinpath('seed.sql').read_bytes())
 result['environment_seconds']=round(time.monotonic()-started,3)
 for site in ['source','target']:
  web=name+'-'+site;run('exec',web,'mkdir','-p','/tmp/product');run('cp',str(b/'product')+'/.',web+':/tmp/product/');run('cp',str(b/'wordpress.php'),web+':/tmp/wordpress.php')
  run('exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins');run('cp',str(b/'automatic-fixture.php'),web+':/var/www/html/wp-content/mu-plugins/capture.php')
 t=time.monotonic();result['fast_contract']=run('exec',name+'-source','php','/tmp/product/tests/construction-follow.php').decode()
 result['contract_process_seconds']=round(time.monotonic()-t,3)
 result['source']=json.loads(wp('source','eval-file','/tmp/wordpress.php','source'))
 run('cp',name+'-source:/tmp/follow-kit.json',str(b/'kit.json'));run('cp',str(b/'kit.json'),name+'-target:/tmp/follow-kit.json')
 result['target']=json.loads(wp('target','eval-file','/tmp/wordpress.php','target'))
 result['passed']=True
except Exception as e:result['error']=str(e);result['passed']=False
finally:
 result['kept']=a.keep and result.get('passed',False);result['cleanup_errors']=[]
 if owned and not result['kept']:
  for site in ['source','target','db']:
   try:run('rm','-f',name+'-'+site)
   except Exception as e:result['cleanup_errors'].append(str(e))
  for site in ['source','target']:
   try:run('volume','rm',name+'-'+site)
   except Exception as e:result['cleanup_errors'].append(str(e))
  try:run('network','rm',name)
  except Exception as e:result['cleanup_errors'].append(str(e))
 result['total_seconds']=round(time.monotonic()-started,3);b.joinpath('result-reuse.json' if a.reuse else 'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
