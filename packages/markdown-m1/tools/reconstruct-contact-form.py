"""CF7 reconstruction through normal authenticated REST registration and saving only."""
import argparse,copy,getpass,hashlib,html,importlib.util,json,re,urllib.parse
from pathlib import Path
_spec=importlib.util.spec_from_file_location('normal_wp_http',Path(__file__).with_name('reconstruct-markdown.py'))
_http=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_http)
Unsupported=_http.Unsupported
KEYS=['title','form','mail','mail_2','messages','additional_settings','locale']
EMBED=re.compile(r'\[contact-form-7\s+id=(?:"([A-Za-z0-9_-]+)"|\'([A-Za-z0-9_-]+)\'|([A-Za-z0-9_-]+))(?:\s+title="[^"\[\]]*")?\s*/?\]')
TAGS={'text','email','url','tel','number','date','textarea','select','checkbox','radio','acceptance','quiz','submit','hidden'}
def ref(m):return next(x for x in m.groups() if x is not None)
def validate(p):
    if set(p)!=set(KEYS):raise Unsupported('Incomplete form material')
    for k in ['title','form','additional_settings','locale']:
        if not isinstance(p[k],str):raise Unsupported('Invalid text material: '+k)
    if not re.fullmatch(r'[a-zA-Z_]+',p['locale']):raise Unsupported('Invalid locale')
    decoded=html.unescape(p['form'])
    if re.search(r'<\s*(?:script|iframe|object|embed|form|input|button|img)\b|\son\w+\s*=|javascript:|https?://',decoded,re.I):raise Unsupported('Executable markup or external/reference-bearing form markup requires review')
    for tag in re.findall(r'\[(/?[A-Za-z][\w-]*\*?)[^\]]*\]',decoded):
        if tag.lstrip('/').rstrip('*') not in TAGS:raise Unsupported('Unknown or reference-bearing form tag: '+tag)
    for line in p['additional_settings'].splitlines():
        if not line.strip():continue
        if not re.fullmatch(r'\s*(?:subscribers_only|demo_mode|skip_mail|do_not_store)\s*:\s*(?:on|off|true|false)\s*',line):raise Unsupported('Additional setting requires explicit review: '+line.split(':')[0])
    for k in ['mail','mail_2']:
        mail=p[k]
        if not isinstance(mail,dict):raise Unsupported('Missing mail structure')
        for key,value in mail.items():
            if key in ['active','use_html','exclude_blank']:
                if type(value) not in (bool,int) or value not in (0,1):raise Unsupported('Invalid mail flag: '+key)
            elif key in ['subject','sender','recipient','body','additional_headers','attachments']:
                if not isinstance(value,str):raise Unsupported('Invalid mail value: '+key)
            else:raise Unsupported('Unknown mail setting: '+key)
        if mail.get('attachments'):raise Unsupported('Attachments require a prepared destination file mapping')
        if mail.get('use_html'):raise Unsupported('HTML mail requires a separate application decision')
        if k=='mail' and mail.get('active',True)!=True:raise Unsupported('CF7 always enables primary mail on normal save')
    if not isinstance(p['messages'],dict) or any(not isinstance(v,str) for v in p['messages'].values()):raise Unsupported('Invalid message structure')
    return copy.deepcopy(p)

def page_content(raw,mapping):
    rest=EMBED.sub('',raw)
    if re.search(r'\[/?[A-Za-z_]|&#(?:0*91|x0*5b);|&lbrack;',rest,re.I):raise Unsupported('Unknown or escaped embedding requires review')
    simple=re.sub(r'<!-- /?wp:(?:paragraph|heading|shortcode) -->','',rest)
    simple=re.sub(r'</?(?:p|h[1-6]|strong|em)>|<br\s*/?>','',simple)
    if '<' in simple or re.search(r'https?://',simple):raise Unsupported('Additional page references/markup require the core registration map')
    if any(ref(m) not in mapping for m in EMBED.finditer(raw)):raise Unsupported('Referenced form was not registered')
    return EMBED.sub(lambda m:'[contact-form-7 id="'+str(mapping[ref(m)])+'"]',raw)

class NormalContactFormClient(_http.NormalMarkdownClient):
    def cf7(self,form_id=None,payload=None):
        route='/contact-form-7/v1/contact-forms'+('' if form_id is None else '/'+str(form_id))
        return json.loads(self.request('/?rest_route='+route,None if payload is None else json.dumps(payload,ensure_ascii=False).encode(),{'X-WP-Nonce':self.nonce,'Content-Type':'application/json'})[0])
    @staticmethod
    def inputs(response):
        p=response['properties']
        return {'title':response['title'],'locale':response['locale'],'form':p['form']['content'],'additional_settings':p['additional_settings']['content'],'mail':p['mail'],'mail_2':p['mail_2'],'messages':p['messages']}
    def verify(self,form_id,expected):
        actual=self.inputs(self.cf7(form_id));defaults={}
        for k in KEYS:
            if isinstance(expected[k],dict):
                for key,value in expected[k].items():
                    if key not in actual[k] or actual[k][key]!=value:raise Unsupported('Normal CF7 save changed '+k+'.'+key+'; no internal repair attempted')
                normalized={key:actual[k][key] for key,v in expected[k].items() if key in ('active','use_html','exclude_blank') and type(v)==int and type(actual[k][key])==bool}
                if normalized:defaults[k+'_normal_boolean_output']=normalized
                added={key:v for key,v in actual[k].items() if key not in expected[k]}
                if added:
                    if k=='messages' or k=='mail' and added=={'active':True}:defaults[k]=added
                    else:raise Unsupported('Unexpected defaults in '+k)
            elif actual[k]!=expected[k]:raise Unsupported('Normal CF7 save changed '+k+'; no internal repair attempted')
        return defaults
    def save_form(self,form_id,payload):
        r=self.cf7(form_id,{**payload,'context':'save'});self.verify(form_id,payload);return r
    def rebuild(self,plan,journal_path,author_map):
        if plan['schema']!='owr-normal-cf7-registration-1' or plan['source_url'].rstrip('/')==self.url:raise Unsupported('Invalid plan or destination collision')
        state={'state':'planning','through':plan['through'],'forms':{},'pages':{},'held':dict(plan['held']) if plan['held'] else {},'excluded':plan['excluded'],'defaults':{},'config_errors':{},'plan_sha256':hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()}
        journal=Path(journal_path)
        with journal.open('x',encoding='utf-8') as f:json.dump(state,f)
        def record():journal.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            eligible=[];owners={};ambiguous=set()
            for item in plan['forms']:
                for alias in [item['origin_id'],item['origin_hash']]:
                    if not alias:continue
                    if alias in owners and owners[alias]!=item['origin_id']:ambiguous.add(alias)
                    owners[alias]=item['origin_id']
            for item in plan['forms']:
                try:
                    if any(x in ambiguous for x in [item['origin_id'],item['origin_hash']]):raise Unsupported('Ambiguous source form identity')
                    eligible.append((item,validate(item['input'])))
                except Unsupported as e:state['held']['form:'+item['origin_id']]=str(e)
            mapping={};state['state']='registering';record()
            for item,payload in eligible:
                old=item['origin_id'];r=self.cf7(payload={**payload,'context':'save'});new=r['id'];state['forms'][old]=new;record()
                state['defaults'][old]=self.verify(new,payload)
                r=self.save_form(new,payload);errors=r.get('config_errors',[])
                if errors:
                    state['config_errors'][old]=errors;state['held']['form:'+old]='CF7 configuration warnings: registered, but not linked to a page';record();continue
                for alias in [old,item['origin_hash']]:
                    if alias:mapping[alias]=new
                record()
            for p in plan['pages']:
                try:
                    if not author_map.get(str(p['author_origin'])):raise Unsupported('Explicit author mapping required')
                    content=page_content(p['content'],mapping)
                except Unsupported as e:state['held']['page:'+str(p['origin_id'])]=str(e);record();continue
                endpoint='pages' if p['type']=='page' else 'posts'
                payload={k:p[k] for k in ['title','slug','status','password','excerpt','comment_status','ping_status']}
                payload.update(content=content,date_gmt=p['date_gmt'].replace(' ','T'),author=author_map[str(p['author_origin'])])
                new=self.rest(endpoint,payload)['id'];state['pages'][str(p['origin_id'])]=new;record()
                if self.rest(endpoint+'/'+str(new)+'?context=edit')['content']['raw']!=content:raise Unsupported('Page registration changed content')
            state['state']='completed';record();return state
        except Exception as e:state['state']='failed';state['error']=str(e);record();raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','url','username','journal','author-map']:p.add_argument('--'+k,required=True)
    p.add_argument('--isolated',action='store_true');a=p.parse_args()
    c=NormalContactFormClient(a.url,a.username,getpass.getpass('WordPress password: '),a.isolated)
    print(json.dumps(c.rebuild(json.loads(Path(a.plan).read_text(encoding='utf-8-sig')),a.journal,json.loads(Path(a.author_map).read_text(encoding='utf-8-sig'))),ensure_ascii=False,indent=2))
