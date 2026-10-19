# Explain intent before any imports that may access local trust or remote hosts.
if __name__ == '__main__':
 import argparse, sys
 parser = argparse.ArgumentParser(description='Site-specific 2026-10-18 pilot; not a scheduler or general installer. See tools/README.md.')
 parser.add_argument('--execute-pilot', action='store_true', help='Explicitly run the reviewed, site-specific pilot (cloud/signing/Docker effects possible).')
 args = parser.parse_args()
 if not args.execute_pilot:
  parser.error('Execution disabled by default. Read tools/README.md before using --execute-pilot.')
 if sys.flags.optimize:
  parser.error('Optimized Python disables pilot checks; use normal Python without -O/-OO.')
import os,json,gzip,tarfile,io,hashlib,secrets,subprocess,time,re,datetime,shutil
from pathlib import Path
os.umask(0o077)
source=Path.home()/'.local/share/owr-production/RS-WP-CERI-20261018-001/restore-download-001'
import importlib.util
trust=Path.home()/'.local/share/owr-trust/wp-ceri-link/RS-WP-CERI-20261018-001'
spec=importlib.util.spec_from_file_location('candidate_gate',Path('/mnt/d/workspace/ozeki-wordpress-resilience/tools/verify-protected-candidate.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
verified=gate.verify(trust,source/'candidate-approval.json',source/'candidate-approval.sig',source/'candidate-anchor.json',source,'wp-ceri-link','RS-WP-CERI-20261018-001')
# Mandatory gate before output creation or Docker operations.
assert json.loads((source/'fresh-fetch-result.json').read_text())['passed']
root=Path.home()/'.local/share/owr-quarantine/wp-ceri-link-s3-20261018-001';root.mkdir(parents=True,exist_ok=False,mode=0o700)
vdir=root/'verify';vdir.mkdir(mode=0o755)
report={'kind':'signed_s3_candidate_quarantine_restore','signature_gate':verified,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':False,'source_access':'none','source_consistency':'live capture; cross-asset point-in-time consistency unverified','public_ports':False}
web='owr-s3-q-20261018-web';db='owr-s3-q-20261018-db';wv='owr-s3-q-20261018-site';dv='owr-s3-q-20261018-db';created=[]
def save():(root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,**kw):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
 if p.returncode:raise RuntimeError('Command failed: '+args[0]+' '+str(args[1:3]))
 return p.stdout
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def writes(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
receipt=json.loads((source/'capture.json').read_text());assert receipt['passed']
report['fresh_s3_fetch']=json.loads((source/'fresh-fetch-result.json').read_text())
save()
# Build file inventory without executing any captured code.
expected={}
with tarfile.open(source/'wordpress-files.tar.gz') as t:
 for m in t:
  assert not(m.issym() or m.islnk() or m.isdev()) and not m.name.startswith('/') and '..' not in Path(m.name).parts
  if m.isfile():expected[m.name.removeprefix('./')]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
writes(vdir/'files.json',expected);(vdir/'files.json').chmod(0o644)
# SQL row counts: scan extended INSERT statements, respecting strings and escapes.
sql=gzip.decompress((source/'database.sql.gz').read_bytes()).decode()
counts={name:0 for name in re.findall(r'CREATE TABLE `([^`]+)`',sql)}
for match in re.finditer(r'^INSERT INTO `([^`]+)` VALUES\s*',sql,re.M):
 table=match.group(1);i=match.end();depth=0;quoted=False
 while i<len(sql):
  c=sql[i]
  if quoted:
   if c=='\\':i+=2;continue
   if c=="'":
    if i+1<len(sql) and sql[i+1]=="'":i+=2;continue
    quoted=False
  else:
   if c=="'":quoted=True
   elif c=='(':
    if depth==0:counts[table]+=1
    depth+=1
   elif c==')':depth-=1
   elif c==';' and depth==0:break
  i+=1
assert len(counts)==12
wpimg,dbimg=receipt['runtime_image_ids'];password=secrets.token_hex(24);rootpassword=secrets.token_hex(24)
(root/'db.env').write_text('MARIADB_DATABASE=owr_quarantine\nMARIADB_USER=owr_quarantine\nMARIADB_PASSWORD='+password+'\nMARIADB_ROOT_PASSWORD='+rootpassword+'\n')
(root/'web.env').write_text('WORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=owr_quarantine\nWORDPRESS_DB_USER=owr_quarantine\nWORDPRESS_DB_PASSWORD='+password+'\n')
config="<?php\ndefine('DB_NAME',getenv('WORDPRESS_DB_NAME'));\ndefine('DB_USER',getenv('WORDPRESS_DB_USER'));\ndefine('DB_PASSWORD',getenv('WORDPRESS_DB_PASSWORD'));\ndefine('DB_HOST',getenv('WORDPRESS_DB_HOST'));\ndefine('DB_CHARSET','utf8mb4');\ndefine('DB_COLLATE','');\n$table_prefix='wp_';\n"
for key in ['AUTH_KEY','SECURE_AUTH_KEY','LOGGED_IN_KEY','NONCE_KEY','AUTH_SALT','SECURE_AUTH_SALT','LOGGED_IN_SALT','NONCE_SALT']:config+="define('"+key+"','"+secrets.token_hex(48)+"');\n"
for key in ['DISABLE_WP_CRON','WP_HTTP_BLOCK_EXTERNAL','AUTOMATIC_UPDATER_DISABLED','DISALLOW_FILE_MODS','DISALLOW_FILE_EDIT']:config+="define('"+key+"',true);\n"
config+="define('WP_HOME','http://127.0.0.1');define('WP_SITEURL','http://127.0.0.1');define('WP_ENVIRONMENT_TYPE','local');define('WP_DEBUG',false);define('ABSPATH',__DIR__.'/');require_once ABSPATH.'wp-settings.php';\n"
mu="<?php\nif(!function_exists('wp_mail')){function wp_mail($to,$subject,$message,$headers='',$attachments=[]){return false;}}\nadd_filter('pre_http_request',function(){return new WP_Error('owr_offline','Quarantine network disabled');},PHP_INT_MAX,3);\nadd_filter('pre_wp_mail','__return_false',PHP_INT_MAX);\n"
(vdir/'offline.ini').write_text('sendmail_path=/bin/false\nallow_url_fopen=Off\ndisplay_errors=Off\n');(vdir/'offline.ini').chmod(0o644)
verifyfiles="<?php $expected=json_decode(file_get_contents('/verify/files.json'),true);$bad=[];foreach($expected as $p=>$h){if(!is_file('/site/'.$p)||hash_file('sha256','/site/'.$p)!==$h){$bad[]=$p;}}echo json_encode(['passed'=>count($bad)===0,'files'=>count($expected),'mismatches'=>count($bad)]);exit(count($bad)?1:0);"
(vdir/'files.php').write_text(verifyfiles);(vdir/'files.php').chmod(0o644)
healthphp="<?php require '/var/www/html/wp-load.php'; global $wpdb; echo json_encode(['wordpress_version'=>$wp_version,'site_name'=>get_bloginfo('name'),'home'=>home_url('/'),'posts_published'=>(int)$wpdb->get_var(\"SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_status='publish' AND post_type='post'\"),'pages_published'=>(int)$wpdb->get_var(\"SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_status='publish' AND post_type='page'\"),'attachments'=>(int)$wpdb->get_var(\"SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='attachment'\"),'active_plugins'=>get_option('active_plugins'),'theme'=>get_option('stylesheet'),'cron_disabled'=>DISABLE_WP_CRON,'http_blocked'=>is_wp_error(wp_remote_get('https://example.com')),'mail_blocked'=>wp_mail('nobody@example.invalid','OWR offline test','No delivery')===false]);"
(vdir/'health.php').write_text(healthphp);(vdir/'health.php').chmod(0o644)
base=['--security-opt','no-new-privileges:true','--pids-limit','128','--cpus','1']
try:
 for n in [web,db]:
  p=subprocess.run(['docker','container','inspect',n],capture_output=True);assert p.returncode!=0,'Container already exists'
 for n in [wv,dv]:
  p=subprocess.run(['docker','volume','inspect',n],capture_output=True);assert p.returncode!=0,'Volume already exists'
 with (source/'runtime-images.tar.gz').open('rb') as f:run(['docker','load'],stdin=f)
 for n in [wv,dv]:run(['docker','volume','create',n])
 with gzip.open(source/'wordpress-files.tar.gz','rb') as f:
  p=subprocess.Popen(['docker','run','--rm','-i','--network','none',*base,'--memory','512m','-v',wv+':/site','--entrypoint','sh',wpimg,'-c','tar -xf - -C /site && chown -R www-data:www-data /site'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  shutil.copyfileobj(f,p.stdin);p.stdin.close();assert p.wait()==0
 report['file_inventory']=json.loads(run(['docker','run','--rm','--network','none',*base,'--memory','512m','-v',wv+':/site:ro','-v',str(vdir)+':/verify:ro','--entrypoint','php',wpimg,'/verify/files.php']));save()
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w') as t:
  for name,data in [('wp-config.php',config),('wp-content/mu-plugins/000-owr-offline.php',mu)]:
   raw=data.encode();m=tarfile.TarInfo(name);m.size=len(raw);m.mode=0o640;m.uid=33;m.gid=33;t.addfile(m,io.BytesIO(raw))
 run(['docker','run','--rm','-i','--network','none',*base,'--memory','256m','-v',wv+':/site','--entrypoint','tar',wpimg,'-xf','-','-C','/site'],input=buf.getvalue())
 run(['docker','run','-d','--name',db,'--network','none',*base,'--memory','512m','--env-file',str(root/'db.env'),'-v',dv+':/var/lib/mysql',dbimg]);created.append(db)
 for _ in range(60):
  p=subprocess.run(['docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True)
  if p.returncode==0:break
  time.sleep(2)
 else:raise RuntimeError('DB health timeout')
 dbcmd=['docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --user="$MARIADB_USER" --database=owr_quarantine --batch --skip-column-names']
 # No root SQL import; only new quarantine database credentials.
 run(dbcmd,input=sql.encode())
 query=';'.join('SELECT '+"'"+name+"',COUNT(*) FROM `"+name+'`' for name in counts)+';'
 actual={parts[0]:int(parts[1]) for line in run(dbcmd,input=query.encode()).decode().splitlines() if (parts:=line.split('\t'))}
 assert actual==counts,'Imported row counts differ';report['database']={'tables':len(counts),'rows':sum(counts.values()),'counts_matched':True};writes(root/'table-counts.json',counts);save()
 run(['docker','run','-d','--name',web,'--network','container:'+db,*base,'--memory','768m','--env-file',str(root/'web.env'),'-v',wv+':/var/www/html','-v',str(vdir)+':/verify:ro','-v',str(vdir/'offline.ini')+':/usr/local/etc/php/conf.d/zz-owr-offline.ini:ro',wpimg]);created.append(web)
 for _ in range(40):
  p=subprocess.run(['docker','exec',web,'php','-r',"$s=@fsockopen('127.0.0.1',80);exit($s?0:1);"],capture_output=True)
  if p.returncode==0:break
  time.sleep(1)
 else:raise RuntimeError('Web listener timeout')
 # Verify actual interfaces and representative external routes, not just compose declarations.
 networkphp="$r=['interfaces'=>array_values(array_diff(scandir('/sys/class/net'),['.','..'])),'blocked'=>[]];foreach(['1.1.1.1','169.254.169.254','172.17.0.1'] as $ip){$s=@fsockopen($ip,80,$e,$m,1);$r['blocked'][$ip]=!$s;if($s)fclose($s);}echo json_encode($r);"
 net=json.loads(run(['docker','exec',web,'php','-r',networkphp]));assert net['interfaces']==['lo'] and all(net['blocked'].values());report['network']=net
 health=json.loads(run(['docker','exec',web,'php','/verify/health.php']));assert health['cron_disabled'] and health['http_blocked'] and health['mail_blocked'];writes(root/'wordpress-health.json',health)
 report['wordpress']={k:v for k,v in health.items() if k not in ['site_name','active_plugins','theme']}
 http="<?php $c=curl_init('http://127.0.0.1/');curl_setopt($c,CURLOPT_RETURNTRANSFER,true);$b=curl_exec($c);echo json_encode(['status'=>curl_getinfo($c,CURLINFO_HTTP_CODE),'bytes'=>strlen($b),'title_present'=>stripos($b,'<title')!==false]);"
 p=json.loads(run(['docker','exec','-i',web,'php'],input=http.encode()));assert p['status']==200 and p['title_present'];report['homepage']=p
 contentphp=r'''<?php
require '/var/www/html/wp-load.php';global $wpdb;
$items=$wpdb->get_results("SELECT ID,post_type FROM {$wpdb->posts} WHERE post_status='publish' AND post_type IN ('post','page')");
$out=['pages'=>[],'media'=>[]];
function fetchlocal($path){$c=curl_init('http://127.0.0.1'.$path);curl_setopt_array($c,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>20,CURLOPT_FOLLOWLOCATION=>false]);$b=curl_exec($c);return ['status'=>curl_getinfo($c,CURLINFO_HTTP_CODE),'bytes'=>strlen($b),'hash'=>hash('sha256',$b),'title'=>stripos($b,'<title')!==false];}
foreach($items as $i){$v=fetchlocal((parse_url(get_permalink($i->ID),PHP_URL_PATH)?:'/'));$out['pages'][]=$v;}
$files=json_decode(file_get_contents('/verify/files.json'),true);
foreach($files as $p=>$h){if(str_starts_with($p,'wp-content/uploads/')&&preg_match('/\.(png|jpg|jpeg|webp|gif|pdf)$/i',$p)){$v=fetchlocal('/'.implode('/',array_map('rawurlencode',explode('/',$p))));$out['media'][]=['status'=>$v['status'],'hash_matched'=>$v['hash']===$h];}}
echo json_encode($out);
'''
 content=json.loads(run(['docker','exec','-i',web,'php'],input=contentphp.encode()))
 writes(root/'content-checks.json',content)
 report['content_checks']={'published_pages_tested':len(content['pages']),'pages_ok':sum(x['status']==200 and x['title'] for x in content['pages']),'media_tested':len(content['media']),'media_ok':sum(x['status']==200 and x['hash_matched'] for x in content['media'])}
 c=report['content_checks'];assert c['published_pages_tested']==c['pages_ok']==2 and c['media_tested']==c['media_ok']==23
 report['passed']=True
finally:
 report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 if created:
  p=subprocess.run(['docker','stop',*reversed(created)],capture_output=True);report['test_containers_stopped']=p.returncode==0
 save();print(json.dumps(report))
