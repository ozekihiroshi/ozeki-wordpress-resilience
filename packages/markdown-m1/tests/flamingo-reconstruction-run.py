from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64
b=Path('/tmp/flamingo-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='fl-registration-'+str(int(time.time()))
spec=importlib.util.spec_from_file_location('registration',b/'product/tools/reconstruct-contact-form.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def d(*args):
 p=subprocess.run(D+list(args),capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError(p.stderr[:2000]+p.stdout[-1000:])
 return p.stdout
def setup(label):
 web=name+'-'+label;vol=web+'-vol';d('volume','create',vol);made.append(('volume',vol))
 d('run','-d','--name',web,'--network',net,'--memory','512m','-v',vol+':/var/www/html','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+label+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
 for _ in range(60):
  if subprocess.run(D+['exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
  time.sleep(1)
 d('exec',web,'sh','-c','echo memory_limit=256M > /usr/local/etc/php/conf.d/fixture-memory.ini')
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'contact-form-7.zip'),web+':/tmp/contact-form-7.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=CF7 normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/contact-form-7.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')
 d('cp',str(b/'flamingo.zip'),web+':/tmp/flamingo.zip');wp('plugin','install','/tmp/flamingo.zip','--activate')
 client=module.NormalContactFormClient(url,'operator','isolated-only-123',True)
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/contact-form-7/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()


try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 src,swp,surl,source=setup('source');sf=fingerprint(swp)
 def flamingohash(wp):return wp('eval',"$r=WP_PLUGIN_DIR.'/flamingo/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($r,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($r))]=hash_file('sha256',$f->getPathname());ksort($a);echo wp_json_encode($a);")
 sfl=flamingohash(swp);results['wordpress']=swp('core','version').strip();results['cf7']=swp('plugin','get','contact-form-7','--field=version').strip();results['flamingo']=swp('plugin','get','flamingo','--field=version').strip()
 form={'title':'Receipt channel','form':'[text equipment-code]\n[submit "Submit"]','additional_settings':'demo_mode: on','locale':'en_US'}
 oldform=source.cf7(payload={**form,'context':'save'})['id']
 seed=json.loads(swp('eval-file','/tmp/product/tests/flamingo-reconstruction.php','seed',str(oldform)));results['source_receipts']=seed
 results['baseline']=json.loads(swp('eval-file','/tmp/product/tests/flamingo-reconstruction.php','capture'))
 extra=json.loads(swp('eval-file','/tmp/product/tests/flamingo-reconstruction.php','seed',str(oldform)))
 extraid=extra['normal']['id'];results['history']=json.loads(swp('eval-file','/tmp/product/tests/flamingo-reconstruction.php','history','receipt:'+str(extraid)))
 before=swp('eval',"echo hash_file('sha256','/tmp/fl-materials.bin');").strip();plan=json.loads(swp('eval-file','/tmp/product/tests/flamingo-reconstruction.php','plan','1'))
 target,twp,turl,client=setup('target');tf=fingerprint(twp);tfl=flamingohash(twp)
 twp('eval',"for($i=0;$i<20;$i++)wp_insert_post(['post_title'=>'Prepared '.$i,'post_status'=>'draft']);update_option('prepared_setting','keep');")
 newform=client.cf7(payload={**form,'context':'save'})['id'];form_before=client.cf7(newform)
 # Include an unmapped receipt to ensure no guessed CF7 relation is written.
 missing=json.loads(json.dumps(plan['receipts'][0]));missing['origin_id']=999999;missing['form_origin_id']=999998;plan['receipts'].append(missing)
 (b/'plan.json').write_text(json.dumps(plan,ensure_ascii=False));(b/'map.json').write_text(json.dumps({str(oldform):newform}))
 d('cp',str(b/'plan.json'),target+':/tmp/plan.json');d('cp',str(b/'map.json'),target+':/tmp/map.json')
 report=json.loads(twp('--user=1','eval-file','/tmp/product/tools/reconstruct-flamingo.php','/tmp/plan.json','/tmp/map.json','/tmp/fl-registration-journal.json','isolated'));results['report']=report
 checks={'baseline_plus_history':len(plan['receipts'])==5 and any(x['origin_id']==extraid for x in plan['receipts']),'new_receipt_ids':all(int(k)!=v for k,v in report['receipts'].items()),'new_form_id':newform!=oldform,'ordinary_fields_verified':str(seed['normal']['id']) in report['verified'] and str(extraid) in report['verified'],'spam_verified':str(seed['spam']['id']) in report['verified'],'unmapped_held':'999999' in report['held']}
 import html,re
 visible=[]
 for old in report['verified']:
  new=report['receipts'][old];page=client.request('/wp-admin/admin.php?page=flamingo_inbound&action=edit&post='+str(new))[0].decode()
  text=' '.join(html.unescape(re.sub(r'<[^>]+>',' ',page)).split())
  visible.append(all(v in text for v in ['PLC-24','solar','monitor','一行目','二行目']))
 checks['admin_receipt_visible']=all(visible) and bool(visible)
 anon=urllib.request.build_opener(urllib.request.ProxyHandler({}));new=report['receipts'][str(seed['normal']['id'])]
 anonymous=anon.open(turl+'/wp-admin/admin.php?page=flamingo_inbound&action=edit&post='+str(new)).read().decode();checks['anonymous_no_receipt']='PLC-24' not in anonymous
 channel=report['channels'][str(oldform)]
 actual=int(twp('eval',"$f=wpcf7_contact_form("+str(newform)+");echo wpcf7_flamingo_add_channel($f->name(),$f->title());").strip())
 checks['normal_channel_reused']=actual==channel['term_id'];checks['no_private_cf7_pointer']=twp('eval',"echo metadata_exists('post',"+str(newform)+",'_flamingo')?'present':'absent';").strip()=='absent'
 checks['prepared_form_unchanged']=client.cf7(newform)==form_before;checks['prepared_setting_unchanged']=twp('option','get','prepared_setting').strip()=='keep';checks['original_unchanged']=before==swp('eval',"echo hash_file('sha256','/tmp/fl-materials.bin');").strip() and plan['input_unchanged'];checks['plugins_unchanged']=sf==fingerprint(swp) and tf==fingerprint(twp) and sfl==flamingohash(swp) and tfl==flamingohash(twp)
 # Record the exact output of normal add for the escaped-path example, without repairing it.
 slashold=str(seed['slashes']['id']);results['backslash_receipt']={'source_fields':seed['slashes']['fields'],'verified':slashold in report['verified'],'failure':report['failed'].get(slashold)}
 slashnew=report['receipts'][slashold]
 results['backslash_receipt']['destination_fields']=json.loads(twp('eval',"$x=new Flamingo_Inbound_Message("+str(slashnew)+");echo wp_json_encode($x->fields);"))
 checks['differences_reported_without_repair']=slashold in report['verified'] or slashold in report['failed']
 results['checks']=checks;results['all_checks_passed']=all(checks.values());results['all_receipts_rebuilt']=not report['failed'] and not report['held'];results['s3_used']=False;results['mail_sent']=False
 assert results['all_checks_passed'],json.dumps(checks)
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
