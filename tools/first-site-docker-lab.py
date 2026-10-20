"""Dedicated generated-container backend. Not a production Docker adapter."""
import hashlib, json, os, select, subprocess, time
from pathlib import Path

class DockerBackend:
    staging_copies=2
    def set_staging(self,directory):self.spool_directory=Path(directory)
    def __init__(self,api,config,db,web,php,sql,hold,ready,release,run):
        self.a=api;self.expected=config;self.db=db;self.web=web;self.php=php;self.sql=sql
        self.hold_fn=hold;self.ready=ready;self.release_fn=release;self.run=run;self.p=None;self.token=None
    def preflight(self,c):
        self.a.require(c==self.expected,'runtime_scope_mismatch')
        self.a.require(c['database']['name']=='lab' and c['database']['prefix']=='wp_' and c['files']['root']=='/var/www/html','runtime_scope_mismatch')
        expected_modes={w:('fenced' if w in ['http','wp_cron','cli','direct_db'] else 'disabled') for w in self.a.WRITERS}
        self.a.require({w:v['mode'] for w,v in c['writers'].items()}==expected_modes,'runtime_scope_mismatch')
        self.a.require(self.db.startswith('owr-first-site-') and self.web.startswith('owr-first-site-'),'runtime_scope_mismatch')
        data=json.loads(self.run('docker','inspect',self.db,self.web).stdout)
        self.a.require(data[0]['HostConfig']['NetworkMode']=='none' and data[1]['HostConfig']['NetworkMode']=='container:'+data[0]['Id'],'runtime_scope_mismatch')
        self.a.require(all(not x['HostConfig']['PortBindings'] and x['Config']['Labels'].get('owr.first-site')=='generated' for x in data),'runtime_scope_mismatch')
        self.a.require(all(m['Destination'] in ['/var/lib/mysql','/var/www/html','/lab'] for x in data for m in x['Mounts']),'runtime_scope_mismatch')
        self.a.require(self.php("echo ini_get('auto_prepend_file');")==b'/lab/route-prepend.php','runtime_scope_mismatch')
        probe=self.php("require '/var/www/html/wp-load.php'; echo json_encode(['multi'=>is_multisite(),'uploads'=>get_option('upload_path'),'cron'=>defined('DISABLE_WP_CRON')&&DISABLE_WP_CRON]);")
        p=json.loads(probe);self.a.require(not p['multi'] and p['uploads'] in ['', 'wp-content/uploads'] and p['cron'],'runtime_scope_mismatch')
    def fence(self,token,wait,lease):
        # Existing gate generates a random token. Map caller ownership to its token.
        self.token=token;self.p,self.gate_token=self.hold_fn(wait=wait,lease=max(1,lease-wait-3));self.ready(self.p)
    def held(self,token):
        return token==self.token and self.p is not None and self.p.poll() is None and self.php("echo @file_get_contents('/tmp/owr-gate.fence');").decode()==self.gate_token
    def release(self,token):
        if token!=self.token:return False
        if self.p is not None and self.p.poll() is None:
            try:self.release_fn(self.p,self.gate_token)
            except Exception:
                if self.p.stdin and not self.p.stdin.closed:self.p.stdin.close()
                self.p.wait(timeout=12)
        return self.php("echo file_exists('/tmp/owr-gate.fence')?'bad':'ok';")==b'ok'
    def schema(self):
        return [line.split('\t') for line in self.sql("SELECT TABLE_NAME,COALESCE(ENGINE,'UNSUPPORTED') FROM information_schema.TABLES WHERE TABLE_SCHEMA='lab' ORDER BY TABLE_NAME;").decode().splitlines()]
    def inventory(self,limit):
        code="""$base='/var/www/html/'; $out=[];$total=0;foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base,FilesystemIterator::SKIP_DOTS),RecursiveIteratorIterator::SELF_FIRST) as $f){if($f->isLink())throw new Exception('link');if($f->isDir())continue;if(!$f->isFile())throw new Exception('special');$total+=$f->getSize();if($total>LIMIT||count($out)>20000)throw new Exception('limit');$hash=hash_file('sha256',$f->getPathname());if($hash===false)throw new Exception('read');$out[substr($f->getPathname(),strlen($base))]=$hash;}ksort($out);echo json_encode($out);""".replace('LIMIT',str(limit))
        return json.loads(self.php(code))
    def references(self):
        # Read standard WP metadata directly; do not bootstrap WP under the DB lock.
        code=r"""$db=new mysqli('127.0.0.1','lab',getenv('WORDPRESS_DB_PASSWORD'),'lab');$q=$db->query("SELECT p.ID,m.meta_key,m.meta_value FROM wp_posts p LEFT JOIN wp_postmeta m ON m.post_id=p.ID AND m.meta_key IN ('_wp_attached_file','_wp_attachment_metadata') WHERE p.post_type='attachment'");$rows=[];while($r=$q->fetch_assoc()){$rows[$r['ID']][$r['meta_key']??'missing']=$r['meta_value'];}$refs=[];foreach($rows as $row){$file=$row['_wp_attached_file']??null;if(!is_string($file)||$file==='')throw new Exception('missing attachment');$refs[]=$file;if(isset($row['_wp_attachment_metadata'])){$m=unserialize($row['_wp_attachment_metadata'],['allowed_classes'=>false]);if(!is_array($m))throw new Exception('invalid metadata');if(isset($m['file'])&&$m['file']!==$file)throw new Exception('metadata mismatch');$dir=dirname($file);$dir=$dir==='.'?'':$dir.'/';foreach(($m['sizes']??[]) as $v){if(!is_array($v)||!isset($v['file'])||basename($v['file'])!==$v['file'])throw new Exception('invalid size');$refs[]=$dir.$v['file'];}if(isset($m['original_image'])){if(basename($m['original_image'])!==$m['original_image'])throw new Exception('invalid original');$refs[]=$dir.$m['original_image'];}}}sort($refs);echo json_encode(array_values(array_unique($refs)));"""
        return json.loads(self.php(code))
    def stream(self,asset,deadline):
        cmd=['docker','exec',self.db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --skip-lock-tables lab'] if asset=='database' else ['docker','exec',self.web,'tar','-czf','-','-C','/var/www/html','.']
        import importlib.util
        spec=importlib.util.spec_from_file_location('first_site_bounded_stream',Path(__file__).with_name('bounded-process-stream.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        yield from module.stream(cmd,deadline,self.expected['operations']['max_bytes'],self.spool_directory,self.a.Rejected)
