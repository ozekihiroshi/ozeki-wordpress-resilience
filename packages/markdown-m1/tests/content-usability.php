<?php
// Disposable WordPress only. Run with wp eval-file ... prepare|check.
if(!in_array(home_url(),['http://localhost:18931','http://localhost:18932'],true))throw new RuntimeException('Isolated fixture required');
wp_set_current_user(1);
$mode=$args[0]??'check';
if($mode==='prepare'){
    $nav=wp_insert_post(['post_type'=>'wp_navigation','post_status'=>'publish','post_title'=>'Prepared navigation','post_content'=>'<!-- wp:navigation-link {"label":"Prepared external link","url":"https://example.invalid/prepared"} /-->']);
    $header=wp_insert_post(['post_type'=>'wp_template_part','post_name'=>'header','post_status'=>'publish','post_title'=>'Prepared header','post_content'=>'<!-- wp:site-title /--><!-- wp:paragraph --><p>PREPARED-HEADER-CONTRACT</p><!-- /wp:paragraph --><!-- wp:navigation {"ref":'.$nav.'} /-->']);
    $front=wp_insert_post(['post_type'=>'wp_template','post_name'=>'front-page','post_status'=>'publish','post_title'=>'Prepared front','post_content'=>'<!-- wp:template-part {"slug":"header","tagName":"header"} /--><!-- wp:post-content /-->']);
    foreach([$header,$front] as $id)wp_set_object_terms($id,get_stylesheet(),'wp_theme');
    wp_set_object_terms($header,'header','wp_template_part_area');
    foreach([$nav,$header,$front]as $id)update_post_meta($id,'prepared_contract',1);
    echo json_encode(['prepared'=>[$nav,$header,$front]]);return;
}
$checks=[];$check=function($name,$ok)use(&$checks){$checks[$name]=(bool)$ok;};
global $wpdb;
$archived=$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON m.post_id=p.ID AND m.meta_key='_ozeki_resilience_m1_origin_url' WHERE p.post_type IN ('wp_template','wp_template_part')");
$check('archived_templates_not_active',(int)$archived===0);
$templates=get_posts(['post_type'=>['wp_template','wp_template_part','wp_navigation'],'posts_per_page'=>-1,'meta_key'=>'prepared_contract']);
$check('prepared_records_preserved',count($templates)===3);
$header=null;foreach($templates as $p)if($p->post_type==='wp_template_part')$header=$p;
$check('prepared_header_content',$header&&str_contains($header->post_content,'PREPARED-HEADER-CONTRACT'));
if($header){$navRef=0;foreach(parse_blocks($header->post_content)as $block)if($block['blockName']==='core/navigation')$navRef=$block['attrs']['ref']??0;
 $check('prepared_navigation_identity',$navRef&&get_post_meta($navRef,'prepared_contract',true)&&get_post_type($navRef)==='wp_navigation');
 $check('prepared_theme_taxonomy',has_term(get_stylesheet(),'wp_theme',$header));}
$resolved=get_block_template(get_stylesheet().'//header','wp_template_part');
$check('core_resolves_prepared_header',$resolved&&str_contains($resolved->content,'PREPARED-HEADER-CONTRACT'));
$resolved=get_block_template(get_stylesheet().'//front-page','wp_template');
$check('core_resolves_prepared_front',$resolved&&str_contains($resolved->content,'wp:post-content'));
// Work on isolated fixture documents; no changes to source originals.
$p=get_page_by_path('contract-public-embed',OBJECT,'page');
if(!$p){
 $doc=wp_insert_post(['post_type'=>'ozmd_document','post_status'=>'publish','post_title'=>'Contract member document','post_name'=>'contract-member-document']);
 (new OzekiMarkdownDocuments\Content\MarkdownSource())->store($doc,"# MEMBER-ONLY-CONTRACT\n\n| Value | Unit |\n|---|---|\n| 24 | V |\n\n[contract_attack]\n");
 update_post_meta($doc,'_wpmem_block','1');update_post_meta($doc,'_ozeki_resilience_m1_origin_url','https://source.invalid/?p=62');
 $pid=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_name'=>'contract-public-embed','post_title'=>'Public embed test','post_content'=>'[ozeki_markdown_document id="'.$doc.'"]']);
 update_post_meta($pid,'_ozeki_resilience_m1_origin_url','https://source.invalid/?p=58');update_post_meta($pid,'_wpmem_block','0');$p=get_post($pid);
 if(!username_exists('contract-member'))wp_insert_user(['user_login'=>'contract-member','user_pass'=>'isolated-contract-member-20261124','user_email'=>'contract-member@example.invalid','role'=>'subscriber']);
}
$doc=get_page_by_path('contract-member-document',OBJECT,'ozmd_document');
$hash=hash('sha256',get_post_meta($doc->ID,'_ozmd_source',true));
$check('markdown_original_present',str_contains(get_post_meta($doc->ID,'_ozmd_source',true),'MEMBER-ONLY-CONTRACT'));
add_shortcode('contract_attack',function(){return 'EXECUTED-ARCHIVED-COMMAND';});
$GLOBALS['post']=$p; $GLOBALS['wp_query']->is_page=true;$GLOBALS['wp_query']->is_singular=true;
$GLOBALS['wp_query']->queried_object=$p;$GLOBALS['wp_query']->queried_object_id=$p->ID;
wp_set_current_user(0);$guest=apply_filters('the_content',$p->post_content);
$check('guest_cannot_read_embedded_member_doc',!str_contains($guest,'MEMBER-ONLY-CONTRACT'));
wp_set_current_user(get_user_by('login','contract-member')->ID);$member=apply_filters('the_content',$p->post_content);
$check('member_can_read_embedded_doc',str_contains($member,'MEMBER-ONLY-CONTRACT')&&str_contains($member,'<table'));
$check('embedded_unknown_shortcode_inert',!str_contains($member,'EXECUTED-ARCHIVED-COMMAND'));
wp_set_current_user(1);$admin=apply_filters('the_content',$p->post_content);
$check('admin_can_read_embedded_doc',str_contains($admin,'MEMBER-ONLY-CONTRACT'));
$check('invalid_embed_attributes_rejected',OzekiResilience\M1\RecoveryContent::markdownEmbed(false,'ozeki_markdown_document',['id'=>(string)$doc->ID,'unsafe'=>'yes'],[])==='');
$check('earlier_access_denial_preserved',OzekiResilience\M1\RecoveryContent::markdownEmbed('','ozeki_markdown_document',['id'=>(string)$doc->ID],[])==='');
$notes=[];$code=OzekiResilience\M1\RecoveryContent::html('<code>[ozeki_markdown_document id="'.$doc->ID.'"]</code>','example',$notes);
$check('code_example_not_executable',!str_contains($code,'[ozeki_markdown_document'));
$check('markdown_original_unchanged',$hash===hash('sha256',get_post_meta($doc->ID,'_ozmd_source',true)));
echo json_encode(['checks'=>$checks,'pass'=>!in_array(false,$checks,true),'document'=>$doc->ID,'page'=>$p->ID],JSON_UNESCAPED_UNICODE);
