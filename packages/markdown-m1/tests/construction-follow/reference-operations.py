"""Normal source actions are only test setup; destination consumes the recorded journal."""
import importlib.util,json,urllib.parse,re,html,time,struct,zlib,hashlib

def execute(run,wp,name,b):
 def load(key):
  spec=importlib.util.spec_from_file_location('test_'+key,b/('product/tools/reconstruct-'+key+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 mods={k:load(k) for k in ['markdown','tablepress','contact-form','members','acf']}
 classes={'markdown':'NormalMarkdownClient','tablepress':'NormalTablePressClient','contact-form':'NormalContactFormClient','members':'NormalMemberClient','acf':'NormalAcfClient'}
 def clients(site):
  url=wp(site,'option','get','home').strip();user='source-operator' if site=='source' else 'destination-admin'
  return {k:getattr(m,classes[k])(url,user,'isolated-only-123',True) for k,m in mods.items()}
 source=clients('source');target=clients('target');start=time.monotonic()
 def chunk(kind,bytes):return struct.pack('>I',len(bytes))+kind+bytes+struct.pack('>I',zlib.crc32(kind+bytes)&0xffffffff)
 png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',800,600,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\x30\x80\xe0'*800)*600))+chunk(b'IEND',b'')
 def image(c):return json.loads(c.request('/?rest_route=/wp/v2/media',png,{'X-WP-Nonce':c.nonce,'Content-Type':'image/png','Content-Disposition':'attachment; filename="diagram.png"'})[0])
 prepared_image=image(target['markdown'])
 target['tablepress'].import_table({'name':'Prepared table','description':'Keep','data':[['Prepared']],'options':{'table_head':1,'use_datatables':False},'visibility':{'rows':[1],'columns':[1]}})
 def import_acf(c,groups):
  # Test the real import form. Normal ACF defaults are output, not missing input.
  url=c.tools+'&tool=import';nonce=mods['markdown'].Fields(c.request(url)[0].decode()).values['_acf_nonce'];boundary='----RecordedAcfOperation';raw=json.dumps(groups,ensure_ascii=False).encode()
  body=('--'+boundary+'\r\nContent-Disposition: form-data; name="_acf_nonce"\r\n\r\n'+nonce+'\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="import_type"\r\n\r\njson\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="acf_import_file"; filename="material.json"\r\nContent-Type: application/json\r\n\r\n').encode()+raw+('\r\n--'+boundary+'--\r\n').encode()
  response=c.request(url,body,{'Content-Type':'multipart/form-data; boundary='+boundary})[0].decode()
  assert re.search(r'Imported (?:1 item|[0-9]+ items)',response),'Normal ACF import not confirmed'
  return c.export([g['key'] for g in groups])
 # A real baseline author is registered by the product, never a supplied ID map.
 wp('source','eval',"$p=get_posts(['numberposts'=>1])[0];$k=OzekiResilience\\M1\\ConstructionOperations::initialSaveWithAuthors(fn()=>[['source_url'=>home_url()],['content.json'=>wp_json_encode(['tables'=>['posts'=>[(array)$p]]])]]);file_put_contents('/tmp/seed-kit.json',wp_json_encode($k));")
 run('cp',name+'-source:/tmp/seed-kit.json',str(b/'seed-kit.json'));run('cp',str(b/'seed-kit.json'),name+'-target:/tmp/seed-kit.json')
 authors=json.loads(wp('target','--user=destination-admin','eval',"$k=json_decode(file_get_contents('/tmp/seed-kit.json'),true);echo wp_json_encode(OzekiResilience\\M1\\ConstructionAuthors::register(['files'=>$k['files'],'anchor'=>$k['construction_anchor']]));"))
 identities={'user:'+str(k):v for k,v in authors.items()}
 image_result=image(source['markdown']);image_id=image_result['id'];image_url=image_result['source_url'];thumb=image_result['media_details']['sizes']['thumbnail']['source_url']
 external='https://images.example.invalid/diagram.png'
 # Interleave types and updates: no destination type-sorted recipe exists.
 login=source['markdown'].rest('pages',{'title':'Login','content':'[wpmem_form login]','status':'publish'})['id']
 profile=source['markdown'].rest('pages',{'title':'Profile','content':'[wpmem_profile]','status':'publish'})['id']
 m=source['members'];form=m.form(m.settingsurl,'updatesettings');p=form.values.copy();p.update(wpmem_settings_logpage=str(login),wpmem_settings_mspage=str(profile));m.submit(form,p)
 table={'name':'Readings','description':'Unchanged scalar 42','data':[['Device','Value'],['PLC',r'C:\manual\42']],'options':{'table_head':1,'table_foot':0,'use_datatables':False},'visibility':{'rows':[1,1],'columns':[1,1]}}
 tid=source['tablepress'].import_table(table)
 raw='# Technical explanation\n\n日本語\n![原本]('+image_url+')\n![縮小]('+thumb+')\n![外部]('+external+')'
 doc=source['markdown'].import_document(raw.encode(),'technical.md')
 raw=raw.replace('# Technical explanation','# Edited technical explanation')
 source['markdown'].save(doc,raw.encode(),{'title':'Explanation','slug':'explanation','status':'publish','password':'','date':'2026-11-28 12:00:00','author_destination':source['markdown'].me['id']})
 cf=source['contact-form'].cf7(payload={'title':'Inquiry','locale':'en_US','form':'[text your-name]\n[textarea probe]\n[submit "Send"]','additional_settings':'skip_mail: on','context':'save'})['id']
 forms=source['contact-form'].cf7();cfhash=next(x['hash'] for x in forms if x['id']==cf)
 relative=urllib.parse.urlsplit(image_url).path
 content=f'[table id="{tid}" /]\n[ozeki_markdown_document id="{doc}"]\n[contact-form-7 id="{cfhash}"]\n<img class="wp-image-{image_id}" src="{thumb}" alt="縮小"/><img src="{relative}"/><img src="{external}" alt="external"/>'
 page=source['markdown'].rest('pages',{'title':'Materials','content':content,'status':'draft'})['id']
 source['members'].restriction(page,'page','1')
 group={'key':'group_follow','title':'Description','fields':[{'key':'field_follow','name':'follow','label':'Description','type':'text','instructions':'説明'}],'location':[[{'param':'post_type','operator':'==','value':'page'}]],'active':True}
 source_groups=import_acf(source['acf'],[group]);source['acf'].save_values(page,'page',{'field_follow':'42 is text; not a post ID'})
 table['data'][1][1]='Edited 42';source['tablepress'].save_table(tid,table)
 source['markdown'].rest('pages/'+str(page),{'status':'publish'})
 # Source field definition and member creation are normal forms, not option writes.
 m.save_field({'0':17,'1':'Company','2':'company','3':'text','4':'y','5':'n','6':'n','profile':True,'placeholder':'','pattern':'','title':''})
 member=m.create_member({'user':{'user_login':'reader','user_email':'reader@example.invalid','display_name':'Reader','user_url':''},'meta':{'nickname':['reader'],'company':['42 Incorporated']}})
 m.save_field({'0':17,'1':'Company updated','2':'company','3':'text','4':'y','5':'n','6':'n','profile':True,'placeholder':'Company','pattern':'','title':''})
 source['contact-form'].cf7(cf,{'title':'Updated inquiry','context':'save'})
 controls=mods['markdown'].Fields(source['markdown'].request('/?page_id='+str(page))[0].decode()).values
 pairs={k:v for k,v in controls.items() if k.startswith('_wpcf7')};pairs.update({'your-name':'Synthetic reader','probe':r'C:\manual\42 日本語'})
 boundary='----RecordedReceipt';body=b''
 for k,v in pairs.items():body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode()
 body+=('--'+boundary+'--\r\n').encode()
 response=json.loads(source['markdown'].request('/?rest_route=/contact-form-7/v1/contact-forms/'+str(cf)+'/feedback',body,{'Content-Type':'multipart/form-data; boundary='+boundary})[0])
 assert response['status']=='mail_sent',response
 journal=json.loads(wp('source','eval','echo wp_json_encode(OzekiResilience\\M1\\ConstructionOperations::stable());'))
 b.joinpath('plugin-journal.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2))
 stages=[{'sequence':e['sequence'],'command':e['contract']['endpoint'],'coverage':e['contract']['coverage'],'reasons':e['contract']['reasons'],'outputs':e.get('outputs')} for e in journal['entries']]
 incomplete=[e for e in stages if e['coverage']!='complete' or (e['command'] not in ('members.settings','acf.import') and not e['outputs'])]
 if incomplete:return {'passed':False,'capture_gaps':incomplete,'stages':stages}
 def receipt(e,form):
  value={'operation':'receipt','entry':e,'source':journal['source'],'form':form,'journal':'/tmp/receipt-follow.json'}
  p=b/'receipt-follow.json';p.write_text(json.dumps(value));run('cp',str(p),name+'-target:/tmp/receipt-follow-input.json')
  r=json.loads(wp('target','--user=destination-admin','eval-file','/tmp/product/tools/construction-api.php','/tmp/receipt-follow-input.json'))
  assert r['state']=='completed' and not r['failed'] and not r['held'],r
  return next(iter(r['receipts'].values()))
 spec=importlib.util.spec_from_file_location('ordinary_dispatch',b/'product/tools/reconstruct-operations.py');dispatch=importlib.util.module_from_spec(spec);spec.loader.exec_module(dispatch)
 completed=[]
 for e in journal['entries']:
  value={'operation':'prepare-operation','entry':e,'through':e['sequence']-1,'identities':identities}
  path=b/'follow-request.json';path.write_text(json.dumps(value));run('cp',str(path),name+'-target:/tmp/follow-request.json')
  q=json.loads(wp('target','--user=destination-admin','eval-file','/tmp/product/tools/construction-api.php','/tmp/follow-request.json'))
  new=dispatch.dispatch(q,e,target,mods,receipt)
  value={'operation':'accept-operation','entry':e,'returned':new,'identities':identities}
  path.write_text(json.dumps(value));run('cp',str(path),name+'-target:/tmp/follow-request.json')
  identities=json.loads(wp('target','--user=destination-admin','eval-file','/tmp/product/tools/construction-api.php','/tmp/follow-request.json'))
  completed.append(e['sequence'])
 newpage=identities['post:'+str(page)];newtable=identities['table:'+str(tid)];newdoc=identities['post:'+str(doc)];newcf=identities['post:'+str(cf)];newmember=identities['user:'+str(member)]
 actual=target['markdown'].rest('pages/'+str(newpage)+'?context=edit')
 newurl=identities['image-url:full:'+str(image_id)];newthumb=identities['image-url:thumbnail:'+str(image_id)];newhash=identities['cf7-hash:'+str(cf)]
 assert newurl!=image_url and newthumb!=thumb and newhash!=cfhash
 assert actual['content']['raw']==f'[table id="{newtable}" /]\n[ozeki_markdown_document id="{newdoc}"]\n[contact-form-7 id="{newhash}"]\n<img class="wp-image-{identities["post:"+str(image_id)]}" src="{newthumb}" alt="縮小"/><img src="{newurl}"/><img src="{external}" alt="external"/>'
 target['tablepress'].verify(str(newtable),table)
 assert target['markdown'].export(newdoc)[0]==raw.replace(image_url,newurl).replace(thumb,newthumb).encode()
 assert target['markdown'].request(newurl)[0]==png
 assert target['markdown'].request(newthumb)[0]==source['markdown'].request(thumb)[0]
 assert target['markdown'].request(prepared_image['source_url'])[0]==png
 rendered=target['markdown'].request('/?page_id='+str(newpage))[0].decode()
 assert 'wpcf7-f'+str(newcf) in rendered and newthumb in rendered,'Normal rendered form/image not linked'
 settings=target['members'].form(target['members'].settingsurl,'updatesettings').values
 assert settings['wpmem_settings_logpage']==str(identities['post:'+str(login)])
 assert settings['wpmem_settings_mspage']==str(identities['post:'+str(profile)])
 editor=target['markdown'].request('/wp-admin/post.php?post='+str(newpage)+'&action=edit')[0].decode()
 assert target['acf'].export(['group_follow'])==source_groups,'Normal ACF definition results differ'
 assert '42 is text; not a post ID' in editor and mods['members'].block_control(editor)=='1'
 assert target['members'].form('/wp-admin/user-edit.php?user_id='+str(newmember),'your-profile').values['company']=='42 Incorporated'
 assert wp('target','option','get','fixture_submission_count').strip()=='0','Destination resent a form'
 # Ordinary later resave is another observed operation, not output correction.
 target['markdown'].rest('pages/'+str(newpage),{'title':'Ordinary resave'})
 assert target['markdown'].rest('pages/'+str(newpage)+'?context=edit')['content']['raw']==actual['content']['raw']
 return {'passed':True,'stages':stages,'completed':completed,'seconds':round(time.monotonic()-start,3),'image_original_and_thumbnail':True,'cf7_hash_embeds':True,'external_url_unchanged':True,'normal_rendering':True,'source_image_sha256':hashlib.sha256(png).hexdigest(),'typed_embeds':True,'settings_references':True,'structured_values_unchanged':True,'ordinary_resave':True,'identities_from_actual_results':identities}
