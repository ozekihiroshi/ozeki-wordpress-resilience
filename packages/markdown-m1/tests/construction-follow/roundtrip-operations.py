import importlib.util,json,time

def execute(run,wp,name,b):
 def load(path,key):
  spec=importlib.util.spec_from_file_location(key,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 first=load(b/'combined-operations.py','first_generation').execute(run,wp,name,b)
 if not first['passed']:return {'passed':False,'first':first}
 start=time.monotonic();objects=first['test_objects']
 mods={k:load(b/('product/tools/reconstruct-'+k+'.py'),'second_'+k) for k in ['markdown','tablepress','contact-form','members','acf','kit']}
 classes={'markdown':'NormalMarkdownClient','tablepress':'NormalTablePressClient','contact-form':'NormalContactFormClient','members':'NormalMemberClient','acf':'NormalAcfClient'}
 def clients(site,user):
  return {k:getattr(mods[k],v)(wp(site,'option','get','home').strip(),user,'isolated-only-123',True) for k,v in classes.items()}
 source=clients('target','destination-admin');dest=clients('third','third-admin')
 # The reconstructed site becomes a new source. No original A IDs are passed to C.
 baseline=json.loads(wp('target','eval-file','/tmp/integrated-operation.php','capture'))
 source['markdown'].rest('pages/'+str(objects['page']),{'title':'Second generation edit'})
 raw=source['markdown'].export(objects['document'])[0]+b'\n\nSECOND-GENERATION-EDIT'
 source['markdown'].save(objects['document'],raw,{'title':'Explanation','slug':'explanation','status':'publish','password':'','date':'2026-11-28 12:00:00','author_destination':source['markdown'].me['id']})
 table={'name':'Readings','description':'Second generation','data':[['Device','Value'],['PLC','SECOND-TABLE']],'options':{'table_head':1,'table_foot':0,'use_datatables':False},'visibility':{'rows':[1,1],'columns':[1,1]}}
 source['tablepress'].save_table(str(objects['table']),table)
 source['contact-form'].cf7(objects['form'],{'title':'Second inquiry title','context':'save'})
 transfer=json.loads(wp('target','eval-file','/tmp/integrated-operation.php','publish'))
 local=b/'second-objects';local.mkdir(exist_ok=True)
 run('cp',name+'-target:/tmp/kit-objects/.',str(local));run('cp',name+'-target:/tmp/kit-commit.json',str(b/'second-commit.json'))
 run('exec',name+'-third','mkdir','-p','/tmp/kit-objects');run('cp',str(local)+'/.',name+'-third:/tmp/kit-objects/')
 run('cp',str(b/'second-commit.json'),name+'-third:/tmp/kit-commit.json')
 plan=json.loads(wp('third','eval-file','/tmp/integrated-operation.php','bundle'))
 if plan['held']:return {'passed':False,'first':first,'second_baseline':baseline,'second_holds':plan['held']}
 def api(value):
  path=b/'third-request.json';path.write_text(json.dumps(value));run('cp',str(path),name+'-third:/tmp/third-request.json')
  return json.loads(wp('third','--user=third-admin','eval-file','/tmp/product/tools/construction-api.php','/tmp/third-request.json'))
 result=mods['kit'].Reconstruction(dest,api,b/('third-'+str(time.time_ns())+'.json')).run(plan,lambda:json.loads(wp('third','eval-file','/tmp/integrated-operation.php','register')))
 if result['state']=='held':return {'passed':False,'first':first,'second_baseline':baseline,'second_registration':result}
 ids=result['follow']['identities'];page=ids['post:'+str(objects['page'])];doc=ids['post:'+str(objects['document'])]
 assert result['follow']['completed']==[e['sequence'] for e in plan['tail']]
 actual=dest['markdown'].rest('pages/'+str(page)+'?context=edit');assert actual['title']['raw']=='Second generation edit'
 markup=dest['markdown'].request('/?page_id='+str(page))[0].decode()
 assert 'SECOND-GENERATION-EDIT' in markup and 'SECOND-TABLE' in markup
 assert b'SECOND-GENERATION-EDIT' in dest['markdown'].export(doc)[0]
 dest['tablepress'].verify(str(ids['table:'+str(objects['table'])]),table)
 dest['markdown'].rest('pages/'+str(page),{'title':'Third ordinary resave'})
 assert dest['markdown'].rest('pages/'+str(page)+'?context=edit')['content']['raw']==actual['content']['raw']
 return {'passed':True,'first':first,'second_baseline':baseline,'second_transfer':transfer,'second_completed':result['follow']['completed'],'third_normal_display_and_resave':True,'second_seconds':round(time.monotonic()-start,3)}
