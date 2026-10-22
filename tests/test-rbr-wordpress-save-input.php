<?php
declare(strict_types=1);
require dirname(__DIR__).'/src/RbrWordPressSave.php';
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
$r=new ReflectionClass(Owr\RbrWordPressSave::class);$service=$r->newInstanceWithoutConstructor();$validate=$r->getMethod('validate');$validate->setAccessible(true);
$base=['operation_id'=>'test-operation','expected_sequence'=>0,'pages'=>[]];
foreach(['company','services','contact']as$role)$base['pages'][$role]=['title'=>'会社案内 '.$role,'slug'=>$role,'paragraphs'=>['A < B & C; content is escaped by projection']];
$validate->invoke($service,$base);$count=1;
$cases=[];$q=$base;$q['pages']['company']['title']='<script>alert(1)</script>';$cases[]=$q;
$q=$base;$q['pages']['company']['path']='/etc/passwd';$cases[]=$q;
$q=$base;$q['pages']['services']['slug']='company';$cases[]=$q;
$q=$base;$q['pages']['company']['paragraphs']=[['type'=>'arbitrary-html']];$cases[]=$q;
$q=$base;unset($q['pages']['contact']);$cases[]=$q;
$q=$base;$q['expected_sequence']='0';$cases[]=$q;
$q=$base;$q['operation_id']='../../escape';$cases[]=$q;
$q=$base;$q['pages']['company']['paragraphs']=array_fill(0,100,str_repeat('a',9000));$cases[]=$q;
foreach($cases as $input){try{$validate->invoke($service,$input);}catch(InvalidArgumentException){$count++;continue;}throw new RuntimeException('Unsafe input accepted');}
echo "Protected save input contracts: $count PASS\n";

