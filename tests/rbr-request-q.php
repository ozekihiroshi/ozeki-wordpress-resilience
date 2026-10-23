<?php
declare(strict_types=1);
require __DIR__.'/../src/RbrGenerationCoordinator.php';
require __DIR__.'/../src/RbrWordPressSave.php';
use Owr\RbrWordPressSave as Save;
$c=['roles'=>['company'=>'company','services'=>'services','contact'=>'contact'],'images'=>['logo'=>['sha256'=>str_repeat('a',64),'width'=>2,'height'=>2,'alt'=>'']],'relations'=>[['from'=>'company','to'=>'logo','type'=>'image','position'=>0],['from'=>'company','to'=>'services','type'=>'link','position'=>1]]];
$i=['operation_id'=>'request-001','expected_sequence'=>0,'pages'=>[]];foreach($c['roles'] as $role=>$id)$i['pages'][$role]=['title'=>$role,'slug'=>$role,'paragraphs'=>['日本語 <script>text only</script>','Second paragraph']];
function check(bool $ok,string $name):void{if(!$ok)throw new RuntimeException($name);echo "PASS $name\n";}
$q=Save::expectedFromRequest($i,$c);check($q===Save::expectedFromRequest($i,$c),'deterministic from request');check($q['pages']['company']['paragraphs']===$i['pages']['company']['paragraphs'],'plain text preserved without rendering');check($q['images']===$c['images']&&$q['relations']===$c['relations'],'enrolled media and relations preserved');
$other=$i;$other['operation_id']='request-002';$other['expected_sequence']=1;check($q===Save::expectedFromRequest($other,$c),'operation metadata does not alter logical expectation');
$other['pages']['contact']['title']='Changed';check(Save::expectedFromRequest($other,$c)['pages']['contact']['title']==='Changed'&&$q['pages']['contact']['title']==='contact','request edits reflected without mutating prior Q');
$bad=$i;$bad['pages']['company']['paragraphs']=[' '];try{Save::expectedFromRequest($bad,$c);throw new RuntimeException('blank accepted');}catch(InvalidArgumentException){echo "PASS blank business text rejected\n";}
$bad=$c;$bad['relations'][1]['position']=3;try{Save::expectedFromRequest($i,$bad);throw new RuntimeException('outside relation accepted');}catch(InvalidArgumentException){echo "PASS outside relationship rejected\n";}
$reflection=new ReflectionClass(Save::class);$object=$reflection->newInstanceWithoutConstructor();$reflection->getProperty('seed')->setValue($object,[['id'=>'request-expectation']]);
try{$reflection->getMethod('expectedContext')->invoke($object);throw new RuntimeException('reserved accepted');}catch(RuntimeException $e){check($e->getMessage()==='Reserved expectation asset identity','reserved Q namespace cannot collide with enrolled assets');}
