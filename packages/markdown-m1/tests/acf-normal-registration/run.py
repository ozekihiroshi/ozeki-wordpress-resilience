from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64,re
b=Path('/tmp/acf-normal-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='acf-normal-'+str(int(time.time()))
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
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'acf.zip'),web+':/tmp/acf.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=ACF normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/acf.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')

 client=module.NormalMarkdownClient(url,'operator','isolated-only-123',True)
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/advanced-custom-fields/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()





import re,html,copy

def import_group(c,groups):
 url='/wp-admin/edit.php?post_type=acf-field-group&page=acf-tools&tool=import'
 markup=c.request(url)[0].decode();nonce=module.Fields(markup).values['_acf_nonce']
 boundary='----ACFNormalFixture';chunks=[]
 for k,v in {'_acf_nonce':nonce,'import_type':'json'}.items():chunks.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode())
 chunks.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="acf_import_file"; filename="material.json"\r\nContent-Type: application/json\r\n\r\n').encode()+json.dumps(groups,ensure_ascii=False).encode()+b'\r\n')
 body=b''.join(chunks)+('--'+boundary+'--\r\n').encode()
 markup=c.request(url,body,{'Content-Type':'multipart/form-data; boundary='+boundary})[0].decode()
 if not re.search(r'Imported (?:1 item|[0-9]+ items)',markup):
  notices=re.findall(r'<div[^>]*class="[^"]*(?:notice|error)[^"]*"[^>]*>(.*?)</div>',markup,re.S)
  raise RuntimeError('Normal import not confirmed: '+re.sub('<[^>]*>',' ',' '.join(notices))[:1200])
 return True

def save_values(c,pid,values):
 saved=c.rest('pages/'+str(pid)+'?context=edit');markup=c.request('/wp-admin/post.php?post='+str(pid)+'&action=edit')[0].decode();fields=module.Fields(markup).values
 assert fields.get('_acf_nonce'),'Normal ACF post nonce missing'
 p={'action':'editpost','post_ID':pid,'post_type':'page','_wpnonce':fields['_wpnonce'],'_acf_nonce':fields['_acf_nonce'],'_acf_screen':fields.get('_acf_screen','post'),'_acf_post_id':fields.get('_acf_post_id',str(pid)),'post_title':saved['title']['raw'],'content':saved['content']['raw'],'post_status':'publish','original_post_status':saved['status'],'user_ID':c.me['id']}
 pairs=list(p.items())
 for key,value in values.items():
  assert 'acf['+key+']' in markup,'Field missing from normal editor: '+key
  if isinstance(value,list):
   if not value:pairs.append(('acf['+key+']',''))
   else:pairs.extend(('acf['+key+'][]',v) for v in value)
  else:pairs.append(('acf['+key+']',value))
 c.request('/wp-admin/post.php',urllib.parse.urlencode(pairs).encode())
 return markup

def get_view(url,pid):
 raw=urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url+'/?page_id='+str(pid)).read().decode()
 match=re.search(r'<pre id="acf-material-view">(.*?)</pre>',raw,re.S);assert match,'Ordinary theme output missing'
 return json.loads(html.unescape(match[1]))

try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 source,swp,surl,sc=setup('source');target,twp,turl,tc=setup('target');sb=fingerprint(swp);tb=fingerprint(twp)
 for web,wp in [(source,swp),(target,twp)]:
  d('cp',str(b/'material.php'),web+':/tmp/material.php');d('exec',web,'mkdir','-p','/var/www/html/wp-content/themes/acf-normal-fixture')
  for f in ['style.css','functions.php','index.php']:d('cp',str(b/f),web+':/var/www/html/wp-content/themes/acf-normal-fixture/'+f)
  wp('theme','activate','acf-normal-fixture')
 types=['text','textarea','number','range','email','url','select','checkbox','radio','button_group','true_false','date_picker','date_time_picker','time_picker','color_picker']
 vals=[r'PLC C:\technical\one & two', '日本語の技術説明\nLine 2', '0','25','reader@example.invalid','https://example.invalid/guide?a=1&b=2','one',['one','two'],'two','one','1','20261128','2026-11-28 12:34:56','12:34:56','#123456']
 group={'key':'group_native_acf_trial','title':'Technical material fields','fields':[],'location':[[{'param':'post_type','operator':'==','value':'page'}]],'active':True,'show_in_rest':False,'description':'Technical notes','position':'normal','style':'default','label_placement':'top','instruction_placement':'label'}
 values={}
 for typ,val in zip(types,vals):
  f={'key':'field_trial_'+typ,'name':'trial_'+typ,'label':'Trial '+typ,'type':typ,'instructions':'入力説明 '+typ,'required':0}
  if typ in ('select','checkbox','radio','button_group'):f.update(choices={'one':'一つ目','two':'二つ目'},return_format='value',allow_null=1)
  if typ in ('number','range'):f.update(min=0,max=100,step=1)
  if typ=='textarea':f.update(rows=3,new_lines='')
  if typ=='date_picker':f.update(display_format='d/m/Y',return_format='Y-m-d')
  group['fields'].append(f);values[f['key']]=val
 group['fields'].append({'key':'field_trial_multi','name':'trial_multi','label':'Multi','type':'select','multiple':1,'choices':{'one':'一','two':'二'},'return_format':'value','allow_null':1,'conditional_logic':[[{'field':'field_trial_true_false','operator':'==','value':'1'}]]});values['field_trial_multi']=['two','one']
 import_group(sc,[group]);sid=sc.rest('pages',{'title':'Technical material','content':'Public technical explanation','status':'publish'})['id']
 save_values(sc,sid,values);baseline=json.loads(swp('eval-file','/tmp/material.php','capture',str(sid)))
 source_material=baseline['acf']['posts'][str(sid)]
 assert len(source_material['acf_references'])==len(values),'Source ordinary save omitted a field'
 for field_name,key in source_material['acf_references'].items():
  assert source_material['acf_values'][field_name]==[values[key]],'Source input/output differs: '+field_name
 values['field_trial_text']=r'Updated C:\technical\two & material';values['field_trial_textarea']='a:0:{}';save_values(sc,sid,values)
 selected=json.loads(swp('eval-file','/tmp/material.php','selected',str(sid)));results['material']={'baseline_unchanged':selected['baseline_unchanged'],'through':selected['through'],'groups':len(selected['acf']['acf_definitions']),'fields':len(selected['portable'][0]['fields'])}
 observed_source=json.loads(swp('eval-file','/tmp/material.php','read',str(sid)))
 assert selected['portable']==observed_source['portable'],'Stored definitions differ from ordinary portable definitions'
 for i in range(24):tc.rest('pages',{'title':'Prepared filler '+str(i),'content':'prepared','status':'draft'})
 did=tc.rest('pages',{'title':'Technical material','content':'Public technical explanation','status':'draft'})['id']
 import_group(tc,selected['portable'])
 material=selected['acf']['posts'][str(sid)];reinput={}
 for field_name,key in material['acf_references'].items():
  assert len(material['acf_values'][field_name])==1
  reinput[key]=material['acf_values'][field_name][0]
 editor=save_values(tc,did,reinput)
 actual=json.loads(twp('eval-file','/tmp/material.php','read',str(did)))
 results['first_comparison']={'definitions':actual['portable']==selected['portable'],'values':actual['capture']['acf_values']==material['acf_values'],'references':actual['capture']['acf_references']==material['acf_references']}
 if not all(results['first_comparison'].values()):
  results['value_differences']={k:{'saved':v,'registered':actual['capture']['acf_values'].get(k)} for k,v in material['acf_values'].items() if actual['capture']['acf_values'].get(k)!=v}
  raise RuntimeError('Ordinary import/save mismatch; no correction performed')
 assert sid!=did
 source_group=selected['acf']['acf_definitions'][0];target_group=actual['capture']['acf_definitions'][0]
 assert source_group['ID']!=target_group['ID']
 results['ids']={'page':[sid,did],'group':[source_group['ID'],target_group['ID']],'field_ids_differ':all(a['ID']!=z['ID'] for a,z in zip(source_group['fields'],target_group['fields']))}
 source_view=get_view(surl,sid);target_view=get_view(turl,did);assert source_view==target_view==actual['formatted']
 # Ordinary administrator re-save must not change values.
 save_values(tc,did,reinput);resaved=json.loads(twp('eval-file','/tmp/material.php','read',str(did)));assert resaved['capture']['acf_values']==material['acf_values']
 # Actual editing of a scalar and a multiple selection, using the same existing form.
 edited=copy.deepcopy(reinput);edited['field_trial_text']='EDITED technical note';edited['field_trial_checkbox']=['two'];edited['field_trial_multi']=[]
 save_values(tc,did,edited);edit_observed=json.loads(twp('eval-file','/tmp/material.php','read',str(did)));edit_view=get_view(turl,did)
 assert edit_observed['capture']['acf_values']['trial_text']==['EDITED technical note'] and edit_observed['capture']['acf_values']['trial_checkbox']==[['two']] and not edit_view['trial_multi']
 save_values(tc,did,edited);edit_resaved=json.loads(twp('eval-file','/tmp/material.php','read',str(did)));assert edit_resaved['capture']['acf_values']==edit_observed['capture']['acf_values']
 results['checks']={'portable_definition_equal':True,'values_and_references_equal':True,'frontend_display_equal':True,'editor_contains_all_fields':all('acf['+k+']' in editor for k in reinput),'instructions_present':all('入力説明 '+x in editor for x in types),'resave_unchanged':True,'edited_values_displayed':edit_view['trial_text']=='EDITED technical note' and edit_view['trial_checkbox']==['two'],'edited_resave_unchanged':True,'plugins_unchanged':sb==fingerprint(swp) and tb==fingerprint(twp),'material_unchanged':selected['baseline_unchanged']}
 results['all_checks_passed']=all(results['checks'].values());assert results['all_checks_passed'];results['s3_used']=False;results['acf_version']=twp('plugin','get','advanced-custom-fields','--field=version').strip();results['wp_version']=twp('core','version').strip();results['tested_types']=types;results['direct_database_writes']=False
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
