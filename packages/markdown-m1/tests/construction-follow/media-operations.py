"""Real core operations; replay receives the journal, not this source recipe."""
from pathlib import Path
import importlib.util,json,urllib.parse,urllib.request,urllib.error,struct,zlib,time,hashlib,re

def execute(run,wp,name,b):
 def load(key):
  sp=importlib.util.spec_from_file_location('fixture_'+key,b/('product/tools/reconstruct-'+key+'.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
 http=load('markdown');dispatch=load('operations');started=time.monotonic()
 def client(site):return http.NormalMarkdownClient(wp(site,'option','get','home').strip(),'source-operator' if site=='source' else 'destination-admin','isolated-only-123',True)
 source=client('source');target=client('target')
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 pixels=b''.join(b'\0'+bytes(v for x in range(320) for v in (x%256,y%256,(x+y)%256)) for y in range(240))
 png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,240,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
 def upload(c):return json.loads(c.request('/?rest_route=/wp/v2/media',png,{'X-WP-Nonce':c.nonce,'Content-Type':'image/png','Content-Disposition':'attachment; filename="media.png"'})[0])
 prepared=upload(target)
 wp('source','eval',"$p=get_posts(['numberposts'=>1])[0];$k=OzekiResilience\\M1\\ConstructionOperations::initialSaveWithAuthors(fn()=>[['source_url'=>home_url()],['content.json'=>wp_json_encode(['tables'=>['posts'=>[(array)$p]]])]]);file_put_contents('/tmp/seed-kit.json',wp_json_encode($k));")
 run('cp',name+'-source:/tmp/seed-kit.json',str(b/'seed-kit.json'));run('cp',str(b/'seed-kit.json'),name+'-target:/tmp/seed-kit.json')
 authors=json.loads(wp('target','--user=destination-admin','eval',"$k=json_decode(file_get_contents('/tmp/seed-kit.json'),true);echo wp_json_encode(OzekiResilience\\M1\\ConstructionAuthors::register(['files'=>$k['files'],'anchor'=>$k['construction_anchor']]));"))
 mapping={'user:'+str(k):v for k,v in authors.items()}
 def edit(c,id,payload):return json.loads(c.request('/?rest_route=/wp/v2/media/'+str(id)+'/edit',json.dumps(payload).encode(),{'X-WP-Nonce':c.nonce,'Content-Type':'application/json'})[0])
 def delete(c,id):
  r=urllib.request.Request(c.url+'/?rest_route=/wp/v2/media/'+str(id)+'&force=true',headers={'X-WP-Nonce':c.nonce},method='DELETE');return json.loads(c.op.open(r,timeout=30).read())
 def blocks(items):
  value='<!-- wp:group {"layout":{"type":"constrained"}} --><div class="wp-block-group"><!-- wp:gallery {"columns":2,"imageCrop":false} --><figure class="wp-block-gallery has-nested-images columns-2">'
  for item in items:
   attrs={'id':item['id'],'sizeSlug':'full','linkDestination':'none','width':12}
   value+='<!-- wp:image '+json.dumps(attrs,separators=(',',':'))+' --><figure class="wp-block-image size-full"><img src="'+item['source_url']+'" class="wp-image-'+str(item['id'])+'" alt="Number 12" width="12"/></figure><!-- /wp:image -->'
  return value+'</figure><!-- /wp:gallery --><!-- wp:paragraph --><p>日本語 12</p><!-- /wp:paragraph --></div><!-- /wp:group -->'
 pixel_oracle={}
 def pixel_signature(data):
  return run('exec','-i',name+'-source','php','-r',"$im=imagecreatefromstring(stream_get_contents(STDIN));$h=hash_init('sha256');hash_update($h,imagesx($im).':'.imagesy($im));for($y=0;$y<imagesy($im);$y++)for($x=0;$x<imagesx($im);$x++)hash_update($h,pack('N',imagecolorat($im,$x,$y)));echo hash_final($h);",raw=data).decode()
 def remember(item):pixel_oracle[item['id']]=pixel_signature(source.request(item['source_url'])[0])
 original=upload(source);oid=original['id'];remember(original)
 source.rest('media/'+str(oid),{'title':'Original','alt_text':'12 is text','caption':'Original caption','author':source.me['id']})
 page=source.rest('pages',{'title':'Recorded gallery','content':blocks([original,original]),'status':'publish'})['id']
 rotated=edit(source,oid,{'src':original['source_url'],'modifiers':[{'type':'rotate','args':{'angle':90}}]})
 assert rotated['id']!=oid;remember(rotated)
 cropped=edit(source,rotated['id'],{'src':rotated['source_url'],'modifiers':[{'type':'crop','args':{'left':10,'top':10,'width':80,'height':80}}]})
 assert cropped['id']!=rotated['id'];remember(cropped)
 source.rest('pages/'+str(page),{'content':blocks([cropped,original])})
 replacement=upload(source);remember(replacement)
 source.rest('pages/'+str(page),{'content':blocks([replacement,replacement])})
 source.rest('media/'+str(replacement['id']),{'alt_text':'Replacement 12','description':'Ordinary updated description'})
 source.rest('pages/'+str(page),{'content':'<!-- wp:paragraph --><p>Images removed normally.</p><!-- /wp:paragraph -->'})
 # Original and intermediates are no longer referenced by this page.
 for item in [original,rotated,cropped]:assert delete(source,item['id'])['deleted'] is True
 source.rest('pages/'+str(page),{'content':blocks([replacement])})
 assert delete(source,replacement['id'])['deleted'] is True
 # Native WordPress keeps a dangling reference. Record its deleted state instead
 # of resurrecting a file, stripping the block, or substituting another image.
 source.rest('pages/'+str(page),{'title':'After normal deletion','content':blocks([replacement])})
 journal=json.loads(wp('source','eval','echo wp_json_encode(OzekiResilience\\M1\\ConstructionOperations::stable());'))
 b.joinpath('media-journal.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2))
 stages=[{'sequence':e['sequence'],'endpoint':e['contract']['endpoint'],'coverage':e['contract']['coverage'],'reasons':e['contract']['reasons']} for e in journal['entries']]
 gaps=[e for e in stages if e['coverage']!='complete']
 if gaps:return {'passed':False,'capture_gaps':gaps,'stages':stages}
 completed=[];checks=[]
 def api(value):
  path=b/'step.json';path.write_text(json.dumps(value));run('cp',str(path),name+'-target:/tmp/step.json')
  return json.loads(wp('target','--user=destination-admin','eval-file','/tmp/product/tools/construction-api.php','/tmp/step.json'))
 def attributes(text):return [json.loads(x) for x in re.findall(r'<!-- wp:image (\{.*?\}) -->',text)]
 def absent(c,id):
  try:c.rest('media/'+str(id));return False
  except urllib.error.HTTPError as e:return e.code==404
 for e in journal['entries']:
  q=api({'operation':'prepare-operation','entry':e,'through':e['sequence']-1,'identities':mapping})
  new=dispatch.dispatch(q,e,{'markdown':target},{'markdown':http},None)
  mapping=api({'operation':'accept-operation','entry':e,'returned':new,'identities':mapping});completed.append(e['sequence'])
  endpoint=q['endpoint'];response=e['result'].get('response') or {}
  if endpoint in ('wordpress.media-upload','wordpress.media-edit'):
   actual=target.rest('media/'+str(new['id']));assert actual['media_details']['width']==response['media_details']['width'] and actual['media_details']['height']==response['media_details']['height']
   # Expected bytes are a test oracle only, never input to the replay.
   assert pixel_signature(target.request(actual['source_url'])[0])==pixel_oracle[response['id']],('Edited pixels differ',e['sequence'])
   checks.append({'operation':e['sequence'],'normal_image_size':[actual['media_details']['width'],actual['media_details']['height']]})
  if endpoint=='/wp/v2/pages':
   content=target.rest('pages/'+str(new)+'?context=edit')['content']['raw']
   if 'content' in q['arguments']:
    assert content==q['arguments']['content'],'Normal core save changed prepared content'
    for a in attributes(content):assert a['width']==12 and a['id'] in mapping.values()
    if '<img' in content:
     rendered=target.request('/?page_id='+str(new))[0].decode();assert '日本語 12' in rendered
  if endpoint=='wordpress.media-delete':assert absent(target,q['target'])
 assert target.request(prepared['source_url'])[0]==png,'Prepared file changed'
 for item in [original,rotated,cropped,replacement]:assert absent(source,item['id']) and absent(target,mapping['post:'+str(item['id'])])
 final=target.rest('pages/'+str(mapping['post:'+str(page)])+'?context=edit')['content']['raw']
 assert 'wp-image-'+str(mapping['post:'+str(replacement['id'])]) in final,'Deleted reference was silently repaired'
 assert any(s.get('source_state')=='deleted' for s in journal['entries'][-1]['contract']['spans'])
 return {'passed':True,'seconds':round(time.monotonic()-started,3),'stages':stages,'completed':completed,'image_checks':checks,'block_numbers_unchanged':True,'new_edit_id_not_forced_to_old':True,'normal_replacement':True,'normal_removal_and_deletion':True,'deleted_reference_recorded_not_repaired':True,'prepared_file_unchanged':True,'source_original_sha256':hashlib.sha256(png).hexdigest()}
