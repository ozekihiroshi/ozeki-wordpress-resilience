"""WP-Members reconstruction through existing administrator forms; isolated use only."""
import argparse,copy,csv,getpass,html,importlib.util,io,json,re,urllib.parse
from pathlib import Path
from html.parser import HTMLParser
spec=importlib.util.spec_from_file_location('member_http',Path(__file__).with_name('reconstruct-markdown.py'))
http=importlib.util.module_from_spec(spec);spec.loader.exec_module(http)
Unsupported=http.Unsupported

class Form(HTMLParser):
    def __init__(self,markup,identity):
        super().__init__(convert_charrefs=True);self.identity=identity;self.inside=False;self.found=False;self.values={};self.controls={};self.action='';self.area=None;self.select=None;self.option=None;self.feed(markup)
        if not self.found:raise Unsupported('Normal form unavailable: '+identity)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form':
            self.inside=self.identity is None or a.get('id')==self.identity or a.get('name')==self.identity
            if self.inside:self.found=True;self.action=a.get('action','')
        if not self.inside:return
        name=a.get('name')
        if tag=='input' and name:
            self.controls[name]=a
            if 'disabled' not in a and a.get('type') not in ('submit','button','file','reset') and (a.get('type') not in ('checkbox','radio') or 'checked' in a):self.values[name]=a.get('value','')
        if tag=='textarea' and name:self.area=name;self.controls[name]=a;self.values[name]=''
        if tag=='select' and name:self.select=name;self.controls[name]=a;self.option=None
        if tag=='option' and self.select:
            self.option=a;self.option_text='';self.option_selected=self.select not in self.values or 'selected' in a
            if self.option_selected:self.values[self.select]=a.get('value','')
    def handle_data(self,data):
        if self.inside and self.area:self.values[self.area]+=data
        if self.inside and self.select and self.option is not None and self.option_selected and 'value' not in self.option:
            self.option_text+=data;self.values[self.select]=self.option_text.strip()
    def handle_endtag(self,tag):
        if tag=='textarea':self.area=None
        if tag=='select':self.select=None
        if tag=='option':self.option=None
        if tag=='form':self.inside=False

def fdict(f):return {str(k):v for k,v in enumerate(f)} if isinstance(f,list) else f

def block_control(markup):
    # Gutenberg and classic editors wrap the same metabox in different forms.
    inputs=''.join(re.findall(r'<input\b[^>]*>',markup))
    return Form('<form id="restriction-check">'+inputs+'</form>','restriction-check').values.get('wpmem_block')

def field_input(field):
    f=fdict(field);typ=f['3'];allowed={'text','email','url','textarea','password','checkbox','select','radio'}
    if typ not in allowed:raise Unsupported('Field type needs a separately verified normal operation: '+typ)
    if not re.fullmatch(r'[A-Za-z0-9_]+',f['2']):raise Unsupported('Unsupported field name')
    if any(v for k,v in f.items() if k not in {'0','1','2','3','4','5','6','7','8','profile','placeholder','pattern','title','rows','cols','checkbox_label'}):raise Unsupported('Unmapped field definition property')
    p={'add_name':f['1'],'add_option':f['2'],'add_type':typ,'add_order_id':f['0'],'add_display':f['4'],'add_required':f['5'],'add_profile':'y' if f.get('profile') else 'n'}
    for k in ('placeholder','pattern','title','rows','cols'):p['add_'+k]=f.get(k,'')
    if typ=='checkbox':p.update(add_checked_value=f['7'],add_checked_default=f.get('8','n'),add_checkbox_label=f.get('checkbox_label',0))
    if typ in ('select','radio'):
        options=f.get('7')
        if not isinstance(options,list) or any(not isinstance(v,str) or v.count('|')!=1 or '\n' in v or '\r' in v for v in options):raise Unsupported('Unsupported choice definition')
        stream=io.StringIO();csv.writer(stream,lineterminator='').writerow(options);p['add_dropdown_value' if typ=='select' else 'add_radio_value']=stream.getvalue()
    return p

class NormalMemberClient(http.NormalMarkdownClient):
    fieldurl='/wp-admin/options-general.php?page=wpmem-settings&tab=fields'
    settingsurl='/wp-admin/options-general.php?page=wpmem-settings'
    def form(self,url,identity):
        form=Form(self.request(url)[0].decode(),identity)
        if not form.action:form.action=url
        return form
    def submit(self,form,payload):return self.request(form.action or self.settingsurl,payload)[0].decode()
    def save_field(self,field):
        f=fdict(field);key=f['2'];payload=field_input(f)
        url=self.fieldurl+'&mode=edit&field='+urllib.parse.quote(key)
        try:
            form=self.form(url,'editfieldform');mode='edit'
            if not form.values.get('add_type'):raise Unsupported('Field does not exist')
        except Unsupported:
            form=Form(self.request(self.fieldurl,{'add_field':'true'})[0].decode(),'addfieldform');mode='add'
        if mode=='edit' and form.values.get('add_type')!=f['3']:raise Unsupported('Existing field type differs; no replacement or private correction')
        if mode=='edit':
            unchanged=True;fixed=[]
            for name,value in payload.items():
                if name=='add_order_id':continue
                if name in ('add_display','add_profile','add_required') and form.controls.get(name,{}).get('type')=='hidden':
                    fixed.append(name);continue
                if name in ('add_display','add_profile','add_required','add_checked_default'):
                    unchanged &= (form.values.get(name)=='y')==(value=='y')
                elif name in ('add_rows','add_cols') and not value:continue
                else:unchanged &= str(form.values.get(name,''))==str(value)
            if unchanged:return {'key':key,'mode':'prepared-definition-retained','fixed_controls':fixed,'order':'existing order maintained'}
            if any(name in fixed and (form.values.get(name)=='y')!=(payload[name]=='y') for name in fixed):raise Unsupported('Editable definition differs but source also needs a non-editable native flag; prepared definition retained')
        values=form.values.copy();values.update(payload);values['wpmem_admin_a']=mode+'_field';self.submit(form,values)
        actual=self.form(url,'editfieldform').values
        for key,value in payload.items():
            if key=='add_order_id':continue # existing field order has a separate normal sortable UI
            if key in ('add_display','add_profile','add_required','add_checked_default'):
                if (actual.get(key)=='y')!=(value=='y'):raise Unsupported('Normal field save changed flag: '+key)
            elif key in ('add_rows','add_cols') and not value:continue
            elif str(actual.get(key,''))!=str(value):raise Unsupported('Normal field save differs: '+key)
        return {'key':f['2'],'mode':mode,'order':'not asserted; existing order maintained'}
    def save_settings(self,settings,page_map):
        form=self.form(self.settingsurl,'updatesettings');p=form.values.copy();s=settings['wpmembers_settings']
        # These controls change account eligibility. Do not create a new policy as a side effect.
        for key,control in [('mod_reg','wpmem_settings_moderate'),('act_link','wpmem_settings_act_link'),('enable_products','wpmem_settings_products')]:
            if int(s.get(key,0))!=int(p.get(control,0)):raise Unsupported('Prepare matching account policy first: '+key)
        expected={}
        for group in ('block','show_excerpt','show_login','show_reg'):
            for typ,v in s.get(group,{}).items():
                name='wpmem_'+group+'_'+typ
                if name not in form.controls:raise Unsupported('Destination post type setting absent: '+name)
                if str(v) not in ('0','1'):raise Unsupported('Unsupported visibility flag')
                if int(v):p[name]='1'
                else:p.pop(name,None)
                expected[name]=str(v)
        for typ,values in s.get('autoex',{}).items():
            key='wpmem_autoex_'+typ
            if key not in form.controls:raise Unsupported('Destination excerpt setting absent')
            if int(values.get('enabled',0)):p[key]='1'
            else:p.pop(key,None)
            for suffix,k in [('_len','length'),('_text','text')]:
                p[key+suffix]=str(values.get(k,''))
                if int(values.get('enabled',0)):expected[key+suffix]=p[key+suffix]
            expected[key]=str(int(values.get('enabled',0)))
        for key,control in [('profile','wpmem_settings_mspage'),('register','wpmem_settings_regpage'),('login','wpmem_settings_logpage')]:
            old=s.get('user_pages',{}).get(key,0)
            if old and str(old) not in page_map:raise Unsupported('Missing prepared page mapping: '+key)
            p[control]=str(page_map[str(old)]) if old else '';expected[control]=p[control]
        self.submit(form,p);after=self.form(self.settingsurl,'updatesettings').values
        for key,value in expected.items():
            if after.get(key,'0' if value in ('0','1') else '')!=value:raise Unsupported('Normal settings save differs: '+key)
        changed=[k for k,v in form.values.items() if k not in expected and k not in ('_wpnonce','_wp_http_referer') and after.get(k)!=v]
        return {'controls':expected,'other_prepared_controls_preserved':not changed,'other_changed_controls':changed}
    def restriction(self,post_id,kind,value):
        if value=='2':raise Unsupported('Hidden mode remains unverified; content is not published')
        endpoint='pages' if kind=='page' else 'posts';saved=self.rest(endpoint+'/'+str(post_id)+'?context=edit')
        url='/wp-admin/post.php?post='+str(post_id)+'&action=edit';markup=self.request(url)[0].decode();fields=http.Fields(markup).values
        if block_control(markup)==value:return
        if saved['status'] not in ('draft','private'):raise Unsupported('Prepare unpublished destination content before setting access')
        if 'wpmem_block_meta_nonce' not in fields:raise Unsupported('Normal restriction control missing')
        p={'action':'editpost','post_ID':post_id,'post_type':kind,'_wpnonce':fields['_wpnonce'],'wpmem_block_meta_nonce':fields['wpmem_block_meta_nonce'],'wpmem_block':value or '0','post_title':saved['title']['raw'],'content':saved['content']['raw'],'post_status':saved['status'],'original_post_status':saved['status'],'user_ID':self.me['id']}
        self.request('/wp-admin/post.php',p)
        after=self.request(url)[0].decode()
        if block_control(after)!=(value or '0'):raise Unsupported('Normal restriction save differs')
    def create_member(self,item,new_password=None):
        u=item['user'];meta=item['meta'];form=self.form('/wp-admin/user-new.php','createuser');p=form.values.copy()
        if any(k in meta for k in ('active','_wpmem_user_confirmed','_wpmem_activation_confirm')):raise Unsupported('Approval/confirmation state requires a separately verified normal operation; account not created')
        if any(len(v)!=1 or not isinstance(v[0],str) for v in meta.values()):raise Unsupported('Unsupported member value shape; account not created')
        if new_password is None:new_password=form.controls.get('pass1',{}).get('data-pw') or form.values.get('pass1')
        if not isinstance(new_password,str) or len(new_password)<12:raise Unsupported('Normal new-account password control unavailable; no saved hash substitution')
        for identity in (u['user_login'],u['user_email']):
            existing=self.rest('users?context=edit&search='+urllib.parse.quote(identity))
            if any(x.get('username')==u['user_login'] or x.get('email')==u['user_email'] for x in existing):raise Unsupported('Destination account already exists; not adopted or changed')
        # Use the ordinary form's generated credential; never import saved hashes or journal passwords.
        p.update(user_login=u['user_login'],email=u['user_email'],url=u.get('user_url',''),role='subscriber',pass1=new_password,pass2=new_password,pw_weak='on');p.pop('send_user_notification',None)
        for key in ('first_name','last_name'):
            if key in meta:p[key]=meta[key][0]
        response=self.submit(form,p)
        candidates=self.rest('users?context=edit&search='+urllib.parse.quote(u['user_login']))
        ids=[x['id'] for x in candidates if x.get('username')==u['user_login'] and x.get('email')==u['user_email']]
        if len(ids)!=1:
            notices=re.findall(r'<div[^>]*(?:id="message"|class="[^"]*(?:error|notice)[^"]*")[^>]*>(.*?)</div>',response,re.S)
            detail=html.unescape(re.sub('<[^>]+>',' ',' '.join(notices)))[:600]
            raise Unsupported('Normal account creation not confirmed: '+detail)
        uid=ids[0]
        try:self.save_profile(uid,item)
        except Unsupported as e:raise Unsupported('Created account '+str(uid)+'; profile incomplete: '+str(e)+'; no private correction or automatic retry') from e
        return uid
    def save_profile(self,uid,item):
        form=self.form('/wp-admin/user-edit.php?user_id='+str(uid),'your-profile');p=form.values.copy();u=item['user']
        expected={'email':u['user_email'],'nickname':item['meta'].get('nickname',[u['user_login']])[0],'display_name':u['display_name'],'url':u.get('user_url','')}
        for key,values in item['meta'].items():
            if key in ('active','_wpmem_user_confirmed','_wpmem_activation_confirm'):raise Unsupported('Approval/confirmation needs a separate ordinary operation; not inferred')
            if len(values)!=1 or not isinstance(values[0],str) or key not in form.controls:raise Unsupported('Unsupported member field value or missing normal control: '+key)
            expected[key]=values[0]
        p.update(expected);p.update(action='update',user_id=uid,role='subscriber',pass1='',pass2='')
        self.submit(form,p);after=self.form('/wp-admin/user-edit.php?user_id='+str(uid),'your-profile').values
        for key,value in expected.items():
            if after.get(key,'')!=value:raise Unsupported('Normal profile save differs: '+key)
    def rebuild(self,plan,page_map,journal,new_passwords=None,password_reset=False):
        if plan['schema']!='owr-normal-members-registration-1' or plan['source_url'].rstrip('/')==self.url:raise Unsupported('Invalid source/destination')
        plugin=self.rest('plugins/wp-members/wp-members')
        if plugin.get('version')!=plan['version'] or plugin.get('status')!='active':raise Unsupported('Prepare the recorded WP-Members version before registration')
        state={'state':'planning','fields':[],'users':{},'restrictions':{},'held':dict(plan['held']) if plan['held'] else {},'credential_policy':'Passwords are not restored. Use the standard WordPress password reset process.','password_reset_required':[]}
        path=Path(journal)
        with path.open('x',encoding='utf-8') as f:json.dump(state,f)
        def record():path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            state['settings']=self.save_settings(plan['settings'],page_map);record()
            for f in plan['settings']['wpmembers_fields']:
                try:state['fields'].append(self.save_field(f))
                except Unsupported as e:state['held']['field:'+fdict(f)['2']]=str(e)
                record()
            for item in plan['restrictions']:
                old=str(item['origin_id'])
                if old not in page_map:state['held']['restriction:'+old]='Missing prepared page';continue
                try:self.restriction(page_map[old],item['type'],item['value']);state['restrictions'][old]=page_map[old]
                except Unsupported as e:state['held']['restriction:'+old]=str(e)
                record()
            for item in plan['users']:
                old=item['origin_id']
                if not password_reset and (not new_passwords or old not in new_passwords):state['held']['user:'+old]=item['credential'];record();continue
                if any(k.startswith('field:') for k in state['held']):state['held']['user:'+old]='Unresolved field definitions';record();continue
                try:
                    state['users'][old]=self.create_member(item,(new_passwords or {}).get(old))
                    if password_reset:state['password_reset_required'].append(old)
                except Unsupported as e:state['held']['user:'+old]=str(e)
                record()
            state['state']='completed_with_holds' if state['held'] else 'completed';record();return state
        except Exception as e:state['state']='failed';state['error']=str(e);record();raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('plan','url','username','page-map','journal'):p.add_argument('--'+k,required=True)
    p.add_argument('--isolated',action='store_true');p.add_argument('--password-reset',action='store_true',help='Create new accounts using WordPress-generated credentials; members must use standard password reset. This tool does not request reset emails; configured notification hooks still apply.');a=p.parse_args()
    c=NormalMemberClient(a.url,a.username,getpass.getpass('Administrator password: '),a.isolated)
    print(json.dumps(c.rebuild(json.loads(Path(a.plan).read_text(encoding='utf-8-sig')),json.loads(Path(a.page_map).read_text(encoding='utf-8-sig')),a.journal,password_reset=a.password_reset),ensure_ascii=False,indent=2))
