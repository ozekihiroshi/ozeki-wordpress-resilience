<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Plugin.php';
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
$testLocale='en_US';
function determine_locale(){global $testLocale;return $testLocale;}
eval('namespace OzekiResilience\\M1; class Store { public static function json($v){return json_encode($v);} }');
function render($a,$s,$list=[]){ob_start();OzekiResilience\M1\Plugin::renderSiteResult($a,$s,[],$list);return ob_get_clean();}
function ok($v,$m){if(!$v)throw new Exception($m);}
$ref=['key'=>'site-snapshots/test/manifest.json','version'=>'v1','sha256'=>'abc'];$s=['manifest'=>$ref,'through'=>56,'at'=>'2026-10-24T13:20:00Z','posts'=>22,'files'=>0];$list=[['ref'=>$ref,'through'=>33,'origin'=>'confirmed_s3']];
$h=render([],$s,$list);ok(str_contains($h,'Success')&&str_contains($h,'34–56 (23 records)')&&str_contains($h,'>22<')&&str_contains($h,'Files written / replaced'),'Legacy success');
$h=render(['status'=>'failed','manifest'=>$ref,'at'=>'now','error'=>'<script>alert(1)</script>'],$s,$list);$summary=explode('<details>',$h)[0];ok(str_contains($summary,'Failed')&&!str_contains($summary,'>22<')&&!str_contains($summary,'Applied formal history through'),'Failure cannot claim old success');ok(!str_contains($h,'<script>')&&str_contains($h,'&lt;script&gt;'),'Escape');ok(str_contains($h,'last_successful_recovery'),'Preserve JSON');
$h=render(['status'=>'running','at'=>'now'],$s);ok(str_contains($h,'completion not confirmed'),'Interrupted');
ok(str_contains($h,'previous recovery is still running'),'Interrupted next action');
$testLocale='ja';$h=render(['status'=>'running','at'=>'now'],$s);ok(str_contains($h,'同じ復旧ポイント・履歴番号'),'Japanese interrupted next action');$testLocale='en_US';
$h=render([],[]);ok(str_contains($h,'No site-wide recovery recorded'),'Empty');
$h=render([],$s);ok(str_contains($h,'Not available'),'Missing checkpoint does not invent range');
$s['through']=33;$h=render(['status'=>'success']+$s,$s,$list);ok(str_contains($h,'>None<'),'No tail');
$s['checkpoint_through']=33;$s['requested_through']=68;$s['through']=68;$h=render(['status'=>'success']+$s,$s);ok(str_contains($h,'Requested formal history end')&&str_contains($h,'34–68 (35 records)'),'Explicit boundary retained without live snapshot listing');
echo "PASS success/legacy/failure/unfinished/empty/missing-point/no-tail/escaping and preserved JSON\n";

foreach(['en_US','ja'] as $testLocale){
 ob_start();OzekiResilience\M1\Plugin::renderSiteResult([],[],['excluded_files'=>[['item'=>'uploads/<private>.pdf']]]);$h=ob_get_clean();
 ok(str_contains($h,$testLocale==='ja'?'自動保全の対象外ファイル':'Files outside automatic protection'),'Visible exclusions in user language');
 ok(str_contains($h,'&lt;private&gt;')&&!str_contains($h,'<private>'),'Excluded paths escaped');
 $missing=$s+['application_report'=>['missing_originals'=>['uploads/<missing>.pdf'],'not_applied'=>[],'count'=>0,'rules'=>'fixture']];
 $h=render([],$missing);
 ok(str_contains($h,$testLocale==='ja'?'復旧は未完了':'Recovery is incomplete'),'Missing originals prominently distinguished from unapplied preserved data');
 ok(!str_contains($h,'<strong>Success</strong>')&&!str_contains($h,'<strong>成功</strong>'),'Missing originals are not labelled successful');
 ok(str_contains($h,'&lt;missing&gt;')&&!str_contains($h,'<missing>'),'Missing paths escaped');
}
