<?php
require_once $argv[1].'/src/Store.php';require_once $argv[1].'/src/Plugin.php';
function checkGfs($v,$m){if(!$v)throw new RuntimeException($m);}
function get_option($k,$default=false){return $GLOBALS['options'][$k]??$default;}
function update_option($k,$v,$autoload=false){$GLOBALS['options'][$k]=$v;return true;}
function delete_option($k){unset($GLOBALS['options'][$k]);}
function current_user_can($c){return true;}
function check_admin_referer($n){}
function sanitize_text_field($s){return trim((string)$s);}
function wp_unslash($s){return $s;}
function wp_timezone(){return new DateTimeZone('Asia/Tokyo');}
function wp_date($f){return (new DateTimeImmutable('now',wp_timezone()))->format($f);}
function wp_clear_scheduled_hook($h){if($h==='owr_m1_checkpoint')$GLOBALS['event']=false;}
function wp_get_scheduled_event($h){return $GLOBALS['event']??false;}
function wp_schedule_single_event($at,$hook,$args=[],$error=false){$GLOBALS['event']=(object)['timestamp'=>$at,'schedule'=>false];return true;}
function is_wp_error($r){return false;}
function admin_url($p){return $p;}
class GfsRedirect extends RuntimeException{}
function wp_safe_redirect($url){throw new GfsRedirect($url);}
$options=['owr_m1_config'=>['sentinel'=>'old']];
$_POST=['operation'=>'configure','bucket'=>'fixture-bucket','region'=>'ap-northeast-1','prefix'=>'fixture/','owner'=>'','retention_days'=>'0','cleanup_keep_days'=>'14','cleanup_enabled'=>'1','gfs'=>[
 'weekly'=>['enabled'=>'on','weekday'=>'0','time'=>'02:00','keep'=>'2'],
 'monthly'=>['enabled'=>'on','day'=>'1','time'=>'02:00','keep'=>'3'],
 'yearly'=>['enabled'=>'on','month'=>'1','day'=>'1','time'=>'02:00','keep'=>'3'],
]];
try{(new Owr\M1\Plugin())->action();}catch(GfsRedirect $e){}
checkGfs(empty($options['owr_m1_error']),'Settings accepted');$saved=$options['owr_m1_config'];
checkGfs(count($saved['gfs'])===3&&$saved['gfs']['monthly']['keep']===3&&$saved['retention_days']===0,'All form fields persisted');
checkGfs($event->timestamp===$options['owr_gfs_due']['at'],'Next event and due slot registered');
$_POST['gfs']['yearly']['time']='25:99';
try{(new Owr\M1\Plugin())->action();}catch(GfsRedirect $e){}
checkGfs($options['owr_m1_config']===$saved&&str_contains($options['owr_m1_error'],'Invalid GFS'),'Invalid settings do not replace config');
echo "PASS GFS actual admin action: W/M/Y form persistence, next-slot registration, optional lock disabled, invalid input preserves config. WordPress API fixture; no cloud.\n";
