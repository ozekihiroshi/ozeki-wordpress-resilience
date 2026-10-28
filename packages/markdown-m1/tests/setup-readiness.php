<?php
// Run with php -n: simulate a server without the ZIP extension. No WordPress or cloud writes.
define('ABSPATH',__DIR__.'/');
require $argv[1].'/src/SetupReadiness.php';
use OzekiResilience\M1\SetupReadiness as R;
function determine_locale(){return $GLOBALS['locale']??'en_US';}
function get_option($key,$default=false){return $GLOBALS['options'][$key]??$default;}
function check($ok,$why){if(!$ok)throw new RuntimeException($why);}
class SetupDatabase {
    public $posts='wp_posts',$postmeta='wp_postmeta',$options='wp_options';
    public $engine='InnoDB',$markdown=false;
    function prepare($sql,$table){return [$sql,$table];}
    function get_var($query){return is_array($query)?$this->engine:($this->markdown?1:null);}
}
$wpdb=new SetupDatabase();$wp_version='6.4';$options=[];
$rows=R::local();check($rows['database']['ok'],'InnoDB accepted');
check(!$rows['zip']['ok']&&str_contains($rows['zip']['next'],'PHP zip'),'Missing ZIP extension gives next step');
$wpdb->engine='MyISAM';check(!R::local()['database']['ok'],'Nontransactional tables rejected');
$wpdb->engine='InnoDB';$wpdb->markdown=true;
check(!R::local()['markdown']['ok'],'Existing Markdown needs active dependency');
$options['active_plugins']=['ozeki-markdown-documents/ozeki-markdown-documents.php'];
check(R::local()['markdown']['ok'],'Active Markdown dependency accepted');
$options['owr_m1_pending']=['operation'=>'pending'];check(!R::local()['pending']['ok'],'Pending work requires resume');
$locale='ja';check(str_contains(R::local()['zip']['next'],'サーバー管理者'),'Japanese next step');
$c=['bucket'=>'fixture','region'=>'ap-northeast-1','prefix'=>'site/'];
check(!R::accepted([])&&R::accepted($c),'Fresh blocked, configured legacy preserved');
check(!R::accepted($c+['setup_version'=>1]),'New settings need confirmation');
check(R::accepted($c+['setup_version'=>1,'terms_version'=>R::TERMS]),'Confirmed settings accepted');
$options['owr_setup_baseline']=['identity'=>R::identity($c),'manifest'=>['key'=>'fixture']];
check(R::baseline($c),'Baseline belongs to destination');$locale='en_US';check(R::storageNext($c+['protect'=>true])==='No action needed.','Completed source is not prompted to repeat initial save');check(str_contains(R::storageNext($c+['setup_role'=>'recovery']),'existing Checkpoint'),'Recovery next action');$c['prefix']='other/';check(!R::baseline($c),'Other destination cannot inherit baseline');
echo "PASS local preparation: missing ZIP, InnoDB, Markdown dependency, pending work, Japanese guidance, confirmation and destination binding.\n";
