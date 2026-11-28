<?php
$plan=json_decode(file_get_contents('/tmp/input-plan.json'),true);$map=json_decode(file_get_contents('/tmp/form-map.json'),true);
$plan['receipts']=array_slice($plan['receipts'],0,1);
$r=OzekiResilience\M1\FlamingoReconstruction::run($plan,$map,'/tmp/receipt-interrupt-journal.json',true);echo json_encode($r);
