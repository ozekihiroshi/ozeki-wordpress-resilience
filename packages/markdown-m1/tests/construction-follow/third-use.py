"""Use an already reconstructed third site; never alter reconstruction materials."""
import importlib.util,json,urllib.request,urllib.parse,http.cookiejar,re,html,subprocess
from pathlib import Path

def verify(run,wp,name,b,ids,objects):
 def load(k):
  sp=importlib.util.spec_from_file_location('use_'+k,b/('product/tools/reconstruct-'+k+'.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
 md=load('markdown');members=load('members');url=wp('third','option','get','home').strip()
 admin=md.NormalMarkdownClient(url,'third-admin','isolated-only-123',True)
 page=ids['post:'+str(objects['page'])];login=ids['post:'+str(objects['login'])]
 jar=http.cookiejar.CookieJar();reader=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
 lost=url+'/wp-login.php?action=lostpassword';f=members.Form(reader.open(lost).read().decode(),'lostpasswordform');v=f.values.copy();v['user_login']='reader@example.invalid'
 reader.open(f.action or lost,urllib.parse.urlencode(v).encode()).read()
 mails=json.loads(run('exec',name+'-third','cat','/tmp/member-mail.json'));links=[]
 for mail in mails:links+=re.findall(r'https?://[^\s<>]+action=rp[^\s<>]+',mail['message'])
 assert links
 response=reader.open(html.unescape(links[-1]));reseturl=response.geturl();f=members.Form(response.read().decode(),'resetpassform');v=f.values.copy();v.update(pass1='third-isolated-reset-456',pass2='third-isolated-reset-456',pw_weak='on');reader.open(f.action or reseturl,urllib.parse.urlencode(v).encode()).read()
 loginurl=url+'/?page_id='+str(login);forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',reader.open(loginurl).read().decode(),re.S) if 'name="log"' in x];assert len(forms)==1
 f=members.Form(forms[0],None);v=f.values.copy();v.update(log='reader',pwd='third-isolated-reset-456');reader.open(f.action or loginurl,urllib.parse.urlencode(v).encode()).read()
 rendered=reader.open(url+'/?page_id='+str(page)).read().decode();guest=urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url+'/?page_id='+str(page)).read().decode()
 assert any('wordpress_logged_in_' in c.name for c in jar)
 assert 'SECOND-GENERATION-EDIT' in rendered and 'SECOND-TABLE' in rendered
 assert 'SECOND-GENERATION-EDIT' not in guest and 'SECOND-TABLE' not in guest
 editor=admin.request('/wp-admin/post.php?post='+str(page)+'&action=edit')[0].decode();assert '42 is text; not a post ID' in editor and members.block_control(editor)=='1'
 form=ids['post:'+str(objects['form'])];forms=json.loads(admin.request('/?rest_route=/contact-form-7/v1/contact-forms',None,{'X-WP-Nonce':admin.nonce})[0]);assert next(f for f in forms if f['id']==form)['title']=='Second inquiry title'
 images=re.findall(r'<img[^>]+src="([^"]+)"',admin.rest('pages/'+str(ids['post:'+str(objects['imagepage'])])+'?context=edit')['content']['raw']);assert images and all(admin.request(html.unescape(u))[0].startswith(b'\x89PNG') for u in images)
 receipts=json.loads(wp('third','eval',"$a=[];foreach(get_posts(['post_type'=>'flamingo_inbound','posts_per_page'=>-1,'post_status'=>'any']) as $p){$m=new Flamingo_Inbound_Message($p->ID);$a[]=['id'=>$p->ID,'fields'=>$m->fields];}echo wp_json_encode($a);"));assert len(receipts)==1 and receipts[0]['fields']['probe']=='C:manual42 日本語'
 viewer=admin.request('/wp-admin/admin.php?page=flamingo_inbound&post='+str(receipts[0]['id'])+'&action=edit')[0].decode();assert 'C:manual42' in html.unescape(viewer)
 assert wp('third','option','get','fixture_submission_count').strip()=='0'
 return {'password_reset_and_member_login':True,'member_visible_guest_blocked':True,'acf_editor_value_retained':True,'updated_cf7_title':True,'block_image_served':True,'flamingo_readable_without_resend':True}

if __name__=='__main__':
 b=Path('/tmp/construction-roundtrip-v5-20261129');name='construction-roundtrip-v5';D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock']
 def run(*args):return subprocess.run(D+list(args),capture_output=True,check=True).stdout
 def wp(site,*args):return run('exec',name+'-'+site,'php','/tmp/wp.phar','--allow-root',*args).decode()
 result=json.loads((b/'result-reuse.json').read_text());state=json.loads(max(b.glob('third-*.json'),key=lambda p:p.stat().st_mtime).read_text())
 result['third_use']=verify(run,wp,name,b,state['follow']['identities'],result['plugins']['first']['test_objects'])
 (b/'result-use.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['third_use']))
