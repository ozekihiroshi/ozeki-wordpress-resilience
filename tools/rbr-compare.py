"""Observe actual DB and served HTML. Q is only the final comparison oracle."""
import hashlib, json
from html.parser import HTMLParser
from urllib.parse import urlsplit, parse_qs

class View(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.main=False;self.globalnav=False;self.related=False;self.nodes=[];self.global_links=[];self.text=None;self.title='';self.h1=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='main':self.main=True
        if tag=='h1':self.h1=True
        if tag=='nav':
            if a.get('id')=='global':self.globalnav=True
            elif self.main and a.get('class')=='related':self.related=True
        if tag=='p' and self.main:self.text=['paragraph','',None]
        if tag=='a' and (self.main or self.globalnav):self.text=['global' if self.globalnav else ('navigation' if self.related else 'link'),'',a.get('href')]
        if tag=='img' and self.main:self.nodes.append(('image',a.get('alt'),a.get('src')))
        if tag in ('script','iframe','form','object'):raise ValueError('Unexpected active element')
    def handle_data(self,data):
        if self.h1:self.title+=data
        if self.text is not None:self.text[1]+=data
    def handle_endtag(self,tag):
        if tag=='h1':self.h1=False
        if tag in ('p','a') and self.text is not None:
            (self.global_links if self.text[0]=='global' else self.nodes).append(tuple(self.text));self.text=None
        if tag=='nav':self.related=False;self.globalnav=False
        if tag=='main':self.main=False

def compare(obs,htmls,media,q,origin):
    rows=obs['rows'];pages={x['asset_id']:x for x in rows if x['type']=='page'};images={x['asset_id']:x for x in rows if x['type']=='attachment'}
    assert len(rows)==len(pages)+len(images)==len(q['pages'])+len(q['images']), 'Unexpected scope'
    assert set(pages)==set(q['pages']) and set(images)==set(q['images']), 'Coverage'
    assert len(set(obs['map'].values()))==len(obs['map'])==len(rows), 'Non-injective map'
    assert all(obs['map'].get(x['asset_id'])==x['id'] for x in rows), 'Map not actual'
    assert not obs['active_plugins'] and obs['side_effect_attempts']==0, 'Unexpected effects/plugins'
    assert obs['run_state']=='applied', 'Incomplete application'
    byid={x['id']:k for k,x in pages.items()};byurl={x['url']:k for k,x in images.items()}
    def target(url):
        p=urlsplit(url);base=urlsplit(origin)
        assert (p.scheme,p.netloc,p.path)==(base.scheme,base.netloc,'/') and not p.fragment, 'Foreign/unresolved route'
        query=parse_qs(p.query);assert set(query)=={'page_id'} and len(query['page_id'])==1, 'Unexpected route'
        return byid[int(query['page_id'][0])]
    logical={'schema':q['schema'],'scope':q['scope'],'actual_status':'draft','pages':{},'images':{},'relations':[]}
    for asset,row in pages.items():
        assert row['status']=='draft' and row['parent']==0, 'Published or unexpected parent'
        v=View();v.feed(htmls[asset]);db=View();db.feed('<main>'+row['body']+'</main>')
        assert v.nodes==db.nodes and v.title==row['title'], 'Served/DB mismatch'
        assert 'white-space:pre-wrap' in htmls[asset], 'Whitespace rendering policy absent'
        paragraphs=[];navpos=0
        for kind,label,url in v.nodes:
            if kind=='paragraph':paragraphs.append(label);continue
            if kind=='image':
                dest=byurl[url];assert label=='', 'Nondecorative rendering'
            else:
                dest=target(url);assert label==pages[dest]['title'], 'Link label mismatch'
            logical['relations'].append({'from':asset,'to':dest,'type':kind,'position':navpos if kind=='navigation' else len(paragraphs)})
            if kind=='navigation':navpos+=1
        logical['pages'][asset]={'role':row['role'],'title':row['title'],'slug':row['slug'],'paragraphs':paragraphs}
        assert [target(x[2]) for x in v.global_links]==[obs['roles'][role] for role in ['company','services','contact']], 'Global order'
        assert all(label==pages[target(url)]['title'] for _,label,url in v.global_links), 'Global label'
    assert obs['landing']==obs['roles']['company'], 'Landing role'
    for asset,row in images.items():
        assert hashlib.sha256(media[asset]).hexdigest()==row['sha256'], 'Served image mismatch'
        assert row['caption']=='' and row['alt']=='', 'Image meaning'
        logical['images'][asset]={k:row[k] for k in ['sha256','width','height','alt']}
    sort=lambda edges:sorted(edges,key=lambda x:(x['from'],x['position'],x['type'],x['to']))
    logical['relations']=sort(logical['relations']);expected=dict(q);expected['relations']=sort(q['relations'])
    assert logical==expected, 'Observed logical state differs from Q'
    return logical
