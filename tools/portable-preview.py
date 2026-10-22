"""Build a local-only review preview from a portable package; no WordPress or publication."""
import argparse, hashlib, html, importlib.util, json, re, subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('portable_extract',ROOT/'tools/portable-content.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
ESC=lambda value:html.escape(str(value),quote=True)
TAGS={'p','h1','h2','h3','h4','h5','h6','ul','ol','li','strong','b','em','i','blockquote','pre','code','br'}
CSS='body{font:16px/1.8 system-ui,sans-serif;margin:0;background:#f5f7fa;color:#192c3a}main,header,footer{max-width:960px;margin:auto;padding:24px}header{border-bottom:4px solid #28606b}nav a{display:inline-block;margin-right:20px}a{color:#135c71}.notice{padding:16px;background:#fff1c9;border-left:4px solid #b86f00}.missing{display:inline-block;background:#fde5e5;padding:6px;border:1px solid #bd5656}article{background:white;padding:24px;margin-top:20px}img{max-width:100%;height:auto}summary{cursor:pointer}code{overflow-wrap:anywhere}li{margin:6px 0}footer{font-size:14px}'
GD=r'''$b=stream_get_contents(STDIN,8388609); if(strlen($b)>8388608)exit(2); $info=@getimagesizefromstring($b); if(!$info||!in_array($info[2],[IMAGETYPE_PNG,IMAGETYPE_JPEG],true)||$info[0]>4096||$info[1]>4096||$info[0]*$info[1]>4000000)exit(3); $i=@imagecreatefromstring($b);if(!$i)exit(4);imagepng($i);imagedestroy($i);'''

def normalize_image(body,image):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',image):raise ValueError('Pinned image ID required')
    cmd=['docker','--host','unix:///var/run/docker.sock','run','--rm','-i','--network','none','--read-only','--user','65534:65534','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--memory-swap','128m','--pids-limit','32','--entrypoint','php',image,'-d','memory_limit=64M','-r',GD]
    r=subprocess.run(cmd,input=body,capture_output=True,timeout=30)
    if r.returncode or not r.stdout.startswith(b'\x89PNG\r\n\x1a\n') or len(r.stdout)>16777216:raise ValueError('image decode/re-encode failed')
    return r.stdout

def build(package,output,image_runtime=None):
    root=Path(package).resolve(strict=True);out=Path(output).resolve()
    if out==root or root in out.parents or out in root.parents:raise ValueError('Output overlaps source')
    manifest=p.load(root/'manifest.json')
    if manifest.get('format')!='owr-portable-package-v1' or manifest.get('state')!='extracted_with_review':raise ValueError('Incomplete/unsupported package')
    ids=manifest['exported']
    if not ids or len(ids)>200 or len(set(ids))!=len(ids) or any(type(x)!=int or x<1 for x in ids):raise ValueError('Invalid page IDs')
    hashes=manifest['hashes'];blobs={};total=0
    if len(hashes)>5000:raise ValueError('File limit')
    for name,expected in hashes.items():
        q=PurePosixPath(name)
        if q.is_absolute() or '..' in q.parts or '\\' in name or str(q)!=name:raise ValueError('Unsafe package path')
        f=root
        for part in q.parts:
            f=f/part
            if f.is_symlink():raise ValueError('Symlink rejected')
        if not f.is_file() or f.stat().st_size>64*1024**2:raise ValueError('Missing/oversized file')
        body=f.read_bytes();total+=len(body)
        if total>128*1024**2 or p.digest(body)!=expected:raise ValueError('Package hash/size mismatch')
        blobs[name]=body
    def read(name):return json.loads(blobs[name],object_pairs_hook=p.unique)
    records={i:read(f'content/{i}.json') for i in ids};issues=read('issues.json');edges=read('relations.json');media=read('media-index.json')
    if len(issues)>20000 or len(edges)>20000 or len(media)>2000:raise ValueError('Record limit')
    extra=[];images={}
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    def warn(page,code,detail):extra.append(dict(page=page,code=code,detail=detail))
    try:
        p.write(out/'build.json',{'state':'incomplete','publication_authorized':False})
        (out/'style.css').write_text(CSS,encoding='utf-8')
        for m in media:
            ident=m['id']
            if type(ident)!=int or ident<1 or ident in images:raise ValueError('Invalid media ID')
            try:
                if image_runtime is None:raise ValueError('image normalization not configured')
                converted=normalize_image(blobs[m['path']],image_runtime)
                name=f'media-{ident}.png';(out/name).write_bytes(converted);images[ident]=name
            except (ValueError,KeyError,subprocess.SubprocessError):warn(None,'image_withheld',str(ident)+': decode/re-encode unavailable or rejected')
        def edge_for(page,ref):
            found=[e for e in edges if e['page']==page and e['kind']==ref['kind'] and e.get('location')==ref.get('location') and e['original']==ref['original']]
            return found[0] if len(found)==1 else None
        anchor_counts={i:Counter(n['id'] for n in rec['nodes'] if n.get('kind')=='anchor' and isinstance(n.get('id'),str)) for i,rec in records.items()}
        def anchor_id(value):return 'anchor-'+hashlib.sha256(value.encode('utf-8')).hexdigest()
        def render(page,rec):
            result=[];stack=[]
            if rec.get('featured'):
                if rec['featured'] in images:result.append('<figure><img alt="参考画像" src="'+images[rec['featured']]+'"><figcaption>保存素材からの参考画像</figcaption></figure>')
                else:result.append('<p class="missing">アイキャッチ画像は表示保留です。</p>')
            for node in rec['nodes']:
                kind=node.get('kind')
                if kind=='text':result.append(ESC(node['text']))
                elif kind=='anchor':
                    if anchor_counts[page][node['id']]==1:result.append('<span id="'+anchor_id(node['id'])+'"></span>')
                    else:warn(page,'ambiguous_anchor_position',node['id'])
                elif kind=='start' and node.get('tag') in TAGS:
                    tag=node['tag'];result.append('<'+tag+'>')
                    if tag!='br':stack.append(tag)
                elif kind=='end':
                    tag=node.get('tag')
                    if tag in stack:
                        while stack:
                            current=stack.pop();result.append('</'+current+'>')
                            if current==tag:break
                elif kind=='reference':
                    index=node['index']
                    if type(index)!=int or not 0<=index<len(rec['references']):raise ValueError('Invalid reference index')
                    ref=rec['references'][index];edge=edge_for(page,ref)
                    if edge and edge['state']=='resolved' and ref['kind']=='link' and edge['target'] in records:
                        suffix='';fallback=False
                        if edge.get('fragment'):
                            fragment=unquote(edge['fragment'])
                            if anchor_counts[edge['target']][fragment]==1:suffix='#'+anchor_id(fragment)
                            else:
                                fallback=True;warn(page,'anchor_position_not_preserved',ref['original'])
                        result.append('<a href="page-'+str(edge['target'])+'.html'+suffix+'">');stack.append('a')
                        if fallback:result.append('<span class="notice">[節の位置は未再現・ページへのリンク]</span>')
                    elif edge and edge['state']=='resolved' and ref['kind']=='image' and edge['target'] in images:
                        result.append('<img src="'+images[edge['target']]+'" alt="'+ESC(ref.get('alt',''))+'">')
                    else:
                        warn(page,'reference_withheld',ref['original'])
                        result.append('<span class="missing">[未解決または表示保留の'+('画像' if ref['kind']=='image' else 'リンク')+']</span>')
                else:warn(page,'node_not_rendered',str(kind))
            result.extend('</'+tag+'>' for tag in reversed(stack));return ''.join(result)
        rendered={i:render(i,records[i]) for i in ids}
        nav='<nav><a href="index.html">確認一覧</a>'+''.join('<a href="page-'+str(i)+'.html">'+ESC(records[i]['title'])+'</a>' for i in ids)+'</nav>'
        def issue_list(items):return '<ul>'+''.join('<li><strong>'+ESC(x['code'])+'</strong> — '+ESC(x.get('detail',''))+'</li>' for x in items)+'</ul>'
        all_issues=issues+extra
        def shell(title,content):
            return '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\'; style-src \'self\'; base-uri \'none\'; form-action \'none\'"><title>'+ESC(title)+'</title><link rel="stylesheet" href="style.css"></head><body><header><strong>Reconstruct — ローカル確認用</strong>'+nav+'</header><main><p class="notice">未公開プレビューです。元サイトの完全再現・無侵害を保証しません。会社情報・連絡先を担当者が確認してください。</p>'+content+'</main><footer>元WordPressへの接続、外部通信、フォーム送信、自動公開は行いません。</footer></body></html>'
        for i in ids:
            local=[x for x in all_issues if x.get('page')==i];global_issues=[x for x in all_issues if x.get('page') is None]
            parent=[e for e in edges if e['page']==i and e['kind']=='parent' and e['state']=='resolved' and e['target'] in ids]
            breadcrumb=''.join('<p>親ページ：<a href="page-'+str(e['target'])+'.html">'+ESC(records[e['target']]['title'])+'</a></p>' for e in parent)
            content='<h1>'+ESC(records[i]['title'])+'</h1>'+breadcrumb+'<p class="notice">このページの確認事項：'+str(len(local))+'件。未対応要素の残存テキストは参考情報です。</p><article>'+rendered[i]+'</article><section><h2>欠落・未対応・表示保留</h2>'+issue_list(local)+'<h2>全体の確認事項</h2>'+issue_list(global_issues)+'</section>'
            (out/f'page-{i}.html').write_text(shell(records[i]['title'],content),encoding='utf-8')
        index='<h1>会社案内の再構築プレビュー</h1><p>'+str(len(ids))+'ページ / '+str(len(all_issues))+'件の確認事項。抽出されなかった選択ID：'+ESC(manifest.get('missing',[]))+'</p><ul>'+''.join('<li><a href="page-'+str(i)+'.html">'+ESC(records[i]['title'])+'</a></li>' for i in ids)+'</ul><h2>確認事項一覧</h2>'+issue_list(all_issues)
        (out/'index.html').write_text(shell('再構築の確認一覧',index),encoding='utf-8')
        result=dict(format='owr-portable-preview-v1',state='preview_generated_with_review',pages=ids,source_manifest_sha256=p.digest((root/'manifest.json').read_bytes()),
            source_checksums_verified=True,images_rendered=len(images),issues=all_issues,publication_authorized=False,source_wordpress_used=False,
            output_hashes={f.name:p.digest(f.read_bytes()) for f in sorted(out.iterdir()) if f.name!='build.json'})
        p.write(out/'build.json',result);return result
    except Exception:
        p.write(out/'build.json',{'state':'incomplete','publication_authorized':False});raise

if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__);c.add_argument('--package',required=True);c.add_argument('--output',required=True);c.add_argument('--image-runtime')
    a=c.parse_args();result=build(a.package,a.output,a.image_runtime);print(json.dumps({k:v for k,v in result.items() if k!='issues'}))
