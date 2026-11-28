"""Normal source actions are only test setup; destination consumes the recorded journal."""
import importlib.util,json,urllib.parse,urllib.request,re,html,time,struct,zlib,hashlib

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
 # Capture a real SiteSnapshot after normal source registrations, before updates.
 baseline=json.loads(wp('source','eval-file','/tmp/integrated-operation.php','capture'))
 raw+='\n\nAfter initial save'
 source['markdown'].save(doc,raw.encode(),{'title':'Explanation','slug':'explanation','status':'publish','password':'','date':'2026-11-28 12:00:00','author_destination':source['markdown'].me['id']})
 source['markdown'].rest('pages/'+str(login),{'title':'Updated login'})
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
 def image_edit(item):
  return json.loads(source['markdown'].request('/?rest_route=/wp/v2/media/'+str(item['id'])+'/edit',json.dumps({'src':item['source_url'],'modifiers':[{'type':'rotate','args':{'angle':90}}]}).encode(),{'X-WP-Nonce':source['markdown'].nonce,'Content-Type':'application/json'})[0])
 def block(item):return '<!-- wp:image '+json.dumps({'id':item['id'],'width':12})+' --><figure class="wp-block-image"><img src="'+item['source_url']+'" class="wp-image-'+str(item['id'])+'" width="12"/></figure><!-- /wp:image -->'
 rotated=image_edit(image_result)
 imagepage=source['markdown'].rest('pages',{'title':'Image lifecycle','content':block(rotated),'status':'publish'})['id']
 replacement=image(source['markdown'])
 source['markdown'].rest('pages/'+str(imagepage),{'content':block(replacement)})
 source['markdown'].rest('media/'+str(replacement['id']),{'alt_text':'Replacement 12'})
 req=urllib.request.Request(source['markdown'].url+'/?rest_route=/wp/v2/media/'+str(rotated['id'])+'&force=true',headers={'X-WP-Nonce':source['markdown'].nonce},method='DELETE')
 assert json.loads(source['markdown'].op.open(req).read())['deleted']
 source['markdown'].rest('pages/'+str(imagepage),{'title':'Resaved lifecycle','content':block(replacement)})
 journal=json.loads(wp('source','eval','echo wp_json_encode(OzekiResilience\\M1\\ConstructionOperations::stable());'))
 b.joinpath('plugin-journal.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2))
 stages=[{'sequence':e['sequence'],'command':e['contract']['endpoint'],'coverage':e['contract']['coverage'],'reasons':e['contract']['reasons'],'outputs':e.get('outputs')} for e in journal['entries']]
 transfer=json.loads(wp('source','eval-file','/tmp/integrated-operation.php','publish'))
 run('cp',name+'-source:/tmp/kit-objects/.',str(b/'kit-objects'))
 run('cp',name+'-source:/tmp/kit-commit.json',str(b/'kit-commit.json'))
 run('exec',name+'-target','mkdir','-p','/tmp/kit-objects')
 run('cp',str(b/'kit-objects')+'/.',name+'-target:/tmp/kit-objects/')
 run('cp',str(b/'kit-commit.json'),name+'-target:/tmp/kit-commit.json')
 plan=json.loads(wp('target','eval-file','/tmp/integrated-operation.php','bundle'))
 if plan['held']:return {'passed':False,'baseline':baseline,'holds':plan['held']}
 def api(value):
  path=b/'follow-request.json';path.write_text(json.dumps(value));run('cp',str(path),name+'-target:/tmp/follow-request.json')
  return json.loads(wp('target','--user=destination-admin','eval-file','/tmp/product/tools/construction-api.php','/tmp/follow-request.json'))
 kitmod=load('kit')
 result=kitmod.Reconstruction(target,api,b/('reconstruction-'+str(time.time_ns())+'.json')).run(plan,lambda:json.loads(wp('target','eval-file','/tmp/integrated-operation.php','register')))
 if result['state']=='held':return {'passed':False,'baseline':baseline,'registration':result,'stages':stages}
 identities=result['follow']['identities'];completed=result['follow']['completed']
 assert completed==[e['sequence'] for e in plan['tail']]
 assert baseline['cutoff']>0 and len(completed)<len(journal['entries'])
 imagecontent=target['markdown'].rest('pages/'+str(identities['post:'+str(imagepage)])+'?context=edit')['content']['raw']
 assert 'wp-image-'+str(identities['post:'+str(replacement['id'])]) in imagecontent
 assert identities['image-url:full:'+str(replacement['id'])] in imagecontent
 assert identities['deleted:'+str(rotated['id'])] is True
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
 # Exercise the reconstructed member via the ordinary password-reset flow.
 import http.cookiejar
 jar=http.cookiejar.CookieJar();reader=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
 url=target['markdown'].url;lost=url+'/wp-login.php?action=lostpassword'
 f=mods['members'].Form(reader.open(lost).read().decode(),'lostpasswordform');v=f.values.copy();v['user_login']='reader@example.invalid'
 reader.open(f.action or lost,urllib.parse.urlencode(v).encode()).read()
 mails=json.loads(run('exec',name+'-target','cat','/tmp/member-mail.json'));links=[]
 for mail in mails:links+=re.findall(r'https?://[^\s<>]+action=rp[^\s<>]+',mail['message'])
 assert links,'Normal password reset did not issue a link'
 response=reader.open(html.unescape(links[-1]));reseturl=response.geturl();f=mods['members'].Form(response.read().decode(),'resetpassform');v=f.values.copy();v.update(pass1='isolated-reset-456',pass2='isolated-reset-456',pw_weak='on')
 reader.open(f.action or reseturl,urllib.parse.urlencode(v).encode()).read()
 loginurl=url+'/?page_id='+str(identities['post:'+str(login)])
 forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',reader.open(loginurl).read().decode(),re.S) if 'name="log"' in x];assert len(forms)==1
 f=mods['members'].Form(forms[0],None);v=f.values.copy();v.update(log='reader',pwd='isolated-reset-456');reader.open(f.action or loginurl,urllib.parse.urlencode(v).encode()).read()
 member_html=reader.open(url+'/?page_id='+str(newpage)).read().decode()
 guest=urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url+'/?page_id='+str(newpage)).read().decode()
 assert any('wordpress_logged_in_' in c.name for c in jar)
 assert 'Edited technical explanation' in member_html and 'Edited 42' in member_html
 assert 'Edited technical explanation' not in guest and 'Edited 42' not in guest
 receipt_entry=next(e for e in journal['entries'] if e['operation']=='flamingo-add')
 newreceipt=identities['post:'+str(receipt_entry['result']['id'])]
 receipt_html=target['markdown'].request('/wp-admin/admin.php?page=flamingo_inbound&post='+str(newreceipt)+'&action=edit')[0].decode()
 source_fields=receipt_entry['result']['receipt']['fields']
 actual_fields=json.loads(wp('target','eval','$m=new Flamingo_Inbound_Message('+str(newreceipt)+');echo wp_json_encode($m->fields);'))
 assert actual_fields==source_fields
 assert all(str(v) in html.unescape(receipt_html) for v in source_fields.values())
 # Ordinary later resave is another observed operation, not output correction.
 target['markdown'].rest('pages/'+str(newpage),{'title':'Ordinary resave'})
 assert target['markdown'].rest('pages/'+str(newpage)+'?context=edit')['content']['raw']==actual['content']['raw']
 return {'test_objects':{'page':newpage,'document':newdoc,'table':newtable,'form':newcf,'member':newmember,'login':identities['post:'+str(login)],'profile':identities['post:'+str(profile)],'imagepage':identities['post:'+str(imagepage)]},'passed':True,'baseline':baseline,'transfer':transfer,'image_lifecycle':True,'member_password_reset_login_access':True,'receipt_view_without_resending':True,'stages':stages,'completed':completed,'seconds':round(time.monotonic()-start,3),'image_original_and_thumbnail':True,'cf7_hash_embeds':True,'external_url_unchanged':True,'normal_rendering':True,'source_image_sha256':hashlib.sha256(png).hexdigest(),'typed_embeds':True,'settings_references':True,'structured_values_unchanged':True,'ordinary_resave':True,'identities_from_actual_results':identities}
