<?php
// No WordPress or network: fail if a no-op edit touches attachment bytes or S3.
namespace OzekiResilience\M1 {
class Plugin {function config(){return ['protect'=>true,'setup_role'=>'source'];}}
class AttachmentHistory {const PENDING='attachment_pending';static function reconcile(){throw new \RuntimeException('No-op edit scanned attachment bodies');}}
class CommentHistory {const PENDING='comment_pending';function enqueueCurrent(...$args){throw new \RuntimeException('No-op edit queried S3');}}

}
namespace {
define('ABSPATH',__DIR__.'/');require __DIR__.'/../src/MediaAccess.php';
function wp_upload_dir(){return ['basedir'=>sys_get_temp_dir()];}
function wp_cache_delete(...$args){}
function get_option($key,$default=false){return $key==='ozeki_resilience_media_capture_state'?['rules'=>[],'scope'=>hash('sha256',serialize([]))]:$default;}
define('ARRAY_A','ARRAY_A');$wpdb=new class {public $posts='posts',$postmeta='postmeta',$last_error='',$prefix='fixture_';function get_results(...$args){return [];}function prepare($q,...$args){return $q;}function get_var($q){return 1;}};
OzekiResilience\M1\MediaAccess::record();echo "Unchanged media: no attachment read and no S3 request PASS\n";
}
