<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Plugin.php';
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
eval('namespace Owr\\M1; class Store { public static function json($v){return json_encode($v);} }');
function render($a,$s,$list=[]){ob_start();Owr\M1\Plugin::renderSiteResult($a,$s,[],$list);return ob_get_clean();}
function ok($v,$m){if(!$v)throw new Exception($m);}
$ref=['key'=>'site-snapshots/test/manifest.json','version'=>'v1','sha256'=>'abc'];$s=['manifest'=>$ref,'through'=>56,'at'=>'2026-10-24T13:20:00Z','posts'=>22,'files'=>0];$list=[['ref'=>$ref,'through'=>33,'origin'=>'confirmed_s3']];
$h=render([],$s,$list);ok(str_contains($h,'Success')&&str_contains($h,'34–56 (23 records)')&&str_contains($h,'>22<')&&str_contains($h,'Files written / replaced'),'Legacy success');
$h=render(['status'=>'failed','manifest'=>$ref,'at'=>'now','error'=>'<script>alert(1)</script>'],$s,$list);$summary=explode('<details>',$h)[0];ok(str_contains($summary,'Failed')&&!str_contains($summary,'>22<')&&!str_contains($summary,'Applied formal history through'),'Failure cannot claim old success');ok(!str_contains($h,'<script>')&&str_contains($h,'&lt;script&gt;'),'Escape');ok(str_contains($h,'last_successful_recovery'),'Preserve JSON');
$h=render(['status'=>'running','at'=>'now'],$s);ok(str_contains($h,'completion not confirmed'),'Interrupted');
$h=render([],[]);ok(str_contains($h,'No site-wide recovery recorded'),'Empty');
$h=render([],$s);ok(str_contains($h,'Not available'),'Missing checkpoint does not invent range');
$s['through']=33;$h=render(['status'=>'success']+$s,$s,$list);ok(str_contains($h,'>None<'),'No tail');
$s['checkpoint_through']=33;$s['requested_through']=68;$s['through']=68;$h=render(['status'=>'success']+$s,$s);ok(str_contains($h,'Requested formal history end')&&str_contains($h,'34–68 (35 records)'),'Explicit boundary retained without live snapshot listing');
echo "PASS success/legacy/failure/unfinished/empty/missing-point/no-tail/escaping and preserved JSON\n";
