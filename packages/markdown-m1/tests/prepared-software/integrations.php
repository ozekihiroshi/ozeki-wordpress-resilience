<?php
require '/var/www/html/wp-load.php';
if(!str_starts_with(home_url(),'http://owr-noinit-'))throw new RuntimeException('Not isolated');
wp_set_current_user(1);$mode=$argv[1];$phase=$argv[2]??'one';
function needI($v,$m){if(!$v||is_wp_error($v))throw new RuntimeException($m);return $v;}
if($mode==='seed'){
 $page=wp_insert_post(['post_type'=>'page','post_name'=>'integration-page','post_title'=>'Integration','post_status'=>'publish','post_content'=>'Integration page']);
 $group=acf_update_field_group(['key'=>'group_noinit','title'=>'Trial fields','location'=>[[['param'=>'post_type','operator'=>'==','value'=>'page']]]]);
 acf_update_field(['key'=>'field_noinit_text','name'=>'trial_text','label'=>'Trial text','type'=>'text','parent'=>$group['ID']]);update_field('field_noinit_text','value-one',$page);
 $doc=wp_insert_post(['post_type'=>'ozmd_document','post_name'=>'integration-document','post_title'=>'Document','post_status'=>'publish','post_content'=>'']);
 (new \OzekiMarkdownDocuments\Content\MarkdownSource())->store($doc,"# Trial document\n\nDocument-one");
 $f=WPCF7_ContactForm::get_template(['locale'=>'en_US']);$f->set_title('Integration form');$p=$f->get_properties();$p['form']='[text your-name] [textarea your-message] [submit "Send"]';$p['additional_settings']='skip_mail: on';$f->set_properties($p);$f->save();
 Flamingo_Inbound_Message::add(['posted_data_hash'=>hash('sha256','noinit'),'subject'=>'Integration inquiry','from'=>'Trial <trial@example.invalid>','fields'=>['your-name'=>'Trial','your-message'=>'Message-one','zero'=>'0']]);
 $t=TablePress::$model_table->get_table_template();$t['name']='Integration table';$t['data']=[['Column'],['Table-one']];needI(TablePress::$model_table->add($t),'Table seed');
 echo '{}';exit;
}
$page=needI(get_page_by_path('integration-page',OBJECT,'page'),'Page missing');$doc=needI(get_page_by_path('integration-document',OBJECT,'ozmd_document'),'Document missing');
$forms=get_posts(['post_type'=>'wpcf7_contact_form','numberposts'=>-1]);$receipts=get_posts(['post_type'=>'flamingo_inbound','post_status'=>'any','numberposts'=>-1]);
$tid=null;foreach(TablePress::$model_table->_debug_get_tables()['table_post'] as $id=>$pid){$t=TablePress::$model_table->load((string)$id,true,true);if($t['name']==='Integration table'){$tid=(string)$id;break;}}needI($tid,'Table absent');
if($mode==='edit'){
 update_field('field_noinit_text','value-'.$phase,$page->ID);do_action('acf/save_post',$page->ID);
 (new \OzekiMarkdownDocuments\Content\MarkdownSource())->store($doc->ID,"# Trial document\n\nDocument-".$phase);wp_update_post(['ID'=>$doc->ID,'post_title'=>'Document '.$phase]);
 $f=WPCF7_ContactForm::get_instance($forms[0]->ID);$f->set_title('Integration form '.$phase);$f->save();
 foreach($receipts as $r){$m=new Flamingo_Inbound_Message($r->ID);$m->save();}
 $t=TablePress::$model_table->load($tid,true,true);$t['data']=[['Column'],['Table-'.$phase]];needI(TablePress::$model_table->save($t),'Table resave');
 echo '{}';exit;
}
if($mode==='state'){
 $f=WPCF7_ContactForm::get_instance($forms[0]->ID);$fields=[];foreach($receipts as $r){$m=new Flamingo_Inbound_Message($r->ID);$fields[]=$m->fields;}
 $t=TablePress::$model_table->load($tid,true,true);$field=get_field_object('field_noinit_text',$page->ID);
 $markdown=get_post_meta($doc->ID,'_ozmd_source',true);$curl=curl_init(home_url('/?post_type=ozmd_document&p='.$doc->ID));curl_setopt_array($curl,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_FOLLOWLOCATION=>true,CURLOPT_TIMEOUT=>45]);$html=curl_exec($curl);file_put_contents('/lab/markdown-'.getenv('TRIAL_SIDE').'.html',$html);file_put_contents('/lab/markdown-'.getenv('TRIAL_SIDE').'.json',json_encode(['http'=>curl_getinfo($curl,CURLINFO_HTTP_CODE),'url'=>curl_getinfo($curl,CURLINFO_EFFECTIVE_URL),'source'=>$markdown]));curl_close($curl);
 needI(str_contains($html,'Document-'),'Markdown rendering');needI(str_contains(do_shortcode('[table id='.$tid.' /]'),'Table-'),'Table rendering');needI(str_contains(do_shortcode('[contact-form-7 id="'.$f->id().'"]'),'your-message'),'Form rendering');needI($field&&$field['name']==='trial_text','ACF use');needI($fields[0]['zero']==='0','Flamingo zero field');
 echo json_encode(['markdown'=>$markdown,'acf'=>get_field('trial_text',$page->ID),'field'=>[$field['key'],$field['name'],$field['type']],'form_title'=>$f->title(),'form'=>$f->prop('form'),'receipts'=>$fields,'table'=>$t['data'],'pending'=>(bool)get_option('ozeki_resilience_m1_comment_pending'),'queue_error'=>get_option('ozeki_resilience_m1_comment_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
