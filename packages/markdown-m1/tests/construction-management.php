<?php
require __DIR__.'/construction-persistence.php';
define('OWR_CONSTRUCTION_ISOLATED',true);
require_once __DIR__.'/../src/Store.php';
require_once __DIR__.'/../src/SiteSnapshot.php';
require_once __DIR__.'/../src/ConstructionAdmin.php';
use OzekiResilience\M1\{ConstructionPreservation as P,ConstructionJournal as J,ConstructionOperations as O,ConstructionCapture,ConstructionAdmin,Store};
class ConstructionMemory {
    public array $objects=[];public bool $fail=false;
    function putObject($a){if($this->fail)throw new RuntimeException('offline');if(isset($this->objects[$a['Key']]))throw new RuntimeException('exists');return $this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>hash('sha256',$a['Body'])];}
    function getObject($a){$v=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$v['VersionId'])throw new RuntimeException('version');return $v;}
}
$options=[];$memory=new ConstructionMemory();$store=new Store($memory,['bucket'=>'isolated','prefix'=>'new-stream/']);$s=new P($store,'storage-A');
$files=['content.json'=>json_encode(['tables'=>['posts'=>[]]])];$manifest=['source_url'=>home_url()];
check($s->status()['transfer']==='initial_required','Missing baseline hidden');
$first=$s->initial(fn()=>[$manifest,$files]);$originals=$memory->objects;
check($s->status()['transfer']==='confirmed','Read-back not acknowledged');
check(rejects(fn()=>$s->initial(fn()=>[$manifest,$files])),'Baseline replaced');
$n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/posts','body'=>['title'=>'New']]);O::finish($n,['response'=>['id'=>19]]);
check($s->status()['transfer']==='pending','Unsaved operation called confirmed');
$memory->fail=true;check(rejects(fn()=>$s->flush()),'Outage accepted');
check(get_option(P::KEY)===$first,'Outage advanced confirmed boundary');
$memory->fail=false;$second=$s->flush();$after=$memory->objects;$again=$s->flush();
check($again['commit']===$second['commit']&&$memory->objects===$after,'Retry duplicated or changed objects');
foreach($originals as $key=>$body)check($memory->objects[$key]===$body,'Original overwritten');
check((new P($store,'storage-B'))->status()['transfer']==='destination_changed','Storage change hidden');
$observer=new ConstructionCapture();(new ReflectionMethod($observer,'effect'))->invoke($observer,'post',['id'=>19]);
check($s->status()['state']==='gap'&&rejects(fn()=>$s->flush()),'Unrecorded change committed');
$before=$options;ConstructionAdmin::authorize();check($before===$options,'Authorization changed state');
echo "PASS initial and daily confirmation through real Store with memory transport, outage/no acknowledgment, idempotent retry, original preservation, destination binding, unrecorded-change hold\n";
$scheduled=[];
function wp_next_scheduled($name){global $scheduled;return $scheduled[$name]??false;}
function wp_schedule_single_event($when,$name){global $scheduled;$scheduled[$name]=$when;return true;}
function determine_locale(){return $GLOBALS['test_locale']??'en_US';}
update_option('ozeki_resilience_m1_config',['protect'=>false,'setup_role'=>'source']);ConstructionAdmin::scheduleTransfer();
check($scheduled===[],'Protection-off scheduled a transfer');
update_option('ozeki_resilience_m1_config',['protect'=>true,'setup_role'=>'source']);ConstructionAdmin::scheduleTransfer();$once=$scheduled;ConstructionAdmin::scheduleTransfer();
check(count($scheduled)===1&&$once===$scheduled,'Duplicate transfer scheduled');
$scheduled=[];update_option('ozeki_resilience_m1_config',['protect'=>true,'setup_role'=>'recovery']);ConstructionAdmin::scheduleTransfer();
check($scheduled===[],'Recovery reader scheduled a write');
$GLOBALS['test_locale']='ja';check(str_contains(ConstructionAdmin::stateText('gap'),'未記録'),'Japanese gap text missing');
$GLOBALS['test_locale']='en_US';check(str_contains(ConstructionAdmin::stateText('gap'),'Unrecorded'),'English gap text missing');
echo "PASS event-driven single transfer, protection-off/recovery refusal, Japanese and English state labels\n";
