<?php
// Existing in-memory S3 fixture; no AWS or WordPress database writes.
require __DIR__.'/checkpoint.php';
require $argv[1].'/src/SiteSnapshot.php';
require $argv[1].'/src/Plugin.php';
use Owr\M1\{Store,SiteSnapshot,Plugin};
class AdminCheckpointS3 extends MemoryS3 {
 public bool $corrupt=false;public array $writes=[];
 function putObject($a){$this->writes[]=$a['Key'];return parent::putObject($a);}
 function getObject($a){$r=parent::getObject($a);if($this->corrupt&&isset($a['VersionId'])&&str_contains($a['Key'],'/resources/'))$r['Body'].='corrupt';return $r;}
}
eval('namespace Aws\\S3; class S3Client { function __construct($options){} function __call($name,$args){return $GLOBALS["fixture"]->$name(...$args);} }');
function get_option($key,$default=false){return $GLOBALS['options'][$key]??$default;}
function update_option($key,$value,$autoload=false){$GLOBALS['options'][$key]=$value;return true;}
function delete_option($key){unset($GLOBALS['options'][$key]);}
function apply_filters($name,$value){return $value;}
function current_user_can($cap){return true;}
function check_admin_referer($name){}
function wp_unslash($v){return $v;}
function admin_url($v){return $v;}
class CheckpointAdminDb {
 public string $prefix='fixture_',$posts='posts',$postmeta='postmeta',$options='options';
 function prepare($sql,...$args){return $sql;}
 function get_var($sql){return str_contains($sql,'ENGINE')?'InnoDB':1;}
}
$wpdb=new CheckpointAdminDb();
class TestRedirect extends RuntimeException {}
function wp_safe_redirect($url){throw new TestRedirect($url);}
$fixture=new AdminCheckpointS3();$options=['owr_m1_config'=>['bucket'=>'fixture','prefix'=>'admin/','region'=>'fixture']];
$store=new Store($fixture,$options['owr_m1_config']);$site=new SiteSnapshot($store);
$baseline=$site->save(['content.json'=>Store::json(['tables'=>['posts'=>[],'postmeta'=>[],'comments'=>[]],'options'=>[]])],['schema'=>'owr-site-snapshot-1','origin'=>'administrator_initial','through'=>0,'source_url'=>'https://fixture.invalid']);
$options['owr_site_snapshot_result']=$baseline;
$_POST=['operation'=>'whole_checkpoint','site_ref'=>Store::json($baseline['manifest'])];
// Fail only the new Checkpoint verification, after the baseline has been read.
$fixture->writes=[];
// Toggle the fault at the new resource write rather than at baseline loading.
$fixture=new class($fixture) extends AdminCheckpointS3 {
 function __construct($old){$this->objects=$old->objects;$this->n=$old->n;}
 function putObject($a){if(str_contains($a['Key'],'/resources/'))$this->corrupt=true;return parent::putObject($a);}
};
try{(new Plugin())->action();throw new RuntimeException('Expected redirect');}catch(TestRedirect $e){}
ok(str_contains($options['owr_m1_error']??'','Site snapshot resource verification failed:'),'Current failure recorded');
ok(str_contains($options['owr_m1_error'],'S3 content mismatch'),'Cause retained');
ok($options['owr_site_snapshot_result']===$baseline,'No replacement success result');
foreach($fixture->writes as $key)ok(!str_ends_with($key,'/manifest.json'),'No failed manifest');
echo "PASS actual admin action with WordPress/S3 fixtures: verification failure recorded with cause, prior snapshot unchanged, no manifest or new success. No browser/real AWS claim.\n";
