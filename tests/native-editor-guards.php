<?php
declare(strict_types=1);
$filters=[];
function add_filter($name,$fn,...$args){global $filters;$filters[$name][]=$fn;}
function add_action(...$args){}
class WP_REST_Request {}
require __DIR__.'/../src/SiteMaterialsEditor.php';
$dir=sys_get_temp_dir().'/owr-native-guard-'.bin2hex(random_bytes(6));mkdir($dir);mkdir($dir.'/requests');mkdir($dir.'/reports');
putenv('OWR_RBR_DISPOSABLE=1');
try {
 Owr\SiteMaterialsEditor::boot($dir);$guard=$filters['wp_insert_post_data'][0];
 $empty=['post_type'=>'post','post_status'=>'auto-draft','post_content'=>'','post_excerpt'=>''];
 if($guard($empty,['ID'=>0])!==$empty)throw new RuntimeException('New blank shell should be allowed');
 foreach([[$empty,['ID'=>17]],[array_replace($empty,['post_content'=>'unsaved']),['ID'=>0]],[array_replace($empty,['post_status'=>'publish']),['ID'=>0]]] as [$data,$arr]){
  $rejected=false;try{$guard($data,$arr);}catch(RuntimeException){$rejected=true;}if(!$rejected)throw new RuntimeException('S3 guard bypass');
 }
 $sentinel=(object)['error'=>'prior rejection'];
 if(Owr\NativeMaterialsEditor::dispatch($sentinel,null,new WP_REST_Request())!==$sentinel)throw new RuntimeException('Prior rejection replaced');
 echo "Native entry guards: 5 checks PASS\n";
}finally{rmdir($dir.'/requests');rmdir($dir.'/reports');rmdir($dir);}
