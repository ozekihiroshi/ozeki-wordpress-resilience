<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'publication/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
function result($r){out(['ok'=>!is_wp_error($r)&&$r!==false,'error'=>is_wp_error($r)?$r->get_error_message():null]);}

if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';$c['setup_role']='source';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));
 $c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 $ids=json_decode(file_get_contents('/lab/ids.json'),true);$id=$ids['protected']??$ids['page']??$ids['post'];$p=get_post($id);
 $body=preg_replace('~http://owr-hypothesis-[^/]+/wp-content/uploads/~',wp_upload_dir()['baseurl'].'/',$p->post_content);
 $r=wp_update_post(['ID'=>$id,'post_content'=>$body."\nCycle edit"],true);out(['success'=>!is_wp_error($r)&&$r!==0]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}

if($mode==='prepare'){
 cfg(false);$due=time()+65;$future=gmdate('Y-m-d H:i:s',$due);file_put_contents('/lab/due.json',json_encode($due));
 $p=wp_insert_post(['post_type'=>'post','post_title'=>'Previously public explanation','post_content'=>'Initial public explanation','post_status'=>'publish']);
 $q=wp_insert_post(['post_type'=>'post','post_title'=>'Scheduled explanation','post_content'=>'Scheduled body','post_status'=>'future','post_date'=>$future,'post_date_gmt'=>$future]);
 file_put_contents('/lab/ids.json',json_encode(['protected'=>$p,'scheduled'=>$q]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$ids=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='ordinary-initial'){result(wp_update_post(['ID'=>$ids['protected'],'post_content'=>'Confirmed public explanation'],true));exit;}
if($mode==='reschedule'){$date=gmdate('Y-m-d H:i:s',time()+172800);result(wp_update_post(['ID'=>$ids['protected'],'post_status'=>'future','post_date'=>$date,'post_date_gmt'=>$date],true));exit;}
if($mode==='cancel-to-draft'){result(wp_update_post(['ID'=>$ids['protected'],'post_status'=>'draft','post_content'=>'Draft explanation, no longer public'],true));exit;}
if($mode==='publish-scheduled'){wp_set_current_user(0);check_and_publish_future_post($ids['scheduled']);result(get_post_status($ids['scheduled'])==='publish');exit;}
if($mode==='ordinary-save'){result(wp_update_post(['ID'=>$ids['scheduled'],'post_content'=>'Normally edited after scheduled publication'],true));exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 wp_set_current_user(0);$articles=[];
 foreach($ids as $name=>$id){$p=get_post($id);$q=new WP_Query(['p'=>$id,'post_type'=>'post','post_status'=>'publish','fields'=>'ids']);$articles[$name]=['status'=>$p->post_status,'content'=>$p->post_content,'anonymous_public_query'=>in_array($id,$q->posts,true),'protected_asset'=>(bool)get_post_meta($id,'_ozeki_resilience_m1_asset',true)];unset($articles[$name]['protected_asset']);}
 out(['articles'=>$articles,'history_count'=>count((new Plugin())->store()->history()),'body_pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'shared_pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'capture_error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
