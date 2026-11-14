<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,Store};
if(!str_starts_with(home_url(),'http://owr-coexist-'))throw new RuntimeException('Not isolated');
wp_set_current_user(1);$mode=$argv[1];$side=getenv('TRIAL_SIDE');$out='/lab/'.$side;
function output($v){echo wp_json_encode($v,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR)."\n";}
function ids(){return json_decode(file_get_contents('/lab/ids.json'),true);}
function cfg($prefix,$protect,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>$prefix,'protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
if($mode==='seed'){
 cfg('source/',false);$a=[];
 $a['post']=wp_insert_post(['post_type'=>'post','post_status'=>'publish','post_name'=>'supported-article','post_title'=>'Supported article','post_content'=>'Supported body 0']);
 $a['page']=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_name'=>'supported-page','post_title'=>'Supported page','post_content'=>'Supported page 0']);
 $a['markdown']=wp_insert_post(['post_type'=>'ozmd_document','post_status'=>'publish','post_name'=>'supported-markdown','post_title'=>'Supported Markdown']);update_post_meta($a['markdown'],'_ozmd_source',"# Supported Markdown\nBody 0");
 $g=acf_update_field_group(['key'=>'group_coexist','title'=>'Coexist fields','location'=>[[['param'=>'post_type','operator'=>'==','value'=>'post']]]]);acf_update_field(['key'=>'field_coexist','name'=>'coexist_caption','label'=>'Caption','type'=>'text','parent'=>$g['ID']]);update_field('field_coexist','ACF 0',$a['post']);
 $f=WPCF7_ContactForm::get_template(['locale'=>'en_US','title'=>'Supported form']);$p=$f->get_properties();$p['form']='[text* your-name] [email* your-email] [text* your-subject] [textarea* your-message] [submit "Send"]';$p['additional_settings']='skip_mail: on';$p['mail_2']['active']=false;$f->set_properties($p);$a['form']=$f->save();
 $a['formpage']=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_name'=>'supported-form','post_title'=>'Form','post_content'=>'[contact-form-7 id="'.$a['form'].'"]']);
 $m=Flamingo_Inbound_Message::add(['subject'=>'Coexist receipt','from'=>'Trial <trial@example.invalid>','fields'=>['your-name'=>'Trial','your-email'=>'trial@example.invalid','your-subject'=>'Coexist receipt','your-message'=>"Receipt 0\nSecond line"]]);$a['receipt']=$m->id();
 $table=TablePress::$model_table->get_table_template();$table['name']='Supported table';$table['data']=[['Label','Value'],['Reading','0']];$a['table']=TablePress::$model_table->add($table);
 $a['tablepage']=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_name'=>'supported-table','post_title'=>'Table','post_content'=>'[table id='.$a['table'].' /]']);
 $a['member']=wp_create_user('coexistmember','Trial-only-password-20261114','coexist@example.invalid');(new WP_User($a['member']))->set_role('subscriber');wp_update_user(['ID'=>$a['member'],'first_name'=>'Member 0']);update_user_meta($a['member'],'active','1');
 $a['private']=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_name'=>'supported-private','post_title'=>'Private','post_content'=>'MEMBER-ONLY-CONTENT']);update_post_meta($a['private'],'_wpmem_block','1');
 $upload=wp_upload_dir();wp_mkdir_p($upload['basedir']);$file=$upload['basedir'].'/coexist.png';file_put_contents($file,base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='));$a['image']=wp_insert_attachment(['post_title'=>'Image','post_mime_type'=>'image/png','post_status'=>'inherit'],$file);update_attached_file($a['image'],$file);wp_update_attachment_metadata($a['image'],['file'=>'coexist.png','width'=>1,'height'=>1,'sizes'=>[]]);set_post_thumbnail($a['post'],$a['image']);
 file_put_contents('/lab/ids.json',wp_json_encode($a));output($a);exit;
}
if($mode==='unsupported'){
 $u=wp_upload_dir();wp_mkdir_p($u['basedir'].'/dlm_uploads');file_put_contents($u['basedir'].'/dlm_uploads/coexist-private.pdf',"%PDF-1.4\nCOEXIST_PRIVATE_FIXTURE\n%%EOF\n");
 $d=wp_insert_post(['post_type'=>'dlm_download','post_status'=>'publish','post_name'=>'unsupported-download','post_title'=>'Unsupported private document']);update_post_meta($d,'_members_only','yes');
 $v=wp_insert_post(['post_type'=>'dlm_download_version','post_status'=>'publish','post_parent'=>$d,'post_title'=>'1']);update_post_meta($v,'_files',[$u['baseurl'].'/dlm_uploads/coexist-private.pdf']);
 update_post_meta(ids()['post'],'unknown_plugin_value',['kind'=>'opaque','value'=>'must stay outside application']);
 output(['download'=>$d,'version'=>$v,'guard_exists'=>file_exists($u['basedir'].'/dlm_uploads/.htaccess')]);exit;
}
if($mode==='baseline'){
 $prefix=$argv[2]??'source/';cfg($prefix,false);$s=new SiteSnapshot((new Plugin())->store());$r=$s->capture(true,[]);file_put_contents($out.'-baseline.json',wp_json_encode($r));[$m,$f]=$s->load($r['manifest']);output(['plugins'=>$m['plugins'],'excluded'=>$m['excluded_plugins'],'files'=>array_keys($f)]);exit;
}
if($mode==='edit'){
 $a=ids();$n=$argv[2];$prefix=$argv[3]??'source/';cfg($prefix,true);
 wp_update_post(['ID'=>$a['post'],'post_content'=>'Supported body '.$n]);wp_update_post(['ID'=>$a['page'],'post_content'=>'Supported page '.$n]);
 $_POST=['ozmd_source'=>"# Supported Markdown\nBody ".$n,'ozmd_source_nonce'=>wp_create_nonce('ozmd_save_markdown_source')];$_POST['ozeki_resilience_m1_base']=(new ReflectionMethod(Plugin::class,'fingerprint'))->invoke(new Plugin(),$a['markdown']);wp_update_post(['ID'=>$a['markdown'],'post_title'=>'Supported Markdown']);$_POST=[];
 update_field('field_coexist','ACF '.$n,$a['post']);do_action('acf/save_post',$a['post']);
 $m=new Flamingo_Inbound_Message($a['receipt']);$m->fields['your-message']="Receipt $n\nSecond line";$m->save();
 $f=WPCF7_ContactForm::get_instance($a['form']);$f->set_title('Supported form '.$n);$f->save();
 $t=TablePress::$model_table->load((string)$a['table'],true,true);$t['data'][1][1]=(string)$n;TablePress::$model_table->save($t);
 wp_update_user(['ID'=>get_user_by('login','coexistmember')->ID,'first_name'=>'Member '.$n]);
 output(['edited'=>$n]);exit;
}
if($mode==='restore'){
 $from=$argv[2];cfg($from.'/',false,'recovery');$s=new SiteSnapshot((new Plugin())->store());$r=json_decode(file_get_contents('/lab/'.$from.'-baseline.json'),true);$prep=$s->recoveryPreparation($r['manifest']);$checks=OzekiResilience\M1\RecoveryPreparation::checks($prep['requirements'],['options'=>['WPLANG'=>$prep['language']]]);$failed=array_values(array_filter($checks,fn($r)=>!$r['ok']));if($failed){output(['blocked'=>$failed]);exit(2);}wp_mkdir_p('/tmp/restore-work');$result=$s->restore($r['manifest'],true,'/tmp/restore-work');output($result);exit;
}
if($mode==='state'){
 $a=ids();$m=new Flamingo_Inbound_Message($a['receipt']);$member=get_user_by('login','coexistmember');$table=TablePress::$model_table->load((string)$a['table'],true,true);$s=(new Plugin())->store();$h=$s->history();$u=wp_upload_dir();
 output(['post'=>get_post($a['post'])->post_content,'page'=>get_post($a['page'])->post_content,'markdown'=>get_post_meta($a['markdown'],'_ozmd_source',true),'acf'=>get_field('coexist_caption',$a['post']),'receipt'=>$m->fields,'form_title'=>WPCF7_ContactForm::get_instance($a['form'])->title(),'table'=>$table['data'],'member_first'=>get_user_meta($member->ID,'first_name',true),'member_auth'=>(bool)wp_check_password('Trial-only-password-20261114',$member->user_pass,$member->ID),'restriction'=>get_post_meta($a['private'],'_wpmem_block',true),'image'=>hash_file('sha256',$u['basedir'].'/coexist.png'),'unknown_meta'=>get_post_meta($a['post'],'unknown_plugin_value',true),'unknown_posts'=>count(get_posts(['post_type'=>['dlm_download','dlm_download_version'],'post_status'=>'any','numberposts'=>-1])),'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'related_pending'=>(bool)get_option('ozeki_resilience_m1_comment_pending'),'history_count'=>count($h),'history_types'=>array_values(array_unique(array_map(fn($r)=>$r['attributes']['post_type']??'',$h))),'private_file_exists'=>file_exists($u['basedir'].'/dlm_uploads/coexist-private.pdf'),'private_guard_exists'=>file_exists($u['basedir'].'/dlm_uploads/.htaccess')]);exit;
}
if($mode==='large'){
 $u=wp_upload_dir();$file=$u['basedir'].'/dlm_uploads/large-fixture.pdf';$f=fopen($file,'wb');ftruncate($f,33*1024*1024);fclose($f);try{$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);output(['captured'=>true]);}catch(Throwable $e){output(['captured'=>false,'error'=>$e->getMessage()]);}finally{unlink($file);}exit;
}
throw new RuntimeException('mode');

