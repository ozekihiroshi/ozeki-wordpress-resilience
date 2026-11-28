"""Development-only TablePress reconstruction through normal authenticated HTTP forms.
No private TablePress calls, DB writes, cache repair, or old ID installation.
"""
import argparse, copy, getpass, hashlib, html, importlib.util, json, re, urllib.parse
from pathlib import Path

_spec=importlib.util.spec_from_file_location('normal_wp_http',Path(__file__).with_name('reconstruct-markdown.py'))
_http=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_http)
Unsupported=_http.Unsupported

BOOLS={'alternating_row_colors','row_hover','print_name','print_description','use_datatables','datatables_sort','datatables_filter','datatables_paginate','datatables_lengthchange','datatables_info','datatables_scrollx'}
INTS={'table_head','table_foot','datatables_paginate_entries'}
TEXTS={'print_name_position','print_description_position','extra_css_classes'}
EMBED=re.compile(r'\[table\s+id=(?:"([A-Za-z0-9_-]+)"|\'([A-Za-z0-9_-]+)\'|([A-Za-z0-9_-]+))\s*/?\]')

def ref(m):return next(x for x in m.groups() if x is not None)

def import_input(table):
    """Validate only; do not sanitize values into a superficially successful import."""
    t=copy.deepcopy(table)
    if set(t)!={'name','description','data','options','visibility'}:raise Unsupported('Incomplete table import material')
    rows=t['data']
    if not isinstance(rows,list) or not rows or not isinstance(rows[0],list) or not rows[0]:raise Unsupported('Empty or invalid table dimensions')
    cols=len(rows[0])
    if any(not isinstance(row,list) or len(row)!=cols for row in rows):raise Unsupported('Nonrectangular table')
    for value in [t['name'],t['description']]+[cell for row in rows for cell in row]:
        if not isinstance(value,str):raise Unsupported('Cell/name/description is not a string; no coercion')
        # This first bounded implementation handles plain information, not instructions.
        # Ordinary import alone is not authority to execute archived HTML/shortcodes.
        decoded=html.unescape(value)
        if re.search(r'<\s*[!/?A-Za-z]|\[/?[A-Za-z_][\w-]*(?:\s|\])',decoded):raise Unsupported('HTML or shortcode-like content requires an explicit application decision')
    v=t['visibility']
    if not isinstance(v,dict) or set(v)!={'rows','columns'} or len(v['rows'])!=len(rows) or len(v['columns'])!=cols or any(type(x)!=int or x not in (0,1) for x in v['rows']+v['columns']):raise Unsupported('Visibility dimensions or values differ')
    opts=t['options']
    if not isinstance(opts,dict):raise Unsupported('Options missing')
    for key,value in opts.items():
        if key=='last_editor':continue  # destination user is assigned by normal TablePress registration
        if key=='datatables_custom_commands':
            if value!='':raise Unsupported('Archived executable custom commands are not imported')
        elif key in BOOLS:
            if type(value)!=bool:raise Unsupported('Invalid boolean option: '+key)
        elif key in INTS:
            if type(value)!=int or value<0:raise Unsupported('Invalid integer option: '+key)
        elif key in TEXTS:
            if not isinstance(value,str):raise Unsupported('Invalid text option: '+key)
            if key.endswith('_position') and value not in ('above','below'):raise Unsupported('Unknown position')
            if key=='extra_css_classes' and not re.fullmatch(r'[A-Za-z0-9_\- ]*',value):raise Unsupported('Unsupported CSS class value')
        else:raise Unsupported('Unknown table option: '+key)
    opts.pop('last_editor',None)
    return t

def page_content(raw,mapping):
    # Exact known shortcode only; no entity-wide decoding or enabling arbitrary commands.
    rest=EMBED.sub('',raw)
    if re.search(r'\[/?[A-Za-z_]|&#(?:0*91|x0*5b);|&lbrack;',rest,re.I):raise Unsupported('Unknown or escaped embedding requires review')
    # Bounded ordinary paragraph/shortcode page. No arbitrary HTML or block attributes.
    simple=re.sub(r'<!-- /?wp:(?:paragraph|heading|shortcode) -->','',rest)
    simple=re.sub(r'</?(?:p|h[1-6]|strong|em)>|<br\s*/?>','',simple)
    if '<' in simple or re.search(r'https?://',simple):raise Unsupported('Additional page markup/references need the core registration map')
    for m in EMBED.finditer(raw):
        if ref(m) not in mapping:raise Unsupported('Referenced table was not registered: '+ref(m))
    return EMBED.sub(lambda m:'[table id="'+mapping[ref(m)]+'" /]',raw)

class NormalTablePressClient(_http.NormalMarkdownClient):
    def import_table(self,table):
        markup=self.request('/wp-admin/admin.php?page=tablepress&action=import')[0].decode()
        nonce=_http.Fields(markup).values['_wpnonce']
        data={'action':'tablepress_import','_wpnonce':nonce,'import[source]':'form-field','import[form-field]':json.dumps(table,ensure_ascii=False),'import[type]':'add'}
        # The server's ordinary success redirect identifies the newly allocated table ID.
        response=self.op.open(self.url+'/wp-admin/admin-post.php',urllib.parse.urlencode(data).encode(),timeout=30)
        response.read();q=urllib.parse.parse_qs(urllib.parse.urlsplit(response.url).query)
        if q.get('message')!=['success_import'] or len(q.get('table_id',[]))!=1:raise Unsupported('Normal import did not identify one table; do not retry blindly')
        return q['table_id'][0]

    def export_table(self,tid):
        markup=self.request('/wp-admin/admin.php?page=tablepress&action=export&table_id='+urllib.parse.quote(tid))[0].decode()
        nonce=_http.Fields(markup).values['_wpnonce']
        body=self.request('/wp-admin/admin-post.php',{'action':'tablepress_export','_wpnonce':nonce,'export[tables_list]':tid,'export[format]':'json','export[csv_delimiter]':',','export[zip_file]':'false'})[0]
        return json.loads(body)

    def save_table(self,tid,table):
        markup=self.request('/wp-admin/admin.php?page=tablepress&action=edit&table_id='+urllib.parse.quote(tid))[0].decode()
        nonce=re.search(r"edit_table:\s*'([^']+)'",markup)
        if not nonce:raise Unsupported('Normal editor nonce missing')
        data={'action':'tablepress_save_table','_ajax_nonce':nonce[1],'tablepress[id]':tid,'tablepress[number][rows]':len(table['data']),'tablepress[number][columns]':len(table['data'][0])}
        for k in ['name','description']:data['tablepress['+k+']']=table[k]
        for k in ['data','options','visibility']:data['tablepress['+k+']']=json.dumps(table[k],ensure_ascii=False)
        r=json.loads(self.request('/wp-admin/admin-ajax.php',data)[0])
        if not r.get('success'):raise Unsupported('Normal editor save failed: '+str(r))
        self.verify(tid,table)

    def verify(self,tid,expected):
        actual=self.export_table(tid)
        for k in ['name','description','data','visibility']:
            if actual[k]!=expected[k]:raise Unsupported('Normal export differs: '+k+'; no repair attempted')
        for k,v in expected['options'].items():
            if actual['options'].get(k)!=v:raise Unsupported('Normal export option differs: '+k+'; no repair attempted')
        return actual

    def rebuild(self,plan,journal_path,author_map):
        if plan['schema']!='owr-normal-tablepress-registration-1' or plan['source_url'].rstrip('/')==self.url:raise Unsupported('Invalid plan or source/destination collision')
        journal=Path(journal_path)
        state={'state':'planning','through':plan['through'],'plan_sha256':hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),'tables':{},'pages':{},'held':dict(plan['held']) if plan['held'] else {},'excluded':plan['excluded'],'destination_owned':plan['destination_owned']}
        with journal.open('x',encoding='utf-8') as f:json.dump(state,f)
        def record():journal.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            eligible=[]
            for item in plan['tables']:
                try:eligible.append((item['origin_id'],import_input(item['table'])))
                except Unsupported as e:state['held']['table:'+item['origin_id']]=str(e)
            state['state']='registering';record()
            for old,t in eligible:
                new=self.import_table(t);state['tables'][old]=new;record()
                self.verify(new,t)  # inspect before linking a public page
                self.save_table(new,t)
            for p in plan['pages']:
                try:
                    if not author_map.get(str(p['author_origin'])):raise Unsupported('Explicit destination author mapping required')
                    content=page_content(p['content'],state['tables'])
                except Unsupported as e:state['held']['page:'+str(p['origin_id'])]=str(e);record();continue
                endpoint='pages' if p['type']=='page' else 'posts'
                payload={k:p[k] for k in ['title','slug','status','password','excerpt','comment_status','ping_status']}
                payload.update(content=content,date_gmt=p['date_gmt'].replace(' ','T'),author=author_map[str(p['author_origin'])])
                new=self.rest(endpoint,payload)['id'];state['pages'][str(p['origin_id'])]=new;record()
                if self.rest(endpoint+'/'+str(new)+'?context=edit')['content']['raw']!=content:raise Unsupported('Normal page registration differs; no repair attempted')
            state['state']='completed';record();return state
        except Exception as e:
            state['state']='failed';state['error']=str(e);record();raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','url','username','journal','author-map']:p.add_argument('--'+k,required=True)
    p.add_argument('--isolated',action='store_true');a=p.parse_args()
    c=NormalTablePressClient(a.url,a.username,getpass.getpass('WordPress password: '),a.isolated)
    print(json.dumps(c.rebuild(json.loads(Path(a.plan).read_text(encoding='utf-8-sig')),a.journal,json.loads(Path(a.author_map).read_text(encoding='utf-8-sig'))),ensure_ascii=False,indent=2))
