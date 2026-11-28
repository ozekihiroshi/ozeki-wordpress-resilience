<?php
spl_autoload_register(function($n){$p='OzekiResilience\\M1\\';if(str_starts_with($n,$p)){ $f='/tmp/product/src/'.substr($n,strlen($p)).'.php';if(is_file($f))require_once $f;}});
use OzekiResilience\M1\{Plugin,SiteSnapshot,ReceiptInputs,Store};
$store=(new Plugin())->store();$site=new SiteSnapshot($store);$data=(new ReflectionMethod($site,'data'))->invoke($site);
$manifest=['schema'=>'owr-site-snapshot-1','origin'=>'administrator_initial','source_url'=>home_url(),'source_upload_url'=>wp_upload_dir()['baseurl'],'through'=>$store->latestState()['through'],'wordpress'=>$GLOBALS['wp_version'],'plugins'=>['contact-form-7/wp-contact-form-7.php','flamingo/flamingo.php']];
$before=$data['flamingo_inputs'];$saved=$site->save(['content.json'=>Store::json($data)],$manifest);[$m,$files]=$site->load($saved['manifest'],true);$loaded=json_decode($files['content.json'],true);if($loaded['flamingo_inputs']!==$before)throw new RuntimeException('snapshot changed raw inputs');
// Actual previous main reader, renamed solely to permit comparison in this process.
require '/tmp/product/src/OldSiteSnapshot.php';$old=new OzekiResilience\M1\OldSiteSnapshot($store);$rejected=false;try{$old->load($saved['manifest'],true);}catch(RuntimeException $e){$rejected=str_contains($e->getMessage(),'Invalid separated site resources');}
if(!$rejected)throw new RuntimeException('old reader accepted new input contract');
unset($data['flamingo_inputs']);$legacy=$site->save(['content.json'=>Store::json($data)],$manifest);$site->load($legacy['manifest'],true);
echo json_encode(['new_snapshot_preserves_inputs'=>true,'old_reader_rejects'=>true,'legacy_snapshot_readable'=>true]);
