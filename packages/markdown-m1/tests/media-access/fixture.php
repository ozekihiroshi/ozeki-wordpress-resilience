<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,Store};
if(!str_starts_with(home_url(),'http://owr-coexist-'))throw new RuntimeException('Isolation required');
set_exception_handler(function($e){echo wp_json_encode(['operation_failed'=>$e->getMessage()]);exit(0);});
add_filter('wp_die_handler',fn()=>function($m){throw new RuntimeException(is_wp_error($m)?$m->get_error_message():(string)$m);});
wp_set_current_user(1);$mode=$argv[1];$case=$argv[2]??'A';if(!in_array($case,['A','B','C','D'],true))throw new RuntimeException('Case');
function out($v){echo wp_json_encode($v,JSON_THROW_ON_ERROR)."\n";}
function cfg($p,$protect,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>$p,'protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function ids(){global $case;return json_decode(file_get_contents('/lab/case-'.$case.'.json'),true);}
function img($id){global $case;$u=wp_upload_dir();$rel='2026/0'.(ord($case)-64).'/fixture.png';wp_mkdir_p(dirname($u['basedir'].'/'.$rel));file_put_contents($u['basedir'].'/'.$rel,base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB1sAAAAASUVORK5CYII='));$a=wp_insert_attachment(['post_title'=>'Nonconfidential image '.$case,'post_status'=>'inherit','post_parent'=>$id,'post_mime_type'=>'image/png'],$u['basedir'].'/'.$rel,$id);update_post_meta($a,'_wp_attached_file',$rel);wp_update_attachment_metadata($a,['width'=>1,'height'=>1,'file'=>$rel,'sizes'=>[],'image_meta'=>[]]);return ['image'=>$a,'rel'=>$rel];}
function body($v){global $case;return 'BOUNDARY-'.$case.' <img class="wp-image-'.$v['image'].'" src="'.wp_upload_dir()['baseurl'].'/'.$v['rel'].'">';}
if($mode==='seed'){
 cfg('source-'.$case.'/',false);$user=get_user_by('login','boundarymember');if(!$user){$uid=wp_create_user('boundarymember','Trial-only-20261114','boundary@example.invalid');(new WP_User($uid))->set_role('subscriber');update_user_meta($uid,'active','1');}
 $v=['post'=>wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_title'=>'Boundary '.$case,'post_content'=>'BOUNDARY-'.$case])];
 if(in_array($case,['B','D'],true)){$v+=img($v['post']);wp_update_post(['ID'=>$v['post'],'post_content'=>body($v)]);}
 file_put_contents('/lab/case-'.$case.'.json',wp_json_encode($v));out($v);exit;
}
if($mode==='baseline'||$mode==='comparison'){
 $from=$argv[3]??'source';cfg($from.'-'.$case.'/',false);$s=new SiteSnapshot((new Plugin())->store());$r=$s->capture(true,[]);[$m,$files]=$s->load($r['manifest']);
 if($mode==='baseline')file_put_contents('/lab/'.$from.'-'.$case.'-ref.json',wp_json_encode($r));
 out(['files'=>array_keys($files),'through'=>$r['through'],'excluded'=>$r['excluded_files']??[]]);exit;
}
if($mode==='change'){
 cfg('source-'.$case.'/',true);$v=ids();
 if(in_array($case,['A','C'],true)){$v+=img($v['post']);file_put_contents('/lab/case-'.$case.'.json',wp_json_encode($v));}
 if(in_array($case,['B','C'],true)){update_post_meta($v['image'],'_members_only','yes');file_put_contents(dirname(wp_upload_dir()['basedir'].'/'.$v['rel']).'/.htaccess',"Require all denied\n");}
 if($case==='D')update_post_meta($v['post'],'_wpmem_block','1');
 if(in_array($case,['A','C'],true))wp_update_post(['ID'=>$v['post'],'post_content'=>body($v)]);
 out(['changed'=>$case]);exit;
}
if($mode==='restore'){$from=$argv[3]??'source';cfg($from.'-'.$case.'/',false,'recovery');$r=json_decode(file_get_contents('/lab/'.$from.'-'.$case.'-ref.json'),true);wp_mkdir_p('/tmp/boundary-restore');out((new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/boundary-restore'));exit;}
if($mode==='resave'){cfg(($argv[3]??'second').'-'.$case.'/',true);$v=ids();wp_update_post(['ID'=>$v['post'],'post_content'=>get_post($v['post'])->post_content.' RESAVED']);out(['resaved'=>true]);exit;}
if($mode==='auth'){$u=get_user_by('login','boundarymember');$token=WP_Session_Tokens::get_instance($u->ID)->create(time()+600);out(['name'=>LOGGED_IN_COOKIE,'value'=>wp_generate_auth_cookie($u->ID,time()+600,'logged_in',$token)]);exit;}
if($mode==='state'){$v=ids();$s=(new Plugin())->store();$h=$s->history();$f=isset($v['rel'])?wp_upload_dir()['basedir'].'/'.$v['rel']:'';out(['ids'=>$v,'body'=>get_post($v['post'])->post_content,'file_exists'=>$f&&is_file($f),'hash'=>$f&&is_file($f)?hash_file('sha256',$f):null,'held_hash'=>isset($v['rel'])&&\OzekiResilience\M1\MediaAccess::heldBody('uploads/'.$v['rel'])!==null?hash('sha256',\OzekiResilience\M1\MediaAccess::heldBody('uploads/'.$v['rel'])):null,'private_meta'=>isset($v['image'])?get_post_meta($v['image'],'_members_only',true):null,'member_block'=>get_post_meta($v['post'],'_wpmem_block',true),'history'=>array_map(fn($x)=>['sequence'=>$x['sequence'],'type'=>$x['attributes']['post_type']??''],$h),'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'related_pending'=>(bool)get_option('ozeki_resilience_m1_comment_pending')]);exit;}
if($mode==='release'){
 cfg('source-'.$case.'/',true);$v=ids();delete_post_meta($v['image'],'_members_only');$guard=dirname(wp_upload_dir()['basedir'].'/'.$v['rel']).'/.htaccess';if(is_file($guard))unlink($guard);\OzekiResilience\M1\MediaAccess::record();out(['released'=>true]);exit;
}
if($mode==='guard'){
 cfg('source-'.$case.'/',true);$v=ids();file_put_contents(dirname(wp_upload_dir()['basedir'].'/'.$v['rel']).'/.htaccess',"Require all denied\n");\OzekiResilience\M1\MediaAccess::record();out(['rechecked'=>true]);exit;
}
if($mode==='reset-uploads'){
 cfg('disabled/',false);$root=wp_upload_dir()['basedir'];if(is_dir($root)&&!rename($root,WP_CONTENT_DIR.'/owr-fixture-previous-uploads-'.bin2hex(random_bytes(6))))throw new RuntimeException('reset');wp_mkdir_p($root);out(['reset'=>true]);exit;
}
if($mode==='ui'){
 require_once ABSPATH.'wp-admin/includes/template.php';
 $locale=$argv[3]??'en_US';add_filter('pre_determine_locale',fn()=>$locale);
 ob_start();(new Plugin())->page();$html=ob_get_clean();
 $label=$locale==='ja'?'ファイルの閲覧条件を再確認・記録':'Record file access conditions';
 out(['locale'=>$locale,'label_present'=>str_contains($html,$label),'operation_present'=>str_contains($html,'media_recheck'),'nonce_present'=>str_contains($html,'_wpnonce')]);exit;
}
throw new RuntimeException('Mode');
