"""Isolated normal-registration coordinator. Input is only the saved bundle.

Maps are populated from actual API/form results, never supplied by a fixture.
No plugin initialization, DB patching, or guessed missing materials.
"""
import base64, importlib.util, json, re, urllib.parse
from pathlib import Path

def module(name):
    spec=importlib.util.spec_from_file_location('kit_'+name,Path(__file__).with_name('reconstruct-'+name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Reconstruction:
    def __init__(self,clients,normal_api,journal):
        self.c=clients;self.api=normal_api;self.path=Path(journal)
        self.s={'state':'planning','posts':{},'documents':{},'tables':{},'forms':{},'authors':{},'receipts':{},'terms':{},'menus':{},'urls':{},'held':{},'operations':[],'result_references':{}}
        with self.path.open('x') as f:json.dump(self.s,f)
    def record(self):self.path.write_text(json.dumps(self.s,ensure_ascii=False,indent=2))
    def call(self,label,fn):
        self.s['attempting']=label;self.record()
        r=fn();self.s['operations'].append(label);self.s.pop('attempting');self.record();return r
    def mapped(self,kind,old):
        if not int(old):return 0
        if str(old) not in self.s[kind]:raise ValueError('Unregistered '+kind+' reference '+str(old))
        return self.s[kind][str(old)]
    def content(self,p,old):
        identities={'post:'+str(k):v for kind in ['posts','documents','forms'] for k,v in self.s[kind].items()}
        identities.update({'table:'+str(k):v for k,v in self.s['tables'].items()});identities.update(self.s['result_references'])
        material=p['initial_references']['contents'].get(str(old))
        if not material:raise ValueError('Missing source-time initial content contract')
        return self.api({'operation':'prepare-initial-content','material':material,'identities':identities})['arguments']
    def run(self,p,register_authors):
        self.source=p['source'];core=self.c['markdown'];posts={str(x['ID']):x for x in p['posts']};meta=p['meta']
        self.s['urls'][self.source.rstrip('/')+'/wp-admin/']=core.url.rstrip('/')+'/wp-admin/'
        try:
            if p['held']:raise ValueError('Material holds: '+str(p['held']))
            self.s['authors']=self.call('authors',register_authors);self.record()
            terms={str(t['term_id']):t for t in p['terms']};tax={str(t['term_taxonomy_id']):t for t in p['taxonomies']}
            for t in p['taxonomies']:
                if t['taxonomy'] not in ('category','post_tag','nav_menu'):continue
                term=terms[str(t['term_id'])];key=t['taxonomy']+':'+str(t['term_id'])
                if t['taxonomy']=='nav_menu':
                    self.s['menus'][str(t['term_id'])]=self.call('menu:'+key,lambda:self.api({'operation':'menu','name':term['name']}))['id'];continue
                endpoint='categories' if t['taxonomy']=='category' else 'tags'
                if int(t['parent']):raise ValueError('Hierarchical term ordering not yet implemented')
                found=core.rest(endpoint+'?slug='+urllib.parse.quote(term['slug']))
                if found:
                    if len(found)!=1 or found[0]['name']!=term['name']:raise ValueError('Taxonomy conflict')
                    self.s['terms'][key]=found[0]['id']
                else:self.s['terms'][key]=self.call('term:'+key,lambda:core.rest(endpoint,{'name':term['name'],'slug':term['slug'],'description':t['description']}))['id']
                self.record()
            # Allocate ordinary page identities first, still unpublished.
            for old,x in posts.items():
                if x['post_type'] not in ('post','page'):continue
                endpoint='pages' if x['post_type']=='page' else 'posts'
                r=self.call('shell:'+old,lambda:core.rest(endpoint,{'title':x['post_title'],'slug':x['post_name'],'status':'draft','author':self.mapped('authors',x['post_author'])}))
                self.s['posts'][old]=r['id'];self.s['urls'][p['source'].rstrip('/')+'/?'+('page_id=' if endpoint=='pages' else 'p=')+old]=r['link'];self.record()
            for old,x in posts.items():
                if x['post_type']!='attachment':continue
                relative=meta[old].get('_wp_attached_file','');path='uploads/'+relative
                if p['media_access'].get(path,{}).get('state')!='public':raise ValueError('File needs a supported private delivery path: '+old)
                raw=base64.b64decode(p['files'][path]);filename=Path(relative).name
                r=self.call('image:'+old,lambda:json.loads(core.request('/?rest_route=/wp/v2/media',raw,{'X-WP-Nonce':core.nonce,'Content-Type':x['post_mime_type'],'Content-Disposition':'attachment; filename="'+filename+'"'})[0]))
                self.s['posts'][old]=r['id'];self.s['urls'][p['uploads'].rstrip('/')+'/'+relative]=r['source_url']
                self.s['result_references']['image-url:full:'+old]=r['source_url']
                for kind,details in r.get('media_details',{}).get('sizes',{}).items():
                    if 'source_url' in details:self.s['result_references']['image-url:'+kind+':'+old]=details['source_url']
                source_refs=p['initial_references']['media'].get(old,{})
                if not source_refs:raise ValueError('Missing source baseline image reference contract: '+old)
                for kind,source_value in source_refs.items():
                    key=kind+':'+old
                    if key not in self.s['result_references']:raise ValueError('Normal upload lacks baseline image kind: '+kind)
                    self.s['urls'][source_value]=self.s['result_references'][key]
                self.record()
                self.call('image-fields:'+old,lambda:core.rest('media/'+str(r['id']),{'title':x['post_title'],'alt_text':meta[old].get('_wp_attachment_image_alt',''),'author':self.mapped('authors',x['post_author'])}))
            for x in p['tables']['tables']:
                self.s['tables'][str(x['origin_id'])]=self.call('table:'+str(x['origin_id']),lambda:self.c['tablepress'].import_table(x['table']));self.record()
                self.c['tablepress'].verify(self.s['tables'][str(x['origin_id'])],x['table'])
            for x in p['forms']['forms']:
                payload=module('contact-form').validate(x['input'])
                r=self.call('form:'+str(x['origin_id']),lambda:self.c['contact-form'].cf7(payload={**payload,'context':'save'}))
                if not r.get('id'):raise ValueError('Normal CF7 registration did not return an ID')
                self.s['forms'][str(x['origin_id'])]=r['id']
                matches=[f for f in self.c['contact-form'].cf7() if f['id']==r['id']]
                if len(matches)!=1 or not matches[0].get('hash'):raise ValueError('Normal form hash missing')
                self.s['result_references']['cf7-hash:'+str(x['origin_id'])]=matches[0]['hash'];self.record()
                self.c['contact-form'].verify(r['id'],payload)
            for old,x in posts.items():
                if x['post_type']!='ozmd_document':continue
                m=meta[old];raw=base64.b64decode(p['files']['markdown/'+old+'.md'])
                raw=self.content(p,old)['source_text'].encode('utf-8')
                if not m.get('_ozmd_original_filename'):raise ValueError('Missing original Markdown filename')
                new=self.call('document:'+old,lambda:core.import_document(raw,m['_ozmd_original_filename']));self.s['documents'][old]=new;self.record()
                item={'title':x['post_title'],'slug':x['post_name'],'status':x['post_status'],'password':x['post_password'],'date':x['post_date'],'author_destination':self.mapped('authors',x['post_author'])}
                self.call('document-save:'+old,lambda:core.save(new,raw,item))
            # ACF's ordinary editor requires unpublished owners during this stage.
            ar=self.call('acf',lambda:self.c['acf'].rebuild(p['acf'],self.s['posts'],str(self.path)+'.acf'))
            if ar['held']:raise ValueError('Normal ACF registration holds: '+str(ar['held']))
            # Only saved login/profile/register pages are published before normal selectors.
            member=p['members'];userpages=member['settings']['wpmembers_settings'].get('user_pages',{})
            early=set(str(i) for i in userpages.values() if i)
            restrictions={str(x['origin_id']):x for x in member['restrictions']}
            for old in early:
                x=posts[old]
                if restrictions[old]['value']!='0':raise ValueError('Member entry page is restricted; no alternative page invented')
                if x['post_content'] not in ('[wpmem_form login]','[wpmem_profile]'):raise ValueError('Member entry page has additional dependencies')
                self.call('entry-page:'+old,lambda:core.rest('pages/'+str(self.mapped('posts',old)),{'content':self.content(p,old)['content'],'status':x['post_status']}))
            mr=self.call('member-settings',lambda:self.c['members'].rebuild(member,self.s['posts'],str(self.path)+'.members',password_reset=True))
            if mr['held']:raise ValueError('Normal member registration holds: '+str(mr['held']))
            for old,new in mr['users'].items():
                if old in self.s['authors']:raise ValueError('Member/author identity already allocated')
                self.s['authors'][old]=new
            self.record()
            for old,x in posts.items():
                if x['post_type'] not in ('post','page') or old in early:continue
                endpoint='pages' if x['post_type']=='page' else 'posts'
                data={'content':self.content(p,old)['content'],'excerpt':self.content(p,old)['excerpt'],'parent':self.mapped('posts',x['post_parent']),'author':self.mapped('authors',x['post_author']),'password':x['post_password'],'comment_status':x['comment_status'],'ping_status':x['ping_status'],'status':x['post_status']}
                data.update(date=x['post_date'].replace(' ','T'),date_gmt=x['post_date_gmt'].replace(' ','T'))
                for taxonomy,field in [('category','categories'),('post_tag','tags')]:
                    assigned=[tax[str(r['term_taxonomy_id'])] for r in p['relationships'] if str(r['object_id'])==old and tax[str(r['term_taxonomy_id'])]['taxonomy']==taxonomy]
                    if assigned:data[field]=[self.s['terms'][taxonomy+':'+str(t['term_id'])] for t in assigned]
                if meta.get(old,{}).get('_thumbnail_id'):data['featured_media']=self.mapped('posts',meta[old]['_thumbnail_id'])
                self.call('publish:'+old,lambda:core.rest(endpoint+'/'+str(self.mapped('posts',old)),data))
            for old,x in posts.items():
                if x['post_type']!='nav_menu_item':continue
                m=meta[old]
                if m.get('_menu_item_type')!='post_type' or int(m.get('_menu_item_menu_item_parent',0)):raise ValueError('Menu operation requires an unsupported relation')
                assigned=[tax[str(r['term_taxonomy_id'])] for r in p['relationships'] if str(r['object_id'])==old and tax[str(r['term_taxonomy_id'])]['taxonomy']=='nav_menu']
                if len(assigned)!=1:raise ValueError('Menu ownership missing')
                item={'menu-item-object-id':self.mapped('posts',m['_menu_item_object_id']),'menu-item-object':m['_menu_item_object'],'menu-item-type':'post_type','menu-item-status':'publish','menu-item-title':x['post_title'],'menu-item-position':int(x['menu_order'])}
                self.s['posts'][old]=self.call('menu-item:'+old,lambda:self.api({'operation':'menu-item','menu':self.mapped('menus',assigned[0]['term_id']),'item':item}))['id'];self.record()
            for e in p['receipts']:
                fid=self.mapped('forms',e['input']['form_id']);old=str(e['result']['id'])
                r=self.call('receipt:'+old,lambda:self.api({'operation':'receipt','entry':e,'source':p['source'],'form':fid,'journal':'/tmp/construction-receipt-'+old+'.json'}))
                if r['state']!='completed':raise ValueError('Receipt registration incomplete: '+str(r))
                self.s['receipts'].update(r['receipts']);self.record()
            # After the baseline, follow the SOURCE-TIME contract in sequence.
            # No route/content parsing or type-based reordering at reconstruction.
            identities={'post:'+str(old):new for old,new in self.s['posts'].items()}
            identities.update({'user:'+str(old):new for old,new in self.s['authors'].items()})
            identities.update(self.s['terms'])
            identities.update({'post:'+str(old):new for kind in ['documents','forms','receipts'] for old,new in self.s[kind].items()})
            identities.update({'table:'+str(old):new for old,new in self.s['tables'].items()})
            identities.update(self.s['result_references'])
            for old,new in self.s['forms'].items():
                forms=self.c['contact-form'].cf7();matches=[x for x in forms if x['id']==new]
                if len(matches)!=1 or not matches[0].get('hash'):raise ValueError('Baseline form result lacks public hash')
                identities['cf7-hash:'+old]=matches[0]['hash']
            dispatcher=module('operations');modules={k:module(k) for k in ['markdown','tablepress','contact-form','members','acf']}
            def receipt(e,form):
                r=self.api({'operation':'receipt','entry':e,'source':p['source'],'form':form,'journal':'/tmp/receipt-follow.json'})
                if r['state']!='completed' or r['failed'] or r['held']:raise ValueError('Recorded receipt registration incomplete')
                return next(iter(r['receipts'].values()))
            completed=[];through=p['anchor']['through']
            for e in p['tail']:
                q=self.api({'operation':'prepare-operation','entry':e,'through':through,'identities':identities})
                if not q.get('skip'):
                    returned=self.call('recorded:'+str(e['sequence']),lambda:dispatcher.dispatch(q,e,self.c,modules,receipt))
                    identities=self.api({'operation':'accept-operation','entry':e,'returned':returned,'identities':identities})
                through=e['sequence'];completed.append(through)
                self.s['follow']={'identities':identities,'completed':completed};self.record()
            self.s['state']='registered_pending_remaining_scope_review';self.record();return self.s
        except Exception as e:
            self.s['state']='held';self.s['error']=str(e);self.record();return self.s
