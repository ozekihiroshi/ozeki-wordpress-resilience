<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'authors/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
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
 cfg(false);
 $a=wp_insert_user(['user_login'=>'fixture-author-a','user_pass'=>wp_generate_password(),'user_email'=>'a@example.invalid','display_name'=>'Original Author A','role'=>'author']);
 $b=wp_insert_user(['user_login'=>'fixture-author-b','user_pass'=>wp_generate_password(),'user_email'=>'b@example.invalid','display_name'=>'Author B','role'=>'author']);
 $other=wp_insert_post(['post_type'=>'post','post_title'=>'Author B control','post_content'=>'Control body','post_status'=>'publish','post_author'=>$b]);
 $p=wp_insert_post(['post_type'=>'post','post_title'=>'Authorship fixture','post_content'=>'Original body','post_status'=>'publish','post_author'=>$a]);
 file_put_contents('/lab/ids.json',json_encode(['page'=>$p,'author_a'=>$a,'author_b'=>$b]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='rename-author'){result(wp_update_user(['ID'=>$i['author_a'],'display_name'=>'Renamed Author A']));exit;}
if($mode==='delete-reassign'){require_once ABSPATH.'wp-admin/includes/user.php';result(wp_delete_user($i['author_a'],$i['author_b']));exit;}
if(in_array($mode,['ordinary-initial','save-after-rename','save-after-delete'],true)){result(wp_update_post(['ID'=>$i['page'],'post_content'=>'Confirmed body: '.$mode],true));exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 $p=get_post($i['page']);$u=get_userdata($p->post_author);$history=(new Plugin())->store()->history();$latestAuthor=null;
 foreach($history as $row)if(($row['attributes']['post_type']??'')==='post'&&(int)($row['attributes']['origin_id']??0)===$i['page'])$latestAuthor=$row['attributes']['author']??null;
 out(['article'=>['content'=>$p->post_content,'status'=>$p->post_status,'author_name'=>$u?$u->display_name:null,'author_nicename'=>$u?$u->user_nicename:null], 'actual_author_id'=>(int)$p->post_author,'author_roles'=>$u?$u->roles:[], 'history_count'=>count($history),'latest_recorded_author'=>$latestAuthor,'body_pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'shared_pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'capture_error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
