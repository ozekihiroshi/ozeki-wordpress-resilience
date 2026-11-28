<?php
namespace OzekiResilience\M1 {
    class Identifiers {public static bool $fail=true;public static function migrate(): void {if(self::$fail)throw new \RuntimeException('fixture');update_option('ozeki_resilience_identifiers_v1',1);}}
}
namespace {
define('ABSPATH',__DIR__.'/');$options=['ozeki_resilience_m1_config'=>['protect'=>true,'bucket'=>'keep'],'ozeki_resilience_setup_baseline'=>['manifest'=>'old'],'ozeki_resilience_m1_pending'=>['keep'=>1]];$hooks=[];
function get_option($k,$d=false){global $options;return $options[$k]??$d;}
function update_option($k,$v,$autoload=false){global $options;$options[$k]=$v;return true;}
function delete_option($k){global $options;unset($options[$k]);return true;}
function add_option($k,$v,$deprecated='',$autoload=false){global $options,$rejectGap;if(!empty($rejectGap)||array_key_exists($k,$options))return false;$options[$k]=$v;return true;}
function wp_cache_delete($k,$group=''){return true;}
function determine_locale(){return 'en_US';}
function add_action($k,$v,...$args){global $hooks;$hooks[$k][]=$v;}
function add_filter($k,$v,...$args){add_action($k,$v);}
$wpdb=new class {function suppress_errors($v){return false;}};
require __DIR__.'/../src/Startup.php';
use OzekiResilience\M1\{Startup,Identifiers};
Identifiers::$fail=false;$before=$options;Startup::prepare();
if(!Startup::ready()||get_option('ozeki_resilience_startup_gap')||get_option('ozeki_resilience_m1_config')!==$before['ozeki_resilience_m1_config']||get_option('ozeki_resilience_setup_baseline')!==$before['ozeki_resilience_setup_baseline'])throw new RuntimeException('Successful migration must preserve protection and baseline');
Identifiers::$fail=true;delete_option('ozeki_resilience_identifiers_v1');
Startup::prepare();
if(Startup::ready())throw new RuntimeException('Failure must not boot adapters');
foreach(array_keys($hooks) as $hook)if(!in_array($hook,['admin_notices','admin_menu'],true))throw new RuntimeException('Unrelated WordPress operation guarded: '.$hook);
Identifiers::$fail=false;Startup::prepare();
if(!Startup::ready()||get_option('ozeki_resilience_m1_config')['protect']||get_option('ozeki_resilience_setup_baseline'))throw new RuntimeException('Recovery silently resumed protection');
if(get_option('ozeki_resilience_m1_pending')!==['keep'=>1]||get_option('ozeki_resilience_m1_config')['bucket']!=='keep')throw new RuntimeException('Pending data/storage changed');
update_option('ozeki_resilience_setup_baseline',['manifest'=>'new']);delete_option('ozeki_resilience_startup_gap');update_option('ozeki_resilience_m1_config',['protect'=>true,'bucket'=>'keep']);Startup::prepare();
if(!get_option('ozeki_resilience_m1_config')['protect'])throw new RuntimeException('Normal restart disabled protection');
Identifiers::$fail=true;$rejectGap=true;delete_option('ozeki_resilience_startup_gap');Startup::prepare();
$message=(new ReflectionMethod(Startup::class,'message'))->invoke(null);
if(Startup::ready()||get_option('ozeki_resilience_startup_gap')||!str_contains($message,'interruption record could not be saved'))throw new RuntimeException('Failure to persist interruption was hidden');
echo "Startup containment and explicit restart PASS\n";
}
