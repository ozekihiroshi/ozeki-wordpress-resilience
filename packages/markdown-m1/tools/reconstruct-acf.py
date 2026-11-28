"""Isolated ACF reconstruction through its existing JSON import and post edit forms."""
import argparse,getpass,hashlib,html,importlib.util,json,re,urllib.parse
from pathlib import Path
from html.parser import HTMLParser
spec=importlib.util.spec_from_file_location('acf_http',Path(__file__).with_name('reconstruct-markdown.py'))
http=importlib.util.module_from_spec(spec);spec.loader.exec_module(http)
Unsupported=http.Unsupported

class Controls(HTMLParser):
    """Read successful field controls, including multi-select and hidden checkbox defaults."""
    def __init__(self,markup):
        super().__init__(convert_charrefs=True);self.pairs=[];self.area=None;self.select=None;self.option=None;self.feed(markup)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);name=a.get('name')
        if tag=='input' and name and 'disabled' not in a and a.get('type') not in ('submit','button','reset','file') and (a.get('type') not in ('checkbox','radio') or 'checked' in a):self.pairs.append((name,a.get('value','')))
        if tag=='textarea' and name and 'disabled' not in a:self.area=[name,'']
        if tag=='select' and name and 'disabled' not in a:self.select=[name,'multiple' in a,[]]
        if tag=='option' and self.select:self.option=[a.get('value'),'', 'selected' in a,'disabled' in a]
    def handle_data(self,data):
        if self.area:self.area[1]+=data
        if self.option:self.option[1]+=data
    def handle_endtag(self,tag):
        if tag=='textarea' and self.area:self.pairs.append(tuple(self.area));self.area=None
        if tag=='option' and self.option:
            a=self.option
            if not a[3]:self.select[2].append((a[0] if a[0] is not None else a[1],a[2]))
            self.option=None
        if tag=='select' and self.select:
            name,multi,options=self.select;chosen=[v for v,s in options if s]
            if not chosen and not multi and options:chosen=[options[0][0]]
            self.pairs.extend((name,v) for v in chosen);self.select=None
    def values(self):
        out={}
        for name,value in self.pairs:
            if name.endswith('[]'):
                key=name[:-2]
                if not isinstance(out.get(key),list):out[key]=[]
                out[key].append(value)
            else:out[name]=value
        return out

class NormalAcfClient(http.NormalMarkdownClient):
    tools='/wp-admin/edit.php?post_type=acf-field-group&page=acf-tools'
    def export(self,keys=None):
        url=self.tools+'&tool=export';markup=self.request(url)[0].decode();controls=Controls(markup)
        class Keys(HTMLParser):
            def __init__(self,text):super().__init__();self.keys=[];self.feed(text)
            def handle_starttag(self,t,attrs):
                a=dict(attrs)
                if t=='input' and a.get('name')=='keys[]':self.keys.append(a['value'])
        available=Keys(markup).keys
        if keys is None:keys=available
        if not keys:return []
        if any(k not in available for k in keys):raise Unsupported('Normal export cannot find registered definition')
        pairs=[('_acf_nonce',controls.values()['_acf_nonce']),('action','download')]+[('keys[]',k) for k in keys]
        return json.loads(self.request(url,urllib.parse.urlencode(pairs).encode())[0])
    def import_groups(self,groups):
        url=self.tools+'&tool=import';markup=self.request(url)[0].decode();nonce=http.Fields(markup).values['_acf_nonce']
        raw=json.dumps(groups,ensure_ascii=False).encode();boundary='----OwrAcf'+hashlib.sha256(raw).hexdigest();chunks=[]
        for k,v in {'_acf_nonce':nonce,'import_type':'json'}.items():chunks.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode())
        chunks.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="acf_import_file"; filename="material.json"\r\nContent-Type: application/json\r\n\r\n').encode()+raw+b'\r\n')
        result=self.request(url,b''.join(chunks)+('--'+boundary+'--\r\n').encode(),{'Content-Type':'multipart/form-data; boundary='+boundary})[0].decode()
        if not re.search(r'Imported (?:1 item|[0-9]+ items)',result):raise Unsupported('Import not confirmed; inspect destination, do not retry blindly')
        actual=self.export([g['key'] for g in groups])
        if {g['key']:g for g in actual}!={g['key']:g for g in groups}:raise Unsupported('Normal import/export differs; no repair attempted')
    def save_values(self,pid,kind,values):
        endpoint='pages' if kind=='page' else 'posts';saved=self.rest(endpoint+'/'+str(pid)+'?context=edit')
        url='/wp-admin/post.php?post='+str(pid)+'&action=edit';markup=self.request(url)[0].decode();fields=http.Fields(markup).values
        if not fields.get('_acf_nonce'):raise Unsupported('Normal ACF post form unavailable')
        p={'action':'editpost','post_ID':pid,'post_type':kind,'_wpnonce':fields['_wpnonce'],'_acf_nonce':fields['_acf_nonce'],'_acf_screen':fields.get('_acf_screen','post'),'_acf_post_id':fields.get('_acf_post_id',str(pid)),'post_title':saved['title']['raw'],'content':saved['content']['raw'],'post_status':saved['status'],'original_post_status':saved['status'],'post_password':saved.get('password',''),'post_name':saved['slug'],'excerpt':saved['excerpt']['raw'],'comment_status':saved['comment_status'],'ping_status':saved['ping_status'],'post_parent':saved.get('parent',0),'user_ID':self.me['id']}
        pairs=list(p.items())
        for key,value in values.items():
            if 'acf['+key+']' not in markup:raise Unsupported('Field absent from normal editor: '+key)
            if isinstance(value,list):
                if value:pairs.extend(('acf['+key+'][]',v) for v in value)
                else:pairs.append(('acf['+key+']',''))
            else:pairs.append(('acf['+key+']',value))
        self.request('/wp-admin/post.php',urllib.parse.urlencode(pairs).encode())
        after=Controls(self.request(url)[0].decode()).values()
        for key,value in values.items():
            actual=after.get('acf['+key+']','')
            # HTML lists selected options in definition order, not stored selection order.
            # Compare displayed selection membership only; never reorder submitted values.
            matches=actual==value or (value==[] and actual=='') or (isinstance(value,list) and isinstance(actual,list) and sorted(value)==sorted(actual))
            if not matches:raise Unsupported('Normal saved form differs: '+key+'; no repair attempted')
        current=self.rest(endpoint+'/'+str(pid)+'?context=edit')
        for k in ('status','password','slug','parent','comment_status','ping_status'):
            if current.get(k)!=saved.get(k):raise Unsupported('Owner setting changed during normal save: '+k)
        for k in ('content','title','excerpt'):
            if current[k]['raw']!=saved[k]['raw']:raise Unsupported('Owner content changed during normal save: '+k)
    def rebuild(self,plan,post_map,journal):
        if plan['schema']!='owr-normal-acf-registration-1' or plan['source_url'].rstrip('/')==self.url:raise Unsupported('Invalid plan/source destination')
        state={'state':'preflight','groups':[],'posts':{},'held':plan.get('held') or {},'through':plan['through']};path=Path(journal)
        with path.open('x',encoding='utf-8') as f:json.dump(state,f)
        def record():path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            if state['held']:state['state']='held';record();return state
            plugin=self.rest('plugins/advanced-custom-fields/acf')
            if plugin['status']!='active' or plugin['version']!=plan['version']:raise Unsupported('Prepare the recorded ACF free version')
            existing=self.export();keys={g['key'] for g in existing};fieldkeys={f['key'] for g in existing for f in g['fields']};names={f['name'] for g in existing for f in g['fields']}
            for g in plan['groups']:
                if g['key'] in keys or any(f['key'] in fieldkeys or f['name'] in names for f in g['fields']):raise Unsupported('Existing definition/key/name collision; no overwrite')
            for item in plan['posts']:
                dest=post_map.get(item['origin_id'])
                if not isinstance(dest,int) or dest<=0:raise Unsupported('Explicit new owner ID mapping required')
                p=self.rest(('pages' if item['type']=='page' else 'posts')+'/'+str(dest)+'?context=edit')
                if p['status'] not in ('draft','private'):raise Unsupported('Prepare an unpublished owner before registration; publication is separate')
            if len(set(post_map.values()))!=len(post_map):raise Unsupported('Owner mappings must be distinct')
            state['state']='importing';record()
            if plan['groups']:self.import_groups(plan['groups'])
            state['groups']=[g['key'] for g in plan['groups']];record()
            for item in plan['posts']:
                self.save_values(post_map[item['origin_id']],item['type'],item['values']);state['posts'][item['origin_id']]=post_map[item['origin_id']];record()
            if existing and existing!=self.export([g['key'] for g in existing]):raise Unsupported('Prepared definitions changed')
            state['state']='completed';record();return state
        except Exception as e:state['state']='stopped';state['error']=str(e);record();raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('plan','url','username','post-map','journal'):p.add_argument('--'+k,required=True)
    p.add_argument('--isolated',action='store_true');a=p.parse_args()
    client=NormalAcfClient(a.url,a.username,getpass.getpass('Administrator password: '),a.isolated)
    print(json.dumps(client.rebuild(json.loads(Path(a.plan).read_text(encoding='utf-8-sig')),json.loads(Path(a.post_map).read_text(encoding='utf-8-sig')),a.journal),ensure_ascii=False,indent=2))
