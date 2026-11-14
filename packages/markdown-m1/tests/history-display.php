<?php
// Isolated WordPress only: the test transport stores immutable fixtures under /lab.
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\Plugin;
use OzekiResilience\M1\Store;
function check($v,$m){if(!$v)throw new RuntimeException($m);}
$types=['','owr_comment','owr_form','owr_member','owr_table','owr_native','owr_acf','owr_media_access','future_kind'];
update_option('ozeki_resilience_m1_config',['bucket'=>'isolated-fixture','region'=>'ap-northeast-1','prefix'=>'history-display/','protect'=>false,'gfs'=>[],'cleanup_enabled'=>false]);
$root='/lab/objects/history-display/history';if(!is_dir($root))mkdir($root,0777,true);
$fixtures=[];$n=0;
foreach($types as $type)foreach(['present','missing','null','empty']as $variant){
 $a=['post_type'=>$type];if($variant==='present')$a+=['title'=>'<existing title>','status'=>'publish'];
 if($variant==='null')$a+=['title'=>null,'status'=>null];if($variant==='empty')$a+=['title'=>'','status'=>''];
 $n++;$row=['schema'=>'owr-md-history-1','sequence'=>$n,'confirmed_at'=>'2026-11-14T00:00:00Z','attributes'=>$a,'original'=>['asset'=>'fixture-'.$n,'source'=>['key'=>'fixture/'.$n.'/source.json']]];
 $path=$root.'/'.sprintf('%020d.json',$n);if(!is_file($path))file_put_contents($path,Store::json($row));$fixtures[]=$row;
}
$before=[];foreach(glob($root.'/*')as $f)$before[$f]=hash_file('sha256',$f);
$store=(new Plugin())->store();$read=$store->history();check($read===$fixtures,'Legacy history read mismatch');
$users=get_users(['role'=>'administrator','number'=>1]);wp_set_current_user($users[0]->ID);require_once ABSPATH.'wp-admin/includes/template.php';
set_error_handler(function($severity,$message,$file,$line){if(error_reporting()&$severity)throw new ErrorException($message,0,$severity,$file,$line);return false;});
$results=[];
foreach(['en_US','ja']as $locale){
 $filter=static fn()=>$locale;add_filter('determine_locale',$filter);
 ob_start();(new Plugin())->page();$html=ob_get_clean();
 if(str_contains($html,'Undefined array key'))throw new RuntimeException(html_entity_decode(strip_tags($html)));
 $label=$locale==='ja'?'ファイルの閲覧条件':'File access conditions';
 check(str_contains($html,$label),'Missing localized access title');
 check(str_contains($html,'&lt;existing title&gt;')&&!str_contains($html,'<existing title>'),'Escaping/legacy title changed');
 check(substr_count($html,'name="sequences[]"')===count($fixtures),'History table truncated');
 foreach($fixtures as $row){$d=Plugin::historyDisplay($row);$a=$row['attributes'];
  if(is_string($a['title']??null))check($d['title']===$a['title'],'Recorded title changed');
  if(is_string($a['status']??null))check($d['status']===$a['status'],'Recorded status changed');
 }
 remove_filter('determine_locale',$filter);$results[$locale]=true;
}
restore_error_handler();
$after=[];foreach(glob($root.'/*')as $f)$after[$f]=hash_file('sha256',$f);check($before===$after,'Existing history rewritten');check($store->history()===$fixtures,'History changed after render');
// The old individual-recovery route must reject media conditions before fetching originals.
if(!class_exists('OzekiMarkdownDocuments\\Content\\MarkdownSource'))eval('namespace OzekiMarkdownDocuments\\Content; class MarkdownSource {}');
$blocked=false;try{(new Plugin())->restore(['29']);}catch(RuntimeException $e){$blocked=str_contains($e->getMessage(),'Use complete site recovery');}
check($blocked,'Media conditions reached individual Markdown restore');
echo json_encode(['history_records'=>count($fixtures),'types'=>count($types),'locales'=>$results,'warnings'=>0,'existing_history_unchanged'=>true,'individual_media_restore_rejected'=>true],JSON_PRETTY_PRINT);
