<?php
namespace OzekiResilience\M1 {class Plugin {public function config(): array{return ['protect'=>true,'setup_role'=>'source'];}} class SiteSnapshot {public static function isInformationFile($p){return true;}}}
namespace {
define('ABSPATH',__DIR__.'/');require __DIR__.'/../src/AttachmentHistory.php';
require __DIR__.'/../src/FileScope.php';
$hooks=[];$opts=[];
function add_action($hook,$fn,...$args){global $hooks;$hooks[$hook][]=$fn;}
function get_option($key,$default=false){global $opts;return $opts[$key]??$default;}
function update_option($key,$value,...$args){global $opts;$opts[$key]=$value;return true;}
function wp_cache_delete(...$args){}
function get_post_type($id){return 'attachment';}
function get_post($id){return (object)['ID'=>$id,'post_type'=>'attachment'];}
function get_post_meta($id){return ['_wp_attached_file'=>['fixture.png']];}
$wpdb=new class {public string $prefix='fixture_';public function prepare($q,...$args){return $q;}public function get_var($q){return 1;}};
(new OzekiResilience\M1\AttachmentHistory())->boot();
foreach($hooks['add_attachment'] as $f)$f(12);
if(get_option(OzekiResilience\M1\AttachmentHistory::PENDING)!==[12=>false])throw new RuntimeException('Registration was not pending');
foreach($hooks['delete_attachment'] as $f)$f(12);
if(get_option(OzekiResilience\M1\AttachmentHistory::DELETED,[])!==[])throw new RuntimeException('Uncompleted deletion must not authorize a missing original');
foreach($hooks['deleted_post_meta'] as $f)$f(1,12,'_wp_attachment_metadata');
foreach($hooks['deleted_post'] as $f)$f(12);
foreach($hooks['deleted_post_meta'] as $f)$f(1,12,'_wp_attachment_metadata');
if(get_option(OzekiResilience\M1\AttachmentHistory::PENDING)!==[12=>true])throw new RuntimeException('Metadata deletion erased attachment deletion');
if(get_option(OzekiResilience\M1\AttachmentHistory::DELETED)!==[12=>['uploads/fixture.png']])throw new RuntimeException('Completed deletion lost its paths');
echo "Attachment deletion survives subsequent metadata callbacks PASS\n";
}
