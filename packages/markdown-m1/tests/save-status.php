<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Plugin.php';
function determine_locale(){return 'en_US';}
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
function show($history,$error='',$pending=[],$queue=[],$notice='',$qe=''){ob_start();OzekiResilience\M1\Plugin::renderSaveStatus($history,$error,$pending,$queue,$notice,$qe,true);return ob_get_clean();}
function ok($b,$m){if(!$b)throw new Exception($m);}
$h=[['sequence'=>56,'confirmed_at'=>'2026-10-25T00:00:00Z','original'=>['asset'=>'a'],'attributes'=>['title'=>'Trial','status'=>'publish']]];
$s=show($h);ok(str_contains($s,'>56<')&&str_contains($s,'No locally pending'),'Confirmed');
$s=show(null,'Denied<script>');ok(str_contains($s,'unknown')&&!str_contains($s,'No confirmed formal')&&!str_contains($s,'<script>'),'Read failure is unknown and escaped');
ok(str_contains(show([]),'No confirmed formal history'),'Empty');
$q=['x'=>['asset'=>'a','operation'=>'x','source'=>'PRIVATE-BODY','attributes'=>['title'=>'<trial>','post_type'=>'owr_comment','status'=>'deleted']]];
$s=show($h,'',['record'=>$h[0]],$q,'article error','queue error');ok(str_contains($s,'Locally pending operations: 2')&&str_contains($s,'Resume history required')&&str_contains($s,'queue error')&&str_contains($s,'article error')&&!str_contains($s,'PRIVATE-BODY')&&!str_contains($s,'<trial>'),'Pending metadata only');
ok(str_contains(show($h,'',[],$q),'No failure reason was recorded'),'Missing reason');
$s=show($h,'',[],[],'','old error');ok(!str_contains($s,'Resume history required')&&str_contains($s,'old error'),'Stale error not pending');
echo "PASS confirmed/empty/unreadable/pending/reasons/stale-error/escaping/no-body\n";

// Optional display metadata must not turn valid non-document history into a warning.
set_error_handler(function($severity,$message){throw new RuntimeException($message);});
foreach(['owr_comment','owr_form','owr_member','owr_table','owr_native','owr_acf','owr_media_access','future_kind']as $type){
    $row=['sequence'=>57,'original'=>['asset'=>'fixture'],'attributes'=>['post_type'=>$type]];
    $display=OzekiResilience\M1\Plugin::historyDisplay($row);
    ok($display['status']==='Not recorded','Missing state is not invented');
    ok(str_contains(show([$row]),$type==='owr_media_access'?'File access conditions':'Not recorded'),'Optional fields render');
    $row['attributes']+=['title'=>'','status'=>''];
    ok(OzekiResilience\M1\Plugin::historyDisplay($row)===['title'=>'','status'=>''],'Empty recorded values retained');
}
restore_error_handler();
echo "PASS optional history display metadata\n";
