<?php
require __DIR__.'/construction-management.php';
use OzekiResilience\M1\{ConstructionCapture,ConstructionJournal as J,ConstructionPreservation as P};
$hooks=[];
function add_action($name,$callback,$priority=10,$accepted=1){$GLOBALS['hooks'][$name][]=[$callback,$accepted];}
function add_filter($name,$callback,$priority=10,$accepted=1){add_action($name,$callback,$priority,$accepted);}
function get_post_status($id){return $GLOBALS['fixture_status'][$id]??'publish';}
function get_post_type($id){return 'page';}
function fire($name,...$args){foreach($GLOBALS['hooks'][$name]??[] as [$callback,$accepted])$callback(...array_slice($args,0,$accepted));}
function clear_fixture_gap(){delete_option(J::KEY.'_gap');}
update_option('ozeki_resilience_m1_config',['setup_role'=>'source','protect'=>true]);
(new ConstructionCapture())->boot();
clear_fixture_gap();$GLOBALS['fixture_status'][4]='auto-draft';
fire('set_object_terms',4,[],[],'category');
fire('wp_after_insert_post',4,(object)['post_type'=>'page','post_status'=>'auto-draft'],false,null);
check(get_option(J::KEY.'_gap',null)===null,'Unpublished auto-draft reported as lost publication');
fire('wp_after_insert_post',5,(object)['post_type'=>'page','post_status'=>'publish'],true,null);
check(get_option(J::KEY.'_gap')['identity']['id']===5,'Unobserved published page silently accepted');
$first=get_option(J::KEY.'_gap');fire('updated_post_meta',1,5,'_thumbnail_id');check(get_option(J::KEY.'_gap')===$first,'Later effect erased first gap');
clear_fixture_gap();fire('wp_after_insert_post',5,(object)['post_type'=>'page','post_status'=>'draft'],true,(object)['post_status'=>'publish']);
check(get_option(J::KEY.'_gap',null)!==null,'Withdrawal of publication silently ignored');
clear_fixture_gap();$saved=get_option(P::KEY);delete_option(P::KEY);
fire('edited_term',8,8,'category');check(get_option(J::KEY.'_gap',null)===null,'Initial preparation treated as protection interruption');
add_option(P::KEY.'_capture','fixture');fire('edited_term',8,8,'category');
check(get_option(J::KEY.'_gap',null)!==null,'Change during initial capture not detected');delete_option(P::KEY.'_capture');update_option(P::KEY,$saved);
clear_fixture_gap();update_option('ozeki_resilience_m1_config',['setup_role'=>'recovery']);fire('user_register',8);
check(get_option(J::KEY.'_gap',null)===null,'Prepared recovery account treated as a lost source edit');
echo "PASS formal/unpublished boundary, publication withdrawal, first-gap retention, initial-capture window and prepared destination\n";
