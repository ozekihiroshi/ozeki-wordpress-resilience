"""Isolated normal operation dispatch. No database correction or source-ID installation."""
import json,urllib.parse,urllib.request,re

def import_acf(c,modules,groups):
 # Normal ACF defaults are output, not missing input.
 url=c.tools+'&tool=import';nonce=modules['markdown'].Fields(c.request(url)[0].decode()).values['_acf_nonce'];boundary='----RecordedAcfOperation';raw=json.dumps(groups,ensure_ascii=False).encode()
 body=('--'+boundary+'\r\nContent-Disposition: form-data; name="_acf_nonce"\r\n\r\n'+nonce+'\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="import_type"\r\n\r\njson\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="acf_import_file"; filename="material.json"\r\nContent-Type: application/json\r\n\r\n').encode()+raw+('\r\n--'+boundary+'--\r\n').encode()
 response=c.request(url,body,{'Content-Type':'multipart/form-data; boundary='+boundary})[0].decode()
 if not re.search(r'Imported (?:1 item|[0-9]+ items)',response):raise RuntimeError('Normal ACF import not confirmed')
 return c.export([g['key'] for g in groups])

def flatten(value,prefix=''):
 pairs=[]
 if isinstance(value,dict):
  for k,v in value.items():pairs+=flatten(v,str(k) if not prefix else prefix+'['+str(k)+']')
 elif isinstance(value,list):
  for n,v in enumerate(value):pairs+=flatten(v,prefix+'['+str(n)+']')
 else:pairs.append((prefix,'' if value is None else str(value)))
 return pairs
def dispatch(q,e,clients,modules,receipt):
 ep=q['endpoint'];a=q['arguments'];id=q['target'];c=clients['markdown']
 if ep=='wordpress.media-upload':
  import base64
  r=json.loads(c.request('/?rest_route=/wp/v2/media',base64.b64decode(a['base64']),{'X-WP-Nonce':c.nonce,'Content-Type':a['content_type'],'Content-Disposition':a['content_disposition']})[0])
  values={'image-url:full':r['source_url']}
  values.update({'image-url:'+k:v['source_url'] for k,v in r.get('media_details',{}).get('sizes',{}).items() if 'source_url' in v})
  return {'id':r['id'],'reference_values':values}
 if ep=='wordpress.media-delete':
  request=urllib.request.Request(c.url+'/?rest_route=/wp/v2/media/'+str(id)+'&'+urllib.parse.urlencode(a),headers={'X-WP-Nonce':c.nonce},method='DELETE')
  r=json.loads(c.op.open(request,timeout=30).read())
  if r.get('deleted') is not True or r.get('previous',{}).get('id')!=id:raise RuntimeError('Normal media deletion not confirmed')
  return True
 if ep=='wordpress.media-edit':
  r=json.loads(c.request('/?rest_route=/wp/v2/media/'+str(id)+'/edit',json.dumps(a).encode(),{'X-WP-Nonce':c.nonce,'Content-Type':'application/json'})[0])
  values={'image-url:full':r['source_url']};values.update({'image-url:'+k:v['source_url'] for k,v in r.get('media_details',{}).get('sizes',{}).items() if 'source_url' in v})
  return {'id':r['id'],'reference_values':values}
 if ep.startswith('/'):
  response=json.loads(c.request('/?rest_route='+ep+('' if id is None else '/'+str(id)),json.dumps(a).encode(),{'X-WP-Nonce':c.nonce,'Content-Type':'application/json'})[0])
  if ep=='/contact-form-7/v1/contact-forms':
   # Normal REST list reports the public hash. Select by the actual returned ID,
   # never by a source hash, title, slug or numeric coincidence.
   items=json.loads(c.request('/?rest_route='+ep,None,{'X-WP-Nonce':c.nonce})[0]);matches=[x for x in items if x['id']==response['id']]
   if len(matches)!=1 or not matches[0].get('hash'):raise RuntimeError('Normal form result hash missing')
   return {'id':response['id'],'reference_values':{'cf7-hash':matches[0]['hash']}}
  if ep=='/wp/v2/media':
   values={'image-url:full':response['source_url']};values.update({'image-url:'+k:v['source_url'] for k,v in response.get('media_details',{}).get('sizes',{}).items() if 'source_url' in v})
   return {'id':response['id'],'reference_values':values}
  return response['id']
 if ep=='flamingo.add':return receipt(e,a['form_id'])
 body=a['body'].copy()
 def tokens(fields):
  if not isinstance(a.get('nonce_fields'),list):raise RuntimeError('Source form participant contract missing')
  for k in a['nonce_fields']:
   if k not in fields:raise RuntimeError('Prepared normal form lacks recorded token: '+k)
   body[k]=fields[k]
 if ep=='markdown.import':
  import base64
  f=a['files']['ozmd_file'];return c.import_document(base64.b64decode(f['base64']),f['name'])
 if ep=='tablepress.import':return clients['tablepress'].import_table(json.loads(body['import']['form-field']))
 if ep=='tablepress.save':
  t=body['tablepress'];data={k:t[k] for k in ['name','description']};data.update({k:json.loads(t[k]) for k in ['data','options','visibility']});clients['tablepress'].save_table(str(id),data);return str(id)
 if ep=='acf.import':
  import base64
  import_acf(clients['acf'],modules,json.loads(base64.b64decode(a['files']['acf_import_file']['base64'])));return True
 if ep=='wordpress.edit':
  fields=modules['markdown'].Fields(c.request('/wp-admin/post.php?post='+str(id)+'&action=edit')[0].decode()).values
  tokens(fields)
  c.request('/wp-admin/post.php',urllib.parse.urlencode(flatten(body)).encode());return id
 if ep=='members.settings':
  m=clients['members'];mode=body['wpmem_admin_a']
  if mode=='update_settings':f=m.form(m.settingsurl,'updatesettings')
  elif mode=='add_field':f=modules['members'].Form(m.request(m.fieldurl,{'add_field':'true'})[0].decode(),'addfieldform')
  elif mode=='edit_field':f=m.form(m.fieldurl+'&mode=edit&field='+urllib.parse.quote(body['add_option']),'editfieldform')
  else:raise RuntimeError('No tested ordinary dispatcher for '+mode)
  tokens(f.values)
  m.submit(f,body);return True
 if ep in ('members.create','members.profile'):
  m=clients['members'];f=m.form('/wp-admin/user-new.php' if ep=='members.create' else '/wp-admin/user-edit.php?user_id='+str(id),'createuser' if ep=='members.create' else 'your-profile')
  tokens(f.values)
  if ep=='members.create':
   password=f.controls['pass1'].get('data-pw') or f.values.get('pass1');body.update(pass1=password,pass2=password)
  m.submit(f,body)
  if id:return id
  users=m.rest('users?context=edit&search='+urllib.parse.quote(body['user_login']));found=[u['id'] for u in users if u['username']==body['user_login']]
  if len(found)!=1:raise RuntimeError('Normal account registration result unresolved')
  return found[0]
 raise RuntimeError('No ordinary dispatcher: '+ep)
