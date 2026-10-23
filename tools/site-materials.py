"""Site-wide immutable materials. Single designated writer; no old WordPress DB input."""
import base64, contextlib, fcntl, gzip, hashlib, json, os, re, time, zlib
from pathlib import Path

def canon(v): return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(v): return hashlib.sha256(v).hexdigest()
def require(v,reason):
    if not v: raise ValueError(reason)
def atomic(path,value):
    tmp=path.with_suffix('.tmp')
    with tmp.open('wb') as f:
        os.chmod(tmp,0o600);f.write(canon(value));f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def normalize(site):
    require(set(site)=={'schema','title','landing','entries'},'Explicit site fields required')
    require(site['schema']=='owr-site-materials-v1','Site schema')
    require(isinstance(site['title'],str) and len(site['title'])<=200,'Site title')
    rows=site['entries'];require(isinstance(rows,list) and 1<=len(rows)<=1000,'Site entry bound')
    ids=set();slugs=set();out=[]
    for source in rows:
        row=json.loads(canon(source));ident=row.get('id');kind=row.get('kind')
        require(isinstance(ident,str) and re.fullmatch('[a-z][a-z0-9_-]{0,79}',ident) and ident not in ids,'Stable unique asset ID')
        ids.add(ident)
        if kind=='image':
            require(set(row)=={'id','kind','mime','data','alt'},'Image fields')
            raw=base64.b64decode(row['data'],validate=True)
            require(0<len(raw)<=4*1024*1024 and isinstance(row['alt'],str) and len(row['alt'])<=1000,'Image bounds')
            require((row['mime']=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (row['mime']=='image/jpeg' and raw.startswith(b'\xff\xd8\xff')),'Supported image signature')
        else:
            require(kind in ('page','post') and set(row)=={'id','kind','title','slug','parent','nodes'},'Supported post/page fields')
            require(isinstance(row['title'],str) and 0<len(row['title'])<=200,'Title bound')
            require(isinstance(row['slug'],str) and re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',row['slug']) and row['slug'] not in slugs,'Unique portable slug');slugs.add(row['slug'])
            require(isinstance(row['nodes'],list) and len(row['nodes'])<=500,'Body bounds')
            for n in row['nodes']:
                typ=n.get('type');keys={'paragraph':{'type','text'},'heading':{'type','text','level'},'link':{'type','text','target'},'image':{'type','target'}}
                require(typ in keys and set(n)==keys[typ],'Unsupported content node; no silent conversion')
                if 'text' in n:require(isinstance(n['text'],str) and len(n['text'])<=20000,'Text bound')
                if typ=='heading':require(type(n['level']) is int and 2<=n['level']<=6,'Heading level')
        out.append(row)
    byid={x['id']:x for x in out}
    require(site['landing'] in byid and byid[site['landing']]['kind']=='page','Landing page')
    for row in out:
        if row['kind']=='image':continue
        p=row['parent'];require(p is None or (row['kind']=='page' and p in byid and byid[p]['kind']=='page'),'Page parent')
        visited={row['id']}
        while p is not None:
            require(p not in visited,'Parent cycle');visited.add(p);p=byid[p]['parent']
        for n in row['nodes']:
            if 'target' in n:require(n['target'] in byid and (byid[n['target']]['kind']=='image')==(n['type']=='image'),'Dangling or wrong-kind relation')
    require(len(canon(site))<=64*1024*1024,'Submitted material size bound')
    return dict(site,entries=sorted(out,key=lambda x:x['id']))

def expected(site):
    rows=[]
    for row in normalize(site)['entries']:
        if row['kind']=='image':row={k:v for k,v in row.items() if k!='data'}|{'sha256':sha(base64.b64decode(row['data']))}
        rows.append(row)
    return {'title':site['title'],'landing':site['landing'],'entries':rows}

def markdown(text):
    # Deliberately bounded portable subset; raw HTML, embeds and inline formatting are rejected.
    nodes=[]
    for line in text.splitlines():
        if not line.strip():continue
        require(not any(c in line for c in '<>!*`[]'),'Unsupported Markdown syntax')
        match=re.fullmatch(r'(#{2,6}) (.+)',line)
        if match:nodes.append({'type':'heading','level':len(match[1]),'text':match[2]})
        else:
            require(not line.startswith('#'),'Unsupported Markdown heading')
            nodes.append({'type':'paragraph','text':line})
    return nodes

class Repository:
    """Durable single-writer journal. Multiple hosts must not share the writer role."""
    def __init__(self,store,work,prefix):
        self.store=store;self.work=Path(work);self.work.mkdir(mode=0o700,parents=True,exist_ok=True);self.prefix=prefix
        require(not self.work.is_symlink(),'Private writer directory required')
    def put(self,raw,horizon):
        require(0<len(raw)<=8*1024*1024,'Stored object size bound')
        # A bounded retention window avoids trying to reuse an already expired original.
        # Deduplication applies within a window; fixed references remain authoritative.
        key_digest=sha(raw+b'\0retention-window:'+str(horizon//86400).encode())
        ref=self.store.put(raw,self.prefix+'rbr-'+key_digest+'.blob')
        actual,until,_=self.store.get(ref)
        require(actual==raw,'Stored bytes mismatch')
        if until<horizon:
            # New retained copy; never extend or overwrite the existing fixed version.
            ref=self.store.put(raw,self.prefix+'rbr-'+sha(raw+str(horizon).encode())+'.blob')
            actual,until,_=self.store.get(ref)
        require(actual==raw and until>=horizon,'Stored bytes/retention mismatch')
        return ref
    def save(self,operation,parent,site,policy='integrity',approval_ref=None):
        require(re.fullmatch('[a-zA-Z0-9_-]{1,80}',operation),'Operation ID')
        require(policy in ('integrity','independent-signature'),'Explicit policy')
        require(policy=='integrity' or approval_ref is not None,'Signature policy requires approval reference')
        site=normalize(site);request={'site':site,'parent':parent,'policy':policy,'approval_ref':approval_ref}
        with (self.work/'writer.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            headfile=self.work/'head.json';head=json.loads(headfile.read_bytes()) if headfile.exists() else None
            opfile=self.work/(operation+'.json')
            if opfile.exists():
                op=json.loads(opfile.read_bytes());require(op['request_sha256']==sha(canon(request)),'Operation reused with different content')
                if op.get('receipt'):
                    require(head in (parent,op['receipt']),'Old operation cannot replace newer head')
                    if head==parent:atomic(headfile,op['receipt'])
                    return op['receipt']
            else:
                require(head==parent,'Stale parent; no writes started')
                op={'request_sha256':sha(canon(request)),'horizon':int(time.time())+35*86400,'state':'saving'};atomic(opfile,op)
            require(head==parent,'Stale resumed operation')
            refs=[]
            for row in site['entries']:
                raw=canon(row);packed=gzip.compress(raw,compresslevel=6,mtime=0)
                ref=self.put(packed,op['horizon'])
                refs.append({'id':row['id'],'ref':ref,'raw_sha256':sha(raw),'raw_size':len(raw),'encoding':'gzip'})
            manifest={'schema':'owr-site-generation-v1','site_title':site['title'],'landing':site['landing'],'objects':refs,'expected':expected(site),'parent':parent,'operation':operation,'policy':policy,'approval_ref':approval_ref,'protect_until':op['horizon'],'rules':'portable-nodes-v1'}
            receipt=self.put(canon(manifest),op['horizon'])
            op.update(state='committed',receipt=receipt);atomic(opfile,op);atomic(headfile,receipt)
            return receipt

def receive(store,receipt,verify_signature=None):
    raw,until,_=store.get(receipt);require(sha(raw)==receipt['sha256'],'Manifest hash')
    m=json.loads(raw);require(m['schema']=='owr-site-generation-v1' and m['rules']=='portable-nodes-v1','Generation contract')
    require(until>=m['protect_until']>time.time(),'Generation retention')
    if m['policy']=='independent-signature':
        require(verify_signature is not None,'Independent signature verifier required');verify_signature(receipt,m['approval_ref'])
    else:require(m['policy']=='integrity','Unknown policy')
    require(1<=len(m['objects'])<=1000,'Object count')
    entries=[];total=0
    for item in m['objects']:
        require(item['encoding']=='gzip' and 0<item['raw_size']<=6*1024*1024,'Compressed object bounds')
        packed,retained,_=store.get(item['ref']);require(retained>=m['protect_until'],'Asset retention')
        require(sha(packed)==item['ref']['sha256'],'Asset compressed hash')
        decoder=zlib.decompressobj(31);raw=decoder.decompress(packed,item['raw_size']+1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail and len(raw)==item['raw_size'] and sha(raw)==item['raw_sha256'],'Compressed content mismatch')
        total+=len(raw);require(total<=64*1024*1024,'Total material bound')
        row=json.loads(raw);require(row['id']==item['id'],'Asset identity');entries.append(row)
    site=normalize({'schema':'owr-site-materials-v1','title':m['site_title'],'landing':m['landing'],'entries':entries})
    require(expected(site)==m['expected'],'Request-derived expected state mismatch')
    return {'schema':'owr-site-received-v1','receipt':receipt,'site':site,'expected':m['expected'],'policy':m['policy'],'parent':m['parent']}
