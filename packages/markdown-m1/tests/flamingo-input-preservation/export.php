<?php
use OzekiResilience\M1\ReceiptInputs as R;
use OzekiResilience\M1\FlamingoReconstruction as F;
use OzekiResilience\M1\Plugin as P;
$d=['tables'=>['posts'=>[],'postmeta'=>[],'terms'=>[],'term_taxonomy'=>[],'term_relationships'=>[]]];
$store=(new P())->store();$rows=$store->history();$n=0;$sources=[];
foreach($rows as $row){$raw=$store->originalSource($row['original']);if($row['attributes']['post_type']==='owr_form_input'){R::replay($d,$raw,$row['attributes']);$sources[]=$raw;$n++;}elseif($row['attributes']['post_type']==='owr_form'){OzekiResilience\M1\FormHistory::replay($d,$raw,$row['attributes']);}}
$manifest=['source_url'=>home_url(),'through'=>count($rows)];$plan=F::plan($manifest,['content.json'=>json_encode($d)]);
$legacy=$d;unset($legacy['flamingo_inputs']);$legacyPlan=F::plan($manifest,['content.json'=>json_encode($legacy)]);
$base=['tables'=>$d['tables']];$baselineError=null;try{R::baseline($base);}catch(Throwable $e){$baselineError=$e->getMessage();}
echo json_encode(['inputs'=>R::all(),'formal_inputs'=>$n,'sources'=>$sources,'plan'=>$plan,'legacy'=>$legacyPlan,'baseline'=>$base['flamingo_inputs']??null,'baseline_error'=>$baselineError,'pending'=>get_option(OzekiResilience\M1\CommentHistory::PENDING,[])]);
