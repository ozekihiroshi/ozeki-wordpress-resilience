from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64
b=Path('/tmp/markdown-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='md-registration-'+str(int(time.time()))
spec=importlib.util.spec_from_file_location('registration',b/'product/tools/reconstruct-markdown.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
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
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'markdown.zip'),web+':/tmp/markdown.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=Markdown normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/markdown.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')
 client=module.NormalMarkdownClient(url,'operator','isolated-only-123',True)
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/ozeki-markdown-documents/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()
try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 src,swp,surl,source=setup('source');source_fingerprint=fingerprint(swp)
 results['wordpress']=swp('core','version').strip();results['markdown']=swp('plugin','get','ozeki-markdown-documents','--field=version').strip()
 png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jp1sAAAAASUVORK5CYII=')
 image=json.loads(source.request('/?rest_route=/wp/v2/media',png,{'X-WP-Nonce':source.nonce,'Content-Type':'image/png','Content-Disposition':'attachment; filename="wiring.png"'})[0]);image_url=image['source_url']
 raw=('# INITIAL\r\n\r\n技術資料 **24 V**。 `C:\\docs\\wiring`\r\n\r\n![Wiring](<'+image_url+'> "Diagram")\r\n\r\n```md\r\n![Example]('+image_url+')\r\n```\r\n\r\n`![Example]('+image_url+')`\r\n\r\n```html\r\n<script>example</script>\r\n```\r\n').encode()
 baseitem={'title':'技術資料 "A" & B','slug':'technical-a','status':'publish','password':'','excerpt':'','date':'2026-11-20 10:11:12','date_gmt':'2026-11-20 10:11:12','author_destination':1,'comment_status':'closed','ping_status':'closed','menu_order':0}
 def add(raw,filename,**changes):
  item={**baseitem,**changes};i=source.import_document(raw,filename);source.save(i,raw,item);return i,item
 main,item=add(raw,'wiring-source.md')
 baseline_raw='# BASELINE-ONLY\r\n\r\n未編集の文書です。\r\n'.encode();baseline,baseline_item=add(baseline_raw,'baseline.markdown',title='Baseline document',slug='baseline-doc')
 withdrawn,withdrawn_item=add(b'# WILL-BE-WITHDRAWN\n','withdrawn.md',slug='withdrawn')
 draft=source.import_document(b'# DRAFT-NOT-FORMAL\n','draft.md')
 missing,missing_item=add(('# MISSING\n![Missing]('+surl+'/wp-content/uploads/missing.png)\n').encode(),'missing.md',slug='missing')
 private,private_item=add(b'# PRIVATE-DOCUMENT\n','private.md',slug='private-doc',status='private')
 content='<!-- wp:paragraph --><p>EMBED-PAGE</p><!-- /wp:paragraph --><!-- wp:shortcode -->[ozeki_markdown_document id="'+str(main)+'"]<!-- /wp:shortcode -->\n[ozeki_markdown_document id="'+str(baseline)+'"]'
 page=source.rest('pages',{'title':'Embedding page','content':content,'status':'publish'})['id'];withdrawn_page=source.rest('pages',{'title':'Withdrawn embedding','content':'[ozeki_markdown_document id="'+str(withdrawn)+'"]','status':'publish'})['id']
 results['baseline']=json.loads(swp('eval-file','/tmp/product/tests/markdown-reconstruction.php','capture'))
 latest=raw+'\r\n## FORMAL-TAIL\r\n正式な追記です。\r\n'.encode();source.save(main,latest,item);source.save(withdrawn,b'# WILL-BE-WITHDRAWN\n',{**withdrawn_item,'status':'draft'})
 added,added_item=add(b'# AFTER-BASELINE\n','after.md',slug='after-baseline')
 results['history']=json.loads(swp('eval-file','/tmp/product/tests/markdown-reconstruction.php','history',str(main),str(withdrawn),str(added)))
 before=swp('eval',"echo hash_file('sha256','/tmp/md-materials.bin');").strip()
 initial=json.loads(swp('eval-file','/tmp/product/tests/markdown-reconstruction.php','plan','0'));plan=json.loads(swp('eval-file','/tmp/product/tests/markdown-reconstruction.php','plan','3'))
 assert base64.b64decode(next(x for x in initial['documents'] if x['origin_id']==main)['source_base64'])==raw
 assert base64.b64decode(next(x for x in plan['documents'] if x['origin_id']==main)['source_base64'])==latest
 target,twp,turl,client=setup('target');target_fingerprint=fingerprint(twp)
 twp('eval',"for($i=0;$i<20;$i++)wp_insert_post(['post_title'=>'Prepared '.$i,'post_status'=>'draft']);update_option('prepared_setting','keep');")
 report=client.rebuild(plan,b/('journal-'+name+'.json'),{'1':1});mapping=report['documents'];assert str(main) in mapping and str(baseline) in mapping
 results['report']=report
 new=mapping[str(main)];new_base=mapping[str(baseline)];new_image=report['image_urls'][image_url]
 expected=latest.replace(image_url.encode(),new_image.encode(),1)
 exported,headers=client.export(new)
 checks={'baseline_and_formal_selection':True,'tail_bytes':exported==expected,'baseline_bytes':client.export(new_base)[0]==baseline_raw,'filename':'wiring-source.md' in urllib.parse.unquote(headers.get('Content-Disposition','')),'new_ids':all(int(k)!=v for k,v in mapping.items()),'withdrawn_excluded':str(withdrawn) not in mapping,'draft_excluded':str(draft) not in mapping,'missing_image_held':str(missing) in report['held'],'new_document_filename_missing_reported':str(added) in report['held'],'withdrawn_embed_held':str(withdrawn_page) in report['held']}
 anon=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def view(url):
  try:return anon.open(url,timeout=30).read().decode()
  except urllib.error.HTTPError as e:
   if e.code in (403,404):return ''
   raise
 direct=turl+'/?post_type=ozmd_document&p='+str(new);embedding=turl+'/?page_id='+str(report['pages'][str(page)])
 for _ in range(2):
  rendered=view(direct);embedded=view(embedding);assert 'FORMAL-TAIL' in rendered and 'FORMAL-TAIL' in embedded and 'BASELINE-ONLY' in embedded and new_image in rendered and '<script>example</script>' not in rendered
 checks['direct_and_embed_views']=True;checks['image_bytes']=anon.open(new_image).read()==png;checks['private_not_public']='PRIVATE-DOCUMENT' not in view(turl+'/?post_type=ozmd_document&p='+str(mapping[str(private)]))
 edited=expected+'\r\n## TARGET-EDIT\r\n通常編集と再保存。\r\n'.encode();client.save(new,edited,item);client.save(new,client.export(new)[0],item)
 checks['normal_edit_resave']=client.export(new)[0]==edited and 'TARGET-EDIT' in view(direct) and 'TARGET-EDIT' in view(embedding)
 core=json.loads(twp('eval',"$p=get_post("+str(new)+");echo json_encode(['title'=>$p->post_title,'date'=>$p->post_date,'status'=>$p->post_status,'author'=>$p->post_author]);"))
 checks['normal_publication_fields']=core['title']==item['title'] and core['date']==item['date'] and core['status']=='publish' and core['author']=='1'
 checks['source_original_unchanged']=source.export(main)[0]==latest and before==swp('eval',"echo hash_file('sha256','/tmp/md-materials.bin');").strip() and plan['input_unchanged']
 checks['plugin_files_unchanged']=source_fingerprint==fingerprint(swp) and target_fingerprint==fingerprint(twp)
 checks['prepared_setting_preserved']=twp('option','get','prepared_setting').strip()=='keep'
 results['checks']=checks;results['publication_readback']=core;results['all_checks_passed']=all(checks.values());results['s3_used']=False
 assert results['all_checks_passed'],json.dumps(checks)
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:2000]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
