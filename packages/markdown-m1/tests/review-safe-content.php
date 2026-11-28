<?php
// Run with wp eval-file on a disposable WordPress with the candidate activated.
use OzekiResilience\M1\RecoveryContent;
require_once WP_PLUGIN_DIR.'/ozeki-resilience/src/RecoveryContent.php';
function safe_check($ok,$why){if(!$ok)throw new RuntimeException($why);}
// Standard closing slash is shortcode grammar, not an application attribute.
foreach(['[table id="1" /]','[table id="1"/]','[table id="1"]',"[table\n id='1' /]",'[contact-form-7 id="abc123" /]','[ozeki_markdown_document id="1" /]'] as $reference){
    $notes=[];
    safe_check(RecoveryContent::html($reference,'self-closing-reference',$notes)===$reference&&$notes===[],'Supported self-closing reference disabled');
}
foreach(['[table id="1" arbitrary="x" /]','[table id="1" / extra]','[table id="1" //]','[table id="1" "extra" /]','[table id="1/" /]','[table id="1" / ]'] as $reference){
    $notes=[];
    safe_check(RecoveryContent::html($reference,'invalid-reference',$notes)!==$reference&&count($notes)>0,'Invalid reference allowed');
}
$original='<h2>技術資料</h2><table><tr><td>24 V</td></tr></table><pre><code>&lt;script&gt;example&lt;/script&gt;</code></pre><img src="https://example.invalid/a.png" onerror="alert(1)"><script>alert(2)</script><a href="javascript:alert(3)">link</a>';
$hash=hash('sha256',$original);$report=[];
$clean=RecoveryContent::html($original,'fixture',$report);
safe_check(!str_contains($clean,'<script')&&!str_contains($clean,'onerror=')&&!str_contains($clean,'javascript:'),'Executable markup survived');
safe_check(str_contains($clean,'技術資料')&&str_contains($clean,'<table>')&&str_contains($clean,'&lt;script&gt;'),'Useful information lost');
safe_check(hash('sha256',$original)===$hash&&count($report)>0,'Original/report contract');
$again=[];safe_check(RecoveryContent::html($clean,'fixture',$again)===$clean,'Second recovery changes safe information');
add_shortcode('table',fn()=>'EXECUTED_CODE_EXAMPLE');
$r=[];$example=RecoveryContent::html('<pre><code>[table id="1"]</code></pre>','example',$r);
safe_check(!str_contains(do_shortcode($example),'EXECUTED_CODE_EXAMPLE'),'Code example executed');
add_shortcode('review_attack',fn()=>'<script>window.reviewExecuted=1</script>');
$r=[];$text=RecoveryContent::html('[review_attack]','shortcode',$r);
safe_check(!str_contains(do_shortcode($text),'<script>'),'Unknown shortcode executed');
foreach(["[review_attack\n value=\"x\"]",'[123attack]','[unrecognized value="[review_attack x]"]'] as $attack){
    add_shortcode('123attack',fn()=>'<script>window.reviewExecuted=3</script>');
    $r=[];safe_check(!str_contains(do_shortcode(RecoveryContent::html($attack,'shortcode-grammar',$r)),'<script>'),'Alternate shortcode syntax executed');
}
$r=[];$block='<!-- wp:review/attack {"action":"execute"} /-->';
register_block_type('review/attack',['render_callback'=>fn()=>'<script>window.reviewExecuted=2</script>']);
safe_check(!str_contains(do_blocks(RecoveryContent::html($block,'block',$r)),'<script>'),'Unknown dynamic block executed');
$r=[];$block="<!--\nwp:review/attack /-->";
safe_check(!str_contains(do_blocks(RecoveryContent::html($block,'block-whitespace',$r)),'<script>'),'Alternate block whitespace executed');
$md="# 技術資料\n\n```html\n<script>alert(1)</script>\n```\n\n[bad](javascript:alert(2))\n";
safe_check(OzekiResilience\M1\Plugin::validatedMarkdown($md)===$md,'Markdown original changed');

// Concrete cross-boundary cases from the one-time call-site review.
$form='[text sample "<PLC>"]<script>FORM_PROBE</script>[acceptance agreement]<script>BODY_PROBE</script>Agree[/acceptance]';
$r=[];$projected=RecoveryContent::project(['tables'=>['posts'=>[['ID'=>91,'post_type'=>'wpcf7_contact_form']],'postmeta'=>[['post_id'=>91,'meta_key'=>'_form','meta_value'=>$form]]]],$r);
$template=$projected['tables']['postmeta'][0]['meta_value'];
safe_check(str_contains($template,'[text sample "<PLC>"]')&&!str_contains($template,'<script>')&&str_contains($template,'Agree'),'CF7 data/HTML boundary');
$manager=clone WPCF7_FormTagsManager::get_instance();$controls=$manager->replace_all($template);
safe_check(str_contains($controls,'&lt;PLC&gt;')&&!str_contains($controls,'<script>'),'CF7 generated input escaping');
$fields=get_option('wpmembers_fields');foreach($fields as &$f)if(($f[2]??'')==='first_name')$f['placeholder']='Reference https://source.invalid/path';unset($f);
$planned=OzekiResilience\M1\MemberHistory::preparedSettings(['wpmembers_fields'=>$fields],'https://source.invalid','https://destination.invalid');
safe_check($planned['wpmembers_fields']===$fields,'Member definitions relocated as site links');
$n=[];$safe=RecoveryContent::html('<!-- wp:review/attack /-->','pattern',$n);
$id=wp_insert_post(['post_type'=>'wp_block','post_status'=>'publish','post_title'=>'Temporary pattern boundary','post_content'=>$safe]);
try{
    update_post_meta($id,'_ozeki_resilience_m1_origin_url','https://source.invalid/?p=91');
    wp_update_post(['ID'=>$id,'post_content'=>html_entity_decode($safe,ENT_QUOTES|ENT_HTML5,'UTF-8')]);
    safe_check(!str_contains(do_blocks('<!-- wp:block {"ref":'.$id.'} /-->'),'<script>'),'Synced pattern reactivated after editing');
}finally{wp_delete_post($id,true);}
echo "Safe content: executable HTML, unknown shortcodes/blocks, useful text, idempotence, original PASS\n";
