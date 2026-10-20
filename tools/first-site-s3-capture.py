"""Generated capture setup for the separate S3 roundtrip; negative cases remain in capture lab."""
import copy, importlib.util, json, os, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(db,web,php,sql,hold,ready,release,run,check,results,output):
    a=load('capture_api','first-site-capture.py');module=load('docker_backend','first-site-docker-lab.py')
    c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text())
    # Real standard attachment fields. No synthetic content-hash postmeta required.
    attachment=php("require '/var/www/html/wp-load.php'; $p=WP_CONTENT_DIR.'/uploads/one.png'; file_put_contents($p,base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZfoAAAAASUVORK5CYII=')); $id=wp_insert_attachment(['post_title'=>'Capture image','post_status'=>'inherit','post_mime_type'=>'image/png'],$p); update_attached_file($id,$p); wp_update_attachment_metadata($id,['width'=>1,'height'=>1,'file'=>'one.png','sizes'=>[]]); wp_insert_post(['post_title'=>'First site normal post','post_status'=>'publish','post_content'=>'Image attachment']); echo $id;")
    check(int(attachment)>0,'normal attachment creation failed')
    run('docker','exec',web,'sh','-c',"printf 'auto_prepend_file=/lab/route-prepend.php\n' > /usr/local/etc/php/conf.d/owr-route-gate.ini")
    run('docker','exec',web,'apachectl','-k','graceful')
    run('docker','exec',web,'sh','-c',"printf '<?php echo ini_get(\"auto_prepend_file\");' > /var/www/html/gate-probe.php")
    deadline=time.monotonic()+20
    while php("echo file_get_contents('http://127.0.0.1/gate-probe.php');")!=b'/lab/route-prepend.php':
        check(time.monotonic()<deadline,'new Apache config not active');time.sleep(.2)
    root=output.parent/(output.stem+'-private');root.mkdir(mode=0o700)
    cfile=root/'config.json';cfile.write_text(json.dumps(c,indent=2));cfile.chmod(0o600)
    def backend():return module.DockerBackend(a,c,db,web,php,sql,hold,ready,release,run)
    b=backend();original_fence=b.fence
    active=[]
    def probe_fence(*args):
        active.append(subprocess.Popen(['docker','exec','-u','www-data',web,'php','/lab/writer.php','3'],stdout=subprocess.PIPE,stderr=subprocess.PIPE))
        deadline=time.monotonic()+10
        while php("echo file_exists('/tmp/owr-writer-active')?'yes':'no';")!=b'yes':
            check(time.monotonic()<deadline,'active writer absent');time.sleep(.05)
        started=time.monotonic()
        original_fence(*args)
        check(time.monotonic()-started>1,'active writer drain was not observed')
        response=php("$c=curl_init('http://127.0.0.1/');curl_setopt($c,CURLOPT_RETURNTRANSFER,true);curl_exec($c);echo curl_getinfo($c,CURLINFO_HTTP_CODE);")
        check(response==b'503','HTTP not fenced')
        blocked=run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_PASSWORD" mariadb -ulab lab',input=b"SET SESSION lock_wait_timeout=1;INSERT INTO wp_options(option_name,option_value,autoload) VALUES('capture_probe','bad','no');",must=False)
        check(blocked.returncode!=0 and b'1205' in blocked.stderr,'direct DB not fenced')
        results.append({'case':'http_and_direct_db_fenced','passed':True})
    b.fence=probe_fence
    work,v=a.capture(c,a.digest(c),b,root)
    out,err=active[0].communicate(timeout=10);check(active[0].returncode==0,'writer did not finish')
    check(v['state']=='consistent',str(v));check(v['references_checked']==1,'standard attachment not checked')
    check(set(v['assets'])=={'database','files'} and v['queue']['state']=='absent','queue absence contract failed')
    results.append({'case':'real_capture_drain_standard_attachment_two_assets','passed':True,'bytes':sum(x['bytes'] for x in v['assets'].values()),'tables':v['tables'],'attempt_id':v['attempt_id']})
    check(php("echo file_get_contents('http://127.0.0.1/gate-probe.php');")==b'/lab/route-prepend.php','HTTP did not resume')
    sql('CREATE DATABASE capture_restored;')
    # Separate DB only in the owned isolated DB container.
    with (work/'database.sql').open('rb') as f:
        p=subprocess.run(['docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot capture_restored'],stdin=f,capture_output=True)
    check(p.returncode==0,'dump restore failed')
    check(sql("SELECT meta_value FROM capture_restored.wp_postmeta WHERE meta_key='_wp_attached_file';").strip()==b'one.png','restored normal WP reference differs')
    check(sql("SELECT COUNT(*) FROM capture_restored.wp_posts WHERE post_title='First site normal post';").strip()==b'1','restored post missing')
    results.append({'case':'isolated_dump_import_posts_attachment_and_http_resumed','passed':True})
