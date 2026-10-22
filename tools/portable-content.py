"""Offline portable extraction. No site rendering, remote fetch or publication."""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit, unquote

MAX_SOURCE = 64 * 1024 * 1024
TAGS = {'p','h1','h2','h3','h4','h5','h6','ul','ol','li','strong','b','em','i','blockquote','pre','code','br','a','img'}
BLOCKS = {'core/paragraph','core/heading','core/list','core/list-item','core/quote','core/code','core/preformatted','core/image'}
ACTIVE = {'script','style','iframe','object','embed','form','svg','template'}

def digest(b): return hashlib.sha256(b).hexdigest()
def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    path.chmod(0o600)

def unique(pairs):
    obj = {}
    for k,v in pairs:
        if k in obj: raise ValueError('duplicate JSON field')
        obj[k]=v
    return obj

def load(path):
    p=Path(path)
    if p.stat().st_size > MAX_SOURCE: raise ValueError('source size limit')
    return json.loads(p.read_text(encoding='utf-8-sig'), object_pairs_hook=unique)

def identity(url):
    p=urlsplit(url)
    return (p.scheme.lower(),p.netloc.lower(),p.path or '/',p.query)

class Body(HTMLParser):
    def __init__(self, record, issue):
        super().__init__(convert_charrefs=True)
        self.record=record; self.issue=issue; self.nodes=[]; self.refs=[]; self.anchors=set(); self.suppressed=[]; self.stack=[]
    def warning(self,code,detail): self.issue(code,detail,location='body:%s:%s'%self.getpos())
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if len(a)!=len(attrs): self.warning('duplicate_attribute',tag)
        if self.suppressed:
            if tag not in {'img','br','input','hr','meta','link','embed'}: self.suppressed.append(tag)
            return
        if tag in ACTIVE:
            self.warning('active_content_excluded',tag)
            if tag!='embed': self.suppressed.append(tag)
            return
        if a.get('id'): self.nodes.append({'kind':'anchor','id':a['id']})
        if tag not in TAGS: self.warning('unsupported_html',tag)
        elif tag not in {'a','img'}: self.nodes.append({'kind':'start','tag':tag})
        if a.get('id'):
            if a['id'] in self.anchors: self.warning('duplicate_anchor',a['id'])
            self.anchors.add(a['id'])
        for key in a:
            if key not in {'id','href','src','alt','title'}: self.warning('attribute_not_converted',tag+':'+key)
        if tag in {'a','img'}:
            ref={'kind':'link' if tag=='a' else 'image','original':a.get('href' if tag=='a' else 'src',''),
                 'location':'body:%s:%s'%self.getpos()}
            if tag=='img': ref['alt']=a.get('alt','')
            self.refs.append(ref); self.nodes.append({'kind':'reference','index':len(self.refs)-1})
        if tag not in {'img','br','input','hr','meta','link','embed'}: self.stack.append(tag)
    def handle_endtag(self,tag):
        if self.suppressed:
            if self.suppressed[-1]==tag: self.suppressed.pop()
            return
        if not self.stack or self.stack[-1]!=tag: self.warning('malformed_html',tag)
        else: self.stack.pop()
        if tag in TAGS and tag not in {'img','br'}: self.nodes.append({'kind':'end','tag':tag})
    def handle_data(self,data):
        if self.suppressed: return
        if re.search(r'\[/?[A-Za-z][\w-]*(?:[\s\]/])',data): self.warning('shortcode_or_bracket_syntax',data[:160])
        if data: self.nodes.append({'kind':'text','text':data})
    def finish(self,body):
        self.feed(body);self.close()
        if self.stack or self.suppressed: self.warning('unclosed_html','unclosed elements')

def extract(source, output):
    if source.get('format')!='owr-portable-source-v1': raise ValueError('unsupported source format')
    selected=source['selected']; records=source['records']; media=source['media']
    if not selected or len(selected)>200 or any(type(x)!=int or x<1 for x in selected) or len(set(selected))!=len(selected): raise ValueError('invalid selection')
    if len(records)>200 or len(media)>2000: raise ValueError('record limit')
    ids=[x['id'] for x in records]; mids=[x['id'] for x in media]
    if any(type(x)!=int or x<1 for x in ids+mids) or len(set(ids))!=len(ids) or len(set(mids))!=len(mids): raise ValueError('duplicate/invalid ID')
    for r in records:
        if r['id'] not in selected or r.get('status')!='publish' or r.get('type') not in {'post','page'}: raise ValueError('record outside public selection')
        if len(r['body'].encode())>2097152 or urlsplit(r['url']).scheme not in {'http','https'}: raise ValueError('invalid record')
    out=Path(output)
    # Exclusive new directory; never overwrite a prior partial or completed package.
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    for name in ('raw','content','readable','media'): (out/name).mkdir(mode=0o700)
    issues=[]; relations=[]; parsers={}; image_index={}; total=0
    def issue(code,detail,page=None,location='record'):
        issues.append(dict(code=code,detail=detail,page=page,location=location))
    try:
        write(out/'manifest.json',{'format':'owr-portable-package-v1','state':'incomplete','publication_authorized':False})
        raw={**source,'media':[{k:v for k,v in m.items() if k!='base64'} for m in media]}
        write(out/'raw'/'source.json',raw)
        for x in set(selected)-set(ids): issue('selected_not_exported',str(x),x)
        for dep in source.get('dependencies',[]): issue('uncollected_dependency',dep)
        if not source.get('observation',{}).get('records_unchanged'): issue('source_changed_or_unconfirmed','source markers differ or absent')
        issue('consistency_not_atomic','Source observations are not an atomic snapshot')
        for m in media:
            if m['state']!='copied': issue('media_unavailable',m['state'],location='media:'+str(m['id'])); continue
            b=base64.b64decode(m['base64'],validate=True); total+=len(b)
            if len(b)>8388608 or total>33554432 or digest(b)!=m['sha256']: raise ValueError('image size/hash mismatch')
            ext='png' if b.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if b.startswith(b'\xff\xd8\xff') else 'bin'
            filename='media/'+str(m['id'])+'.'+ext
            (out/filename).write_bytes(b);(out/filename).chmod(0o600)
            image_index[m['id']]={k:v for k,v in m.items() if k!='base64'}
            image_index[m['id']].update(path=filename,inspection='signature_only_not_decoded_or_sanitized')
            issue('media_requires_review' if ext!='bin' else 'unsupported_media',m['name'],location='media:'+str(m['id']))
        for r in records:
            page=r['id']
            def report(code,detail,location='record',page=page): issue(code,detail,page,location)
            for block in r.get('blocks',[]):
                if block['name'] not in BLOCKS: report('unsupported_block',block['name'])
            for key in r.get('unmapped_meta_keys',[]): report('unmapped_metadata',key)
            parser=Body(r,report);parser.finish(r['body']);parsers[page]=parser
        by_url={}
        for r in records: by_url.setdefault(identity(r['url']),[]).append(r['id'])
        by_image={}
        for m in media: by_image.setdefault(identity(m['url']),[]).append(m['id'])
        def edge(page,kind,original,target=None,reason=None,**extra):
            relations.append(dict(page=page,kind=kind,original=original,target=target,state='resolved' if target is not None else 'unresolved',reason=reason,**extra))
            if reason: issue('unresolved_'+kind,reason,page,extra.get('location','record'))
        for r in records:
            page=r['id']; p=parsers[page]
            if r.get('parent'): edge(page,'parent',str(r['parent']),r['parent'] if r['parent'] in ids else None,None if r['parent'] in ids else 'outside_selection')
            if r.get('featured'): edge(page,'featured',str(r['featured']),r['featured'] if r['featured'] in image_index else None,None if r['featured'] in image_index else 'missing_media')
            for ref in p.refs:
                uri=urljoin(r['url'],ref['original']);u=urlsplit(uri);target=None;reason=None
                if not ref['original']: reason='empty_reference'
                elif u.scheme not in {'http','https'} or u.username or u.password: reason='scheme_or_credentials_requires_review'
                elif ref['kind']=='image':
                    candidates=by_image.get(identity(uri),[])
                    if len(candidates)==1 and candidates[0] in image_index: target=candidates[0]
                    else: reason='missing_or_ambiguous_media'
                else:
                    candidates=by_url.get(identity(uri),[])
                    if len(candidates)==1:
                        target=candidates[0]
                        if u.fragment and unquote(u.fragment) not in parsers[target].anchors: target=None;reason='missing_anchor'
                    else: reason='external_or_unmapped_url' if not candidates else 'ambiguous_url'
                edge(page,ref['kind'],ref['original'],target,reason,location=ref['location'],fragment=u.fragment)
            write(out/'content'/f'{page}.json',{k:v for k,v in r.items() if k!='body'}|{'nodes':p.nodes,'references':p.refs,'anchors':sorted(p.anchors),'conversion':'partial' if any(i['page']==page for i in issues) else 'supported_subset'})
            # Plain text is deliberately inert. No Markdown/HTML rendering in this increment.
            text=r['title']+'\n\n'
            for node in p.nodes:
                if node['kind']=='text':text+=node['text']
                elif node['kind']=='reference':text+=' [reference '+str(node['index'])+'] '
                elif node['kind']=='end' or node.get('tag')=='br':text+='\n'
            text+='\n\nIssues and image/link mapping: see issues.json and relations.json.\n'
            (out/'readable'/f'{page}.txt').write_text(text,encoding='utf-8');(out/'readable'/f'{page}.txt').chmod(0o600)
        write(out/'media-index.json',list(image_index.values()));write(out/'relations.json',relations);write(out/'issues.json',issues)
        (out/'README.txt').write_text('Portable extraction only. Not a website or safe-to-publish package.\nRead readable/*.txt and content/*.json without WordPress. Media paths are in media-index.json. Raw sources are untrusted and must not be web-served. All issues are in issues.json. No malware-free claim.\n',encoding='utf-8')
        (out/'README.txt').chmod(0o600)
        hashes={str(f.relative_to(out)):digest(f.read_bytes()) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='manifest.json'}
        manifest=dict(format='owr-portable-package-v1',state='extracted_with_review',selected=selected,exported=ids,
            missing=sorted(set(selected)-set(ids)),counts=dict(pages=len(records),media=len(image_index),relations=len(relations),issues=len(issues)),
            observation=source.get('observation'),hashes=hashes,publication_authorized=False,static_site_generated=False)
        write(out/'manifest.json',manifest);return manifest
    except Exception:
        write(out/'manifest.json',{'format':'owr-portable-package-v1','state':'incomplete','publication_authorized':False})
        raise

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--source',required=True);cli.add_argument('--output',required=True)
    args=cli.parse_args();print(json.dumps(extract(load(args.source),args.output),ensure_ascii=False))
