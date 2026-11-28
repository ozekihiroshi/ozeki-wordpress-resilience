<?php
define('ABSPATH',__DIR__.'/');
// A minimal deterministic HTML boundary; full WordPress behavior is a separate integration check.
function wp_kses_post($s){return preg_replace('~<script>.*?</script>~s','',$s);}
require __DIR__.'/../src/ConstructionSafety.php';
use OzekiResilience\M1\ConstructionSafety as S;
$plain=['forms'=>['forms'=>[]],'tail'=>[]];
foreach(['flamingo.add','members.profile','tablepress.import','acf.import','markdown.import'] as $endpoint)$plain['tail'][]=['state'=>'registered','sequence'=>count($plain['tail'])+1,'contract'=>['coverage'=>'complete','endpoint'=>$endpoint,'arguments'=>['value'=>'<PLC> [example] C:\\manual\\42']]];
$before=serialize($plain);
if(S::inspect($plain)!==[]||serialize($plain)!==$before)throw new RuntimeException('Structured information treated as HTML');
$bad=$plain;$bad['tail'][]=['state'=>'registered','sequence'=>6,'contract'=>['coverage'=>'complete','endpoint'=>'/contact-form-7/v1/contact-forms','arguments'=>['form'=>'<script>run()</script>','additional_settings'=>'on_sent_ok: run()']]];
$original=serialize($bad);if(!S::inspect($bad)||serialize($bad)!==$original)throw new RuntimeException('Unsafe application accepted or original rewritten');
$good=['form'=>'[text your-name]','additional_settings'=>'skip_mail: on'];if(S::form($good))throw new RuntimeException('Normal form refused');
$bad=['tail'=>[['state'=>'registered','sequence'=>1,'contract'=>['coverage'=>'complete','endpoint'=>'/wp/v2/users','arguments'=>['roles'=>['administrator']]]]]];
if(!S::inspect($bad))throw new RuntimeException('Recorded contract was treated as permission for an arbitrary REST route');
$bad['tail'][0]['contract']=['coverage'=>'complete','endpoint'=>'members.create','arguments'=>['body'=>['role'=>'administrator']]];
if(!S::inspect($bad))throw new RuntimeException('Archived privileges accepted');
echo "PASS form HTML/settings held without rewriting; structured and Markdown originals unchanged\n";
