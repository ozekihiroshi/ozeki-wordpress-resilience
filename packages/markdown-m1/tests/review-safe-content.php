<?php
// Run with wp eval-file on a disposable WordPress with the candidate activated.
use OzekiResilience\M1\RecoveryContent;
require_once WP_PLUGIN_DIR.'/ozeki-resilience/src/RecoveryContent.php';
function safe_check($ok,$why){if(!$ok)throw new RuntimeException($why);}
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
echo "Safe content: executable HTML, unknown shortcodes/blocks, useful text, idempotence, original PASS\n";
