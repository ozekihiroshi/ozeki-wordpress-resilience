<?php
$plan=json_decode(file_get_contents('/tmp/input-plan.json'),true);$map=json_decode(file_get_contents('/tmp/form-map.json'),true);
$r=OzekiResilience\M1\FlamingoReconstruction::run($plan,$map,'/tmp/receipt-journal.json',true);echo json_encode($r);
