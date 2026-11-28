<?php
// Synthetic acceptance fixture, orchestrated by recovery-fields-run.py.
// Copy to /lab/fields.php on a fresh isolated-review site with a fresh storage
// prefix. Never run on a real site. The runner asserts use after both recoveries.
$_SERVER['REMOTE_ADDR']='127.0.0.1';$_SERVER['HTTP_USER_AGENT']='IsolatedFixture';$_SERVER['REQUEST_METHOD']='POST';$_SERVER['REQUEST_URI']='/';require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,SetupReadiness};
if(!str_contains(home_url(),'isolated-review'))throw new RuntimeException('Isolated site required');
wp_set_current_user(1);$mode=$argv[1];
function cfg(){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>'fields-final-quotes-'.(($GLOBALS['argv'][2]??'')==='second'?'second':'first').'/','owner'=>'','protect'=>false,'setup_role'=>'source','setup_version'=>1,'terms_version'=>SetupReadiness::TERMS,'gfs'=>[],'cleanup_enabled'=>false]);}
cfg();
if($mode==='seed'){
 $source=new OzekiMarkdownDocuments\Content\MarkdownSource();$doc=wp_insert_post(['post_type'=>'ozmd_document','post_title'=>'Revision fixture','post_status'=>'publish']);
 $source->store($doc,"# Old revision\nOriginal technical description");$rev=wp_save_post_revision($doc);
 if(!$rev||get_post_meta($rev,'_ozmd_source',true)==='')throw new RuntimeException('Source revision missing');
 $source->store($doc,"# Current revision\nCurrent technical description");wp_save_post_revision($doc);
 $forms=[];
 foreach(['your','custom'] as $prefix){$f=WPCF7_ContactForm::get_template();$f->set_title('Limited '.$prefix);$p=$f->get_properties();
  $p['form']='[text* '.$prefix.'-name][email* '.$prefix.'-email][text '.$prefix.'-subject][textarea your-message][submit "Send"]';
  $p['additional_settings']='skip_mail: on'."\n".'flamingo_email: "['.$prefix.'-email]"'."\n".'flamingo_name: "['.$prefix.'-name]"'."\n".'flamingo_subject: "['.$prefix.'-subject]"';
  if($prefix==='custom')$p['additional_settings']=str_replace('"',"'",$p['additional_settings']);
  $p['mail']['sender']='Isolated <source@example.invalid>';$p['mail']['recipient']='destination@example.invalid';$f->set_properties($p);$f->save();$forms[$prefix]=$f->id();
 }
 update_post_meta($doc,'_ozmd_original_filename','technical-source.md');
 $group=acf_update_field_group(['key'=>'group_omission_fields','title'=>'Technical inputs','location'=>[[['param'=>'post_type','operator'=>'==','value'=>'page']]]]);
 acf_update_field(['key'=>'field_omission_help','name'=>'omission_help','label'=>'Device','type'=>'text','instructions'=>'Use <b>24 V</b> equipment. <script>FIELD_SCRIPT</script> [untrusted_command]','parent'=>$group['ID']]);
 $page=wp_insert_post(['post_type'=>'page','post_title'=>'Technical input','post_status'=>'publish']);update_field('field_omission_help','PLC <PLC> [channel]',$page);
 file_put_contents('/lab/limited-ids.json',json_encode(['doc'=>$doc,'revision'=>$rev,'forms'=>$forms,'page'=>$page]));echo "Seeded\n";exit;
}
$ids=json_decode(file_get_contents('/lab/limited-ids.json'),true);
if($mode==='revision'){
 $source=get_post_meta($ids['revision'],'_ozmd_source',true);$current=get_post_meta($ids['doc'],'_ozmd_source',true);
 $r=wp_restore_post_revision($ids['revision']);$restored=get_post_meta($ids['doc'],'_ozmd_source',true);
 $derived=get_post_meta($ids['doc'],'_ozmd_source_sha256',true)===hash('sha256',$restored);
 (new OzekiMarkdownDocuments\Content\MarkdownSource())->store($ids['doc'],$current);
 echo json_encode(['revision_exists'=>(bool)get_post($ids['revision']),'revision_source_present'=>$source!=='','restore_returned_success'=>(bool)$r,'restored_old_markdown'=>str_contains($restored,'Old revision'),'derived_hash_matches'=>$derived,'current_original_present'=>str_contains($current,'Current revision')]);exit;
}
if($mode==='submit'){
 $prefix=$argv[2];$f=WPCF7_ContactForm::get_instance($ids['forms'][$prefix]);
 $_POST=['_wpcf7'=>(string)$f->id(),'_wpcf7_version'=>WPCF7_VERSION,'_wpcf7_locale'=>'en_US','_wpcf7_unit_tag'=>'wpcf7-f'.$f->id().'-o1','_wpcf7_container_post'=>'0',$prefix.'-name'=>'Fixture Reader',$prefix.'-email'=>'reader@example.invalid',$prefix.'-subject'=>'Fixture subject','your-message'=>'Technical fixture'];
 $received=null;add_action('wpcf7_after_flamingo',function($r)use(&$received){$received=$r;});
 $r=$f->submit(['skip_mail'=>true]);$receipt=(int)($received['flamingo_inbound_id']??0);
 echo json_encode(['status'=>$r['status'],'received'=>$receipt>0,'name'=>wpcf7_flamingo_get_value('name',$f),'email'=>wpcf7_flamingo_get_value('email',$f),'subject'=>wpcf7_flamingo_get_value('subject',$f),'receipt_subject'=>$receipt?get_post($receipt)->post_title:null,'receipt_from'=>$receipt?get_post_meta($receipt,'_from',true):null]);exit;
}
if($mode==='capture'){$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/limited-ref.json',json_encode($r));echo "Captured\n";exit;}
if($mode==='use'){
 $field=acf_get_field('field_omission_help');$field['value']=get_field('field_omission_help',$ids['page']);ob_start();acf_render_field_wrap($field);$html=ob_get_clean();
 $method=new ReflectionMethod(OzekiMarkdownDocuments\Admin\DocumentTransfer::class,'exportFilename');$object=(new ReflectionClass(OzekiMarkdownDocuments\Admin\DocumentTransfer::class))->newInstanceWithoutConstructor();
 $filename=$method->invoke($object,get_post($ids['doc']));
 $data=['instructions_retained'=>str_contains($html,'24 V'),'instructions_html_safe'=>!str_contains($html,'<script>')&&!str_contains($field['instructions'],'[untrusted_command]'),'acf_value_unchanged'=>$field['value']==='PLC <PLC> [channel]','filename'=>$filename];
 acf_update_field($field);
 foreach($ids['forms']as $formId){$form=WPCF7_ContactForm::get_instance($formId);$form->set_properties($form->get_properties());$form->save();}
 update_field('field_omission_help',$field['value'],$ids['page']);wp_update_post(['ID'=>$ids['page'],'post_content'=>'Normal edit after recovery']);
 echo json_encode($data);exit;
}
if($mode==='restore'){
 require_once ABSPATH.'wp-admin/includes/user.php';foreach(get_users()as $u)if(!user_can($u,'manage_options'))wp_delete_user($u->ID,1);
 $r=json_decode(file_get_contents('/lab/limited-ref.json'),true);$url='http://isolated-review-fields-'.(($argv[2]??'')==='second'?'second':'first').'.invalid';update_option('home',$url);update_option('siteurl',$url);
 $out=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/lab/work');file_put_contents('/lab/limited-application.json',json_encode($out['application_report']));echo "Restored\n";exit;
}
throw new RuntimeException('Unknown mode');
