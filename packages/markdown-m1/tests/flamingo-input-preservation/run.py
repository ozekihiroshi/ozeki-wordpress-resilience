from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64
b=Path('/tmp/flamingo-input-preservation-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='fl-contract-'+str(int(time.time()))
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
 web,wp,url,client=setup('fixture');initial=fingerprint(wp)
 def flhash():return wp('eval',"$r=WP_PLUGIN_DIR.'/flamingo/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($r,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($r))]=hash_file('sha256',$f->getPathname());ksort($a);echo wp_json_encode($a);")
 fbefore=flhash();d('exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'observe.php'),web+':/var/www/html/wp-content/mu-plugins/fixture-observe.php');d('cp',str(b/'fixture.php'),web+':/var/www/html/wp-content/mu-plugins/fixture-input.php')
 payload={'title':'Input contract fixture','form':'[text* your-name]\n[email* your-email]\n[text your-subject]\n[textarea probe]\n[checkbox choices "alpha" "beta"]\n[submit "Send"]','additional_settings':'','locale':'en_US','mail':{'subject':'[your-subject]','sender':'Fixture <sender@example.invalid>','recipient':'operator@example.invalid','body':'[probe]','additional_headers':'','attachments':'','use_html':False,'exclude_blank':False},'context':'save'}
 fid=client.cf7(payload=payload)['id'];pid=client.rest('pages',{'title':'Form','content':'[contact-form-7 id="'+str(fid)+'"]','status':'publish'})['id']
 import re,html
 markup=client.request('/?page_id='+str(pid))[0].decode();fields=module._http.Fields(markup).values
 probe='path=C:\\docs\nnetwork=\\\\server\\share\njson={"path":"C:\\\\docs","quote":"\\"hello\\""}\nliteral=\\n\n日本語 "quote" apostrophe\' end'
 values={k:v for k,v in fields.items() if k.startswith('_wpcf7')};values.update({'your-name':'Tester','your-email':'tester@example.invalid','your-subject':'Contract check','probe':probe,'choices[]':'alpha'})
 wp('option','update','fixture_protect','1');boundary='----ContractFixtureOnly';body=b''
 for k,v in values.items():body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode()
 body+=('--'+boundary+'--\r\n').encode()
 anonymous=urllib.request.build_opener(urllib.request.ProxyHandler({}));request=urllib.request.Request(url+'/?rest_route=/contact-form-7/v1/contact-forms/'+str(fid)+'/feedback',body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
 response=json.loads(anonymous.open(request,timeout=30).read());results['feedback']=response;results['sent_fields']={'probe':probe,'choices':['alpha']}
 d('cp',str(b/'export.php'),web+':/tmp/export.php')
 def export():return json.loads(wp('eval-file','/tmp/export.php'))
 first=export();results['first']=first
 assert first['formal_inputs']==1,first
 r=first['inputs'][0];original=json.loads(r['input_json'])
 assert original['fields']['probe']==probe and r['state']=='confirmed'
 assert first['baseline'] and first['legacy']['held'] and not first['legacy']['receipts']
 # Repeat commit after acknowledgment loss, then a fresh PHP process retry.
 d('exec',web,'touch','/tmp/lose-response')
 response2=json.loads(anonymous.open(request,timeout=30).read());second=export()
 (wp('eval','(new OzekiResilience\\M1\\ReceiptInputs())->resume();'))
 retried=export();assert retried['formal_inputs']==2,retried
 assert all(x['state']=='confirmed' for x in retried['inputs'])
 wp('eval','(new OzekiResilience\\M1\\ReceiptInputs())->resume();')
 assert export()['formal_inputs']==2
 # A write outage keeps registration durable; retry does not repeat Flamingo add.
 d('exec',web,'touch','/tmp/deny-writes');response3=json.loads(anonymous.open(request,timeout=30).read())
 outage=export();assert any(x['state']=='registered' for x in outage['inputs']) and outage['formal_inputs']==2
 d('exec',web,'rm','/tmp/deny-writes');wp('eval','(new OzekiResilience\\M1\\ReceiptInputs())->resume();')
 final=export();assert final['formal_inputs']==3 and all(x['state']=='confirmed' for x in final['inputs'])
 d('cp',str(b/'OldSiteSnapshot.php'),web+':/tmp/product/src/OldSiteSnapshot.php');d('cp',str(b/'snapshot.php'),web+':/tmp/snapshot.php');results['snapshot']=json.loads(wp('eval-file','/tmp/snapshot.php'))
 # Set up a separate prepared target, register a new CF7 form normally.
 target,twp,turl,tclient=setup('target');d('exec',target,'mkdir','-p','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'fixture.php'),target+':/var/www/html/wp-content/mu-plugins/fixture-input.php')
 for i in range(5):tclient.rest('pages',{'title':'New target '+str(i),'status':'draft'})
 tfid=tclient.cf7(payload=payload)['id'];assert tfid!=fid
 (b/'input-plan.json').write_text(json.dumps(final['plan']));(b/'form-map.json').write_text(json.dumps({str(fid):tfid}))
 for fn in ['input-plan.json','form-map.json','rebuild.php']:d('cp',str(b/fn),target+':/tmp/'+fn)
 rebuilt=json.loads(twp('eval-file','/tmp/rebuild.php','--user=operator'));results['rebuilt']=rebuilt
 assert len(rebuilt['verified'])==3 and not rebuilt['failed'],rebuilt
 for newid in rebuilt['receipts'].values():
  view=tclient.request('/wp-admin/admin.php?page=flamingo_inbound&post='+str(newid)+'&action=edit')[0].decode()
  assert 'Contract check' in view and 'path=' in view
 again=json.loads(twp('eval-file','/tmp/rebuild.php','--user=operator'));assert again['receipts']==rebuilt['receipts'] and len(again['verified'])==3
 # A separate interrupted reconstruction attempt must not register on retry.
 before_count=twp('post','list','--post_type=flamingo_inbound','--format=count')
 d('cp',str(b/'rebuild-interrupt.php'),target+':/tmp/rebuild-interrupt.php');d('exec',target,'touch','/tmp/interrupt-registration')
 twp('eval-file','/tmp/rebuild-interrupt.php','--user=operator')
 d('exec',target,'rm','/tmp/interrupt-registration');uncertain=json.loads(twp('eval-file','/tmp/rebuild-interrupt.php','--user=operator'))
 assert uncertain['held'] and not uncertain['receipts'] and twp('post','list','--post_type=flamingo_inbound','--format=count')==before_count
 results['reconstruction_retry']={'same_ids':again['receipts']==rebuilt['receipts'],'uncertain_outcome_held':True}
 results['regression']={}
 for test in ['forms.php','comments.php']:
  results['regression'][test]=d('exec',target,'php','/tmp/product/tests/'+test,'/tmp/product')
 for fn in ['ReceiptInputs.php','FormHistory.php','CommentHistory.php','FlamingoReconstruction.php','SiteSnapshot.php']:
  d('exec',target,'php','-l','/tmp/product/src/'+fn)
 # Interrupted before registration: stage survives and is not inferred from DB.
 d('exec',web,'touch','/tmp/interrupt-registration')
 try:anonymous.open(request,timeout=30).read()
 except urllib.error.HTTPError:pass
 d('exec',web,'rm','/tmp/interrupt-registration');interrupted=export()
 assert interrupted['formal_inputs']==3 and any(x['state']=='staged' for x in interrupted['inputs'])
 assert interrupted['baseline_error']
 results['checks']={'raw_cf7_input_unchanged':True,'formal_after_success':True,'lost_ack_no_duplicate':True,'write_outage_retry':True,'unconfirmed_not_promoted':True,'legacy_output_held':True,'normal_add_result_equal':True,'admin_receipt_view':True,'baseline_contains_inputs':True,'plugins_unchanged':initial==fingerprint(wp) and fbefore==flhash()}
 results['final']=final;results['interrupted']=interrupted;results['s3_used']=False;results['all_checks_passed']=all(results['checks'].values())
 assert results['all_checks_passed']
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps({'checks':results.get('checks'),'error':results.get('error'),'feedback':results.get('feedback'),'elapsed_seconds':results['elapsed_seconds'],'cleanup_errors':errors},ensure_ascii=False,indent=2))
