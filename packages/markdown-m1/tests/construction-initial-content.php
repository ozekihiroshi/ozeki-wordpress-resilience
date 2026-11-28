<?php
require __DIR__.'/construction-media.php';
use OzekiResilience\M1\{ConstructionContract as IC,ConstructionFollow as IFollower};
$c=$e['contract'];$c['endpoint']='initial-content';$c['output_type']=null;$c['target']=null;
$material=['input'=>$c['arguments'],'input_sha256'=>IC::hash($c['arguments']),'contract'=>$c,'contract_sha256'=>IC::hash($c)];
$map['deleted:12']=true;
$prepared=IFollower::initial($material,$map);
check(str_contains($prepared['arguments']['content'],'"id":99,"width":12'),'Initial block references differ from daily contract');
$changed=$material;$changed['input']['content'].='changed';
check(rejects(fn()=>IFollower::initial($changed,$map)),'Changed initial input accepted');
check(rejects(fn()=>IFollower::initial($material,[])),'Missing initial reference inferred');
$changed=$material;$changed['contract']['coverage']='incomplete';$changed['contract_sha256']=IC::hash($changed['contract']);
check(rejects(fn()=>IFollower::initial($changed,$map)),'Incomplete initial contract accepted');
check(IC::describe('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>'<!-- wp:quote --><blockquote><p>Quote</p></blockquote><!-- /wp:quote -->']])['coverage']==='complete','Previously supported quote lost during contract unification');
echo json_encode(['initial_content_contract_checks'=>5])."\n";
