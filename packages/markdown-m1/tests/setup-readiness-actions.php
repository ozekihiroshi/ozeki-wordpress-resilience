<?php
// Exercise the real admin handler: recovery mode must reject both capture paths before storage access.
define('ABSPATH',__DIR__.'/');
require $argv[1].'/src/Plugin.php';
function current_user_can($c){return true;}
function check_admin_referer($n){}
function determine_locale(){return 'en_US';}
function get_option($k,$default=false){return $GLOBALS['options'][$k]??$default;}
function update_option($k,$v,$autoload=false){$GLOBALS['options'][$k]=$v;}
function admin_url($p){return $p;}
class SetupRedirect extends RuntimeException{}
function wp_safe_redirect($u){throw new SetupRedirect();}
$options=['owr_m1_config'=>['setup_role'=>'recovery']];
foreach(['whole_initial','initial_snapshot'] as $operation){
 $_POST=['operation'=>$operation,'trust_initial'=>1];
 try{(new Owr\M1\Plugin())->action();}catch(SetupRedirect $e){}
 if(!str_contains($options['owr_m1_error']??'','recovery destination'))throw new RuntimeException('Capture path not blocked: '.$operation);
}
echo "PASS recovery destination rejects primary and supplementary initial capture before S3 access.\n";
