<?php
// Exercise the actual save filter before any lock, S3 write or transaction.
define('ABSPATH',__DIR__.'/');
require $argv[1].'/src/Plugin.php';
use OzekiResilience\M1\Plugin;
function check($value,$why){if(!$value)throw new RuntimeException($why);}
function get_option($key,$default=false){return $key==='ozeki_resilience_m1_config'?['protect'=>true]:$default;}
function get_post($id){return (object)['post_status'=>'publish'];}
function get_post_meta($id,$key,$single){return '';}
function current_user_can(...$args){return $GLOBALS['allowed'];}
function wp_unslash($v){return stripslashes($v);}
function sanitize_text_field($v){return trim(strip_tags($v));}
function wp_verify_nonce($v,$action){$GLOBALS['nonce_checks']++;return $v==='valid'&&$action==='ozmd_save_markdown_source';}
function update_option(...$args){}
function wp_strip_all_tags($v){return strip_tags($v);}
function esc_html($v){return htmlspecialchars($v,ENT_QUOTES,'UTF-8');}
class WP_Error {function __construct(public $code,public $message){}}
class SaveStopped extends RuntimeException{}
function wp_die($error,$title,$args){throw new SaveStopped($error->message);}
class LockBoundary extends RuntimeException{}
class FixtureDb {
 public string $prefix='isolated_';
 function prepare($query,...$args){return $query;}
 function get_var($query){$GLOBALS['lock_attempts']++;throw new LockBoundary('Reached lock boundary');}
}
$wpdb=new FixtureDb();$allowed=true;
$data=['post_type'=>'ozmd_document','post_status'=>'publish'];
foreach([
 ['ozmd_source'=>'new'],
 ['ozmd_source'=>'new','ozmd_source_nonce'=>''],
 ['ozmd_source'=>'new','ozmd_source_nonce'=>'bad'],
 ['ozmd_source'=>'new','ozmd_source_nonce'=>['valid']],
 ['ozmd_source'=>['new'],'ozmd_source_nonce'=>'valid'],
 ['ozmd_source_nonce'=>'valid'],
] as $request){
 $_POST=$request;$lock_attempts=0;$nonce_checks=0;
 try{(new Plugin())->before($data,['ID'=>1],[],true);throw new RuntimeException('Expected rejection');}
 catch(SaveStopped $e){check(!str_contains($e->getMessage(),'Reached lock boundary'),'Malformed editor request rejected first');}
 check($lock_attempts===0,'No lock or storage effects');
}
foreach([['ozmd_source'=>"# Text\n```php\necho 'example';\n```",'ozmd_source_nonce'=>'valid'],[]] as $request){
 $_POST=$request;$lock_attempts=0;$nonce_checks=0;
 try{(new Plugin())->before($data,['ID'=>1],[],true);}catch(SaveStopped $e){check(str_contains($e->getMessage(),'Reached lock boundary'),'Allowed save proceeds');}
 check($lock_attempts===1,'Valid editor and non-editor saves continue');
 check($nonce_checks===($request?1:0),'Nonce mandatory only for submitted editor original');
}
$allowed=false;$_POST=['ozmd_source'=>'new','ozmd_source_nonce'=>'valid'];$lock_attempts=0;
try{(new Plugin())->before($data,['ID'=>1],[],true);}catch(SaveStopped $e){check(str_contains($e->getMessage(),'Invalid save permission'),'Permission independently required');}
check($lock_attempts===0,'Unauthorized save blocked');
echo "PASS editor nonce missing/invalid/array and partial source rejected before side effects; valid and non-editor paths retained; capability independently required.\n";
