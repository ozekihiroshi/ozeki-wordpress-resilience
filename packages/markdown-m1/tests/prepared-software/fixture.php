<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,MemberHistory};
if(!str_starts_with(home_url(),'http://owr-noinit-'))throw new RuntimeException('Not isolated');
wp_set_current_user(1);$mode=$argv[1];
function configN($prefix,$protect=false,$role='source'){$aws=is_file('/lab/aws.json')?json_decode(file_get_contents('/lab/aws.json'),true):[];update_option('ozeki_resilience_m1_config',['bucket'=>$aws['bucket']??'isolated','owner'=>$aws['owner']??'','region'=>'ap-northeast-1','prefix'=>($aws['prefix']??'').$prefix.'/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function emitN($v){echo json_encode($v,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);}
function softwareN(){ $files=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator(WP_PLUGIN_DIR,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$files[$f->getPathname()]=hash_file('sha256',$f->getPathname());ksort($files);return [hash('sha256',json_encode($files)),get_option('active_plugins')]; }
function stateN(){
 $u=get_user_by('login','trialreader');$settings=[];foreach(MemberHistory::OPTIONS as $k)$settings[$k]=get_option($k,false);
 $pages=[];foreach(get_posts(['post_type'=>'page','numberposts'=>-1]) as $p)$pages[$p->post_name]=['id'=>$p->ID,'body'=>$p->post_content,'restriction'=>get_post_meta($p->ID,'_wpmem_block',true)];
 return ['home'=>home_url(),'settings'=>$settings,'pages'=>$pages,'member'=>$u?['first_name'=>get_user_meta($u->ID,'first_name',true),'city'=>get_user_meta($u->ID,'billing_city',true),'choice'=>get_user_meta($u->ID,'trial_select',true),'roles'=>$u->roles,'password_ok'=>wp_check_password('Trial-member-ONLY-382!',$u->user_pass,$u->ID),'active'=>get_user_meta($u->ID,'active',true)]:null,'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'queue'=>(bool)get_option('ozeki_resilience_m1_comment_pending'),'error'=>get_option('ozeki_resilience_m1_capture_error',false)];
}
if($mode==='prepare'){
 $s=get_option('wpmembers_settings');if(!is_array($s)||!isset($s['version'],$s['form_tags']))throw new RuntimeException('Normal activation did not prepare settings');
 $s['clone_menus']=1;$s['form_tags']['default']='Prepared '.getenv('TRIAL_SIDE').' reference '.preg_replace('/-(target|third)$/','-source',home_url());$s['notify']=0;$s['captcha']=0;update_option('wpmembers_settings',$s);
 file_put_contents('/lab/'.getenv('TRIAL_SIDE').'-prepared.json',json_encode(stateN()));
 emitN(['prepared'=>true,'version'=>$s['version'],'db_version'=>$s['db_version']]);exit;
}
if($mode==='seed'){
 $ids=[];foreach(['private'=>'CONFIDENTIAL_SYNTHETIC_TEXT','login'=>'[wpmem_form login]','profile'=>'[wpmem_profile]'] as $slug=>$content){$ids[$slug]=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_name'=>'trial-'.$slug,'post_title'=>'Trial '.$slug,'post_content'=>$content],true);if(is_wp_error($ids[$slug]))throw new RuntimeException('Page creation failed');}
 update_post_meta($ids['private'],'_wpmem_block','1');
 $u=wp_create_user('trialreader','Trial-member-ONLY-382!','trialreader@example.invalid');if(is_wp_error($u))throw new RuntimeException($u->get_error_message());(new WP_User($u))->set_role('subscriber');
 wp_update_user(['ID'=>$u,'first_name'=>'Initial','last_name'=>'Reader']);update_user_meta($u,'billing_city','Tokyo');update_user_meta($u,'active','1');update_user_meta($u,'trial_select','a');
 $fields=get_option('wpmembers_fields');$fields[]=[0=>'30',1=>'Technical area',2=>'trial_select',3=>'select',4=>'y',5=>'n',6=>'n',7=>['Solar|a','PLC|b'],'profile'=>true];update_option('wpmembers_fields',$fields);
 $s=get_option('wpmembers_settings');$s['block']=['post'=>0,'page'=>0];$s['show_excerpt']=['post'=>0,'page'=>0];$s['mod_reg']=0;$s['notify']=0;$s['user_pages']=['login'=>$ids['login'],'profile'=>$ids['profile'],'register'=>''];update_option('wpmembers_settings',$s);
 emitN(stateN());exit;
}
if($mode==='baseline'){configN($argv[2]);$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/'.$argv[2].'-ref.json',json_encode($r));configN($argv[2],true);emitN(['saved'=>true]);exit;}
if($mode==='restore'){
 configN($argv[2],false,'recovery');$software=softwareN();$includes=get_included_files();$r=json_decode(file_get_contents('/lab/'.$argv[2].'-ref.json'),true);$r=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');if($software!==softwareN())throw new RuntimeException('Installed software changed during recovery');foreach(array_diff(get_included_files(),$includes) as $path)if(preg_match('~/(?:install|uninstall)\.php$~',$path))throw new RuntimeException('Installer included during recovery');emitN(['through'=>$r['through'],'report'=>$r['application_report'],'installed_software_unchanged'=>true,'no_installer_included'=>true]);exit;
}
if($mode==='state'){emitN(stateN()+['queue_error'=>get_option('ozeki_resilience_m1_comment_error',false),'config'=>(new Plugin())->config()]);exit;}
if($mode==='edit-definition'){$fields=get_option('wpmembers_fields');foreach($fields as &$f)if($f[2]==='trial_select'){$f[1]='Updated technical area';$f[7]=['Solar|a','PLC|b','Monitoring|c'];}unset($f);update_option('wpmembers_fields',$fields);emitN(['changed'=>true]);exit;}
if($mode==='delete-definition'){$fields=array_values(array_filter(get_option('wpmembers_fields'),fn($f)=>$f[2]!=='trial_select'));update_option('wpmembers_fields',$fields);emitN(['deleted'=>true]);exit;}
if($mode==='negative'){
 $keep=get_option('wpmembers_settings');delete_option('wpmembers_settings');$before=stateN();configN($argv[2],false,'recovery');$r=json_decode(file_get_contents('/lab/'.$argv[2].'-ref.json'),true);
 try{(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');throw new LogicException('Missing preparation accepted');}catch(RuntimeException $e){$after=stateN();update_option('wpmembers_settings',$keep);emitN(['rejected'=>true,'reason'=>$e->getMessage(),'state_unchanged'=>$before===$after]);}exit;
}
throw new RuntimeException('Unknown mode');
