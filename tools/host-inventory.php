<?php
/** CLI host probe: SELECT-only account; never loads wp-config.php or WordPress. */
if (PHP_SAPI !== 'cli') { http_response_code(403); exit; }
ini_set('display_errors','0');
$stage='configuration';
try {
    $get=static function($name) { $v=getenv('OWR_INV_'.$name); if (!is_string($v)||$v==='') throw new RuntimeException(); return $v; };
    $site=$get('SITE'); $hash=$get('CONFIG_SHA256'); $nonce=$get('NONCE');
    if (!preg_match('/^[a-z][a-z0-9-]{0,47}$/D',$site)||!preg_match('/^[a-f0-9]{64}$/D',$hash)||!preg_match('/^[a-f0-9]{32}$/D',$nonce)) throw new RuntimeException();
    $name=$get('DB_NAME');$prefix=$get('DB_PREFIX');$root=$get('ROOT');
    if (!preg_match('/^[A-Za-z][A-Za-z0-9_]{0,63}$/D',$name)||!preg_match('/^[A-Za-z][A-Za-z0-9_]{0,63}$/D',$prefix)) throw new RuntimeException();
    $stage='database';
    mysqli_report(MYSQLI_REPORT_ERROR|MYSQLI_REPORT_STRICT);
    $db=mysqli_init();$db->options(MYSQLI_OPT_CONNECT_TIMEOUT,5);
    $db->real_connect($get('DB_HOST'),$get('DB_USER'),$get('DB_PASSWORD'),$name);
    $db->query('SET SESSION MAX_STATEMENT_TIME=5'); // Initial adapter: MariaDB only.
    $db->query('START TRANSACTION READ ONLY');
    $q=$db->prepare('SELECT TABLE_NAME,COALESCE(ENGINE,\'VIEW\') FROM information_schema.TABLES WHERE TABLE_SCHEMA=? LIMIT 2001');$q->bind_param('s',$name);$q->execute();$rows=$q->get_result()->fetch_all(MYSQLI_NUM);
    if (!$rows||count($rows)>2000) throw new RuntimeException();
    $engines=[];$names=[];foreach($rows as $row){$names[]=$row[0];$engines[]=$row[1];}
    foreach(['options','posts','postmeta'] as $required) if (!in_array($prefix.$required,$names,true)) throw new RuntimeException();
    $opts=$db->query("SELECT option_name,option_value FROM `{$prefix}options` WHERE option_name IN ('upload_path','upload_url_path') LIMIT 3")->fetch_all(MYSQLI_ASSOC);
    $uploads='wp-content/uploads';$external=false;
    foreach($opts as $o){if(strlen($o['option_value'])>1024)throw new RuntimeException();if($o['option_name']==='upload_path'&&$o['option_value']!=='')$uploads=$o['option_value'];if($o['option_name']==='upload_url_path'&&$o['option_value']!=='')$external=true;}
    $db->rollback();$db->close();
    $stage='files';
    if(is_link($root)||realpath($root)!==$root||!is_dir($root))throw new RuntimeException();
    $count=0;$bytes=0;$links=0;$special=0;$deadline=microtime(true)+20;
    $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS),RecursiveIteratorIterator::SELF_FIRST);
    foreach($it as $f){
        if(++$count>20000||microtime(true)>$deadline)throw new RuntimeException();
        if($f->isLink()){$links++;continue;}
        if($f->isFile()){$bytes+=$f->getSize();}elseif(!$f->isDir()){$special++;}
    }
    $engines=array_values(array_unique($engines));sort($engines);
    $report=['format'=>'owr-host-inventory-v1','site_id'=>$site,'config_sha256'=>$hash,'nonce'=>$nonce,'observed_at'=>gmdate('c'),'status'=>'observed',
      'facts'=>['database'=>['name'=>$name,'prefix'=>$prefix,'engines'=>$engines,'tables'=>count($names)],
       'files'=>['root'=>$root,'entries'=>$count,'bytes'=>$bytes,'links'=>$links,'special'=>$special],
       'wordpress'=>['standard_upload_path'=>$uploads==='wp-content/uploads','external_upload_url'=>$external,'multisite_tables'=>in_array($prefix.'blogs',$names,true)],
       'runtime'=>['php_version'=>PHP_VERSION,'os_family'=>PHP_OS_FAMILY]],
      'unverified'=>['writers','queue','dependencies','runtime_image_binding','multisite_config','storage','trust','operational_ledgers','file_snapshot_consistency']];
    echo json_encode($report,JSON_THROW_ON_ERROR)."\n";
} catch(Throwable $e) {
    echo json_encode(['format'=>'owr-host-inventory-v1','status'=>'probe_failed','stage'=>$stage])."\n";exit(2);
}
