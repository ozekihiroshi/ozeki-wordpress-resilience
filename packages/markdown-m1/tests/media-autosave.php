<?php
/** Offline regression: revisions must not start full media reconciliation. */
namespace OzekiResilience\M1 {
    class Plugin { public function config(): array { return ['protect'=>true,'bucket'=>'fixture','prefix'=>'isolated/','region'=>'test','owner'=>'1']; } }
    class AttachmentHistory { public const PENDING='attachments'; }
    class CommentHistory { public const PENDING='comments'; }
}
namespace {
define('ABSPATH',__DIR__.'/');
require __DIR__.'/../src/SaveFailure.php';
require __DIR__.'/../src/MediaAccess.php';
use OzekiResilience\M1\{MediaAccess,SaveFailure,Plugin};
$actions=[];$options=[];
function add_action($name,$callback,...$rest){global $actions;$actions[$name][]=$callback;}
function get_post_type($id){return $id===2?'revision':'page';}
function update_option($key,$value,...$rest){global $options;$options[$key]=$value;return true;}
function get_option($key,$default=false){global $options;return $options[$key]??$default;}
function delete_option($key){global $options;unset($options[$key]);}
function fire($name,...$args){global $actions;foreach($actions[$name]??[] as $f)$f(...$args);}
function check($ok,$message){if(!$ok)throw new \RuntimeException($message);}
$wpdb=new class {
    public $prefix='fixture_';public $locks=0;
    function prepare($query,...$args){return $query;}
    function get_var($query){$this->locks++;return 0;}
};
(new MediaAccess())->boot();
fire('wp_after_insert_post',2,(object)['post_type'=>'revision']);
fire('updated_post_meta',1,2,'_wpmem_block');
fire('updated_post_meta',1,1,'_edit_lock');
fire('updated_post_meta',1,1,'_edit_last');
fire('shutdown');
check($wpdb->locks===0&&!get_option(MediaAccess::PENDING),'Autosave/editor bookkeeping started reconciliation');
fire('updated_post_meta',1,1,'_wpmem_block');
fire('shutdown');
check($wpdb->locks===1&&get_option(MediaAccess::PENDING),'Real access change lost its retry state');
check(get_option(SaveFailure::OPTION)['context']==='Media access capture','Deferred failure lacks diagnostic');
$scope=MediaAccess::scope((new Plugin())->config());
MediaAccess::baselineComplete([],'wrong-scope');
check(get_option(MediaAccess::PENDING),'Other destination cleared pending work');
$options['attachments']=['pending'];MediaAccess::baselineComplete([],$scope);
check(get_option(MediaAccess::PENDING),'Unfinished attachments certified by baseline');
unset($options['attachments']);MediaAccess::baselineComplete([],$scope);
check(!get_option(MediaAccess::PENDING)&&get_option('ozeki_resilience_media_capture_state')['scope']===$scope,'Completed baseline did not seed reconciliation');
echo "PASS revision isolation, real access changes, deferred lock retry and baseline scope\n";
}
