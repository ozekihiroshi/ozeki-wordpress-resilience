<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/ReceiptInputs.php';

/** Normal CF7 channel registration and Flamingo inbound add(); no private writes. */
final class FlamingoReconstruction {
    /** Bridge from an operation captured during CF7 registration; no form resubmission. */
    public static function recorded(array $entry,string $source,int $newForm,string $journal,bool $isolated=false): array {
        if(($entry['operation']??'')!=='flamingo-add'||($entry['state']??'')!=='registered')throw new \RuntimeException('A confirmed registration input is required');
        if(hash('sha256',wp_json_encode($entry['input']))!==($entry['input_sha256']??''))throw new \RuntimeException('Recorded receipt input changed');
        $input=$entry['input'];$result=$entry['result'];$raw=wp_json_encode($input['arguments']);
        $plan=['schema'=>'owr-normal-flamingo-registration-2','source_url'=>$source,'through'=>$entry['sequence'],'held'=>[],
            'receipts'=>[['origin_id'=>$result['id'],'form_origin_id'=>$input['form_id'],'input'=>$input['arguments'],'input_json'=>$raw,
                'input_sha256'=>hash('sha256',$raw),'expected'=>$result['receipt'],'dependencies'=>$input['dependencies']]]];
        return self::run($plan,[(string)$input['form_id']=>$newForm],$journal,$isolated);
    }
    private static function plain(mixed $v): void {
        if(is_array($v)){foreach($v as $child)self::plain($child);return;}
        if(!is_scalar($v)&&$v!==null)throw new \RuntimeException('Unsupported object in receipt');
    }
    public static function plan(array $manifest,array $files): array {
        $d=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        $meta=[];foreach($d['tables']['postmeta'] as $m)$meta[(int)$m['post_id']][$m['meta_key']][]=$m['meta_value'];
        $out=['schema'=>'owr-normal-flamingo-registration-2','source_url'=>$manifest['source_url'],'through'=>$manifest['through'],'receipts'=>[],'held'=>[]];
        foreach($d['tables']['posts'] as $p){
            if($p['post_type']!=='flamingo_inbound')continue;$id=(int)$p['ID'];
            try {
                if(!in_array($p['post_status'],['publish','flamingo-spam'],true))throw new \RuntimeException('Receipt lifecycle is not a new registration; held.');
                $r=$d['flamingo_inputs'][(string)$id]??null;
                if(!$r)throw new \RuntimeException('Legacy stored output only: original registration input is unavailable; not inferred.');
                ReceiptInputs::validate($r);
                if($r['receipt_origin_id']!==$id)throw new \RuntimeException('Input identity mismatch.');
                if(($p['post_status']==='flamingo-spam')!==$r['result']['spam'])throw new \RuntimeException('Receipt status changed after registration; original input cannot reproduce that later operation.');
                $frozen=[];foreach($r['items'] as $item)if((int)$item['post']['ID']===$id)foreach($item['meta'] as $m)$frozen[$m['meta_key']][]=$m['meta_value'];
                $stored=$meta[$id]??[];ksort($stored);ksort($frozen);
                if($stored!==$frozen)throw new \RuntimeException('Receipt metadata changed after recorded registration; later input is unavailable and is not inferred.');
                $a=json_decode($r['input_json'],true,512,JSON_THROW_ON_ERROR);self::plain($a);
                $out['receipts'][]=['origin_id'=>$id,'form_origin_id'=>$r['form_origin_id'],'input'=>$a,'input_json'=>$r['input_json'],'input_sha256'=>$r['input_sha256'],'expected'=>$r['result'],'dependencies'=>$r['dependencies']];
            }catch(\Throwable $e){$out['held'][(string)$id]=$e->getMessage();}
        }
        return $out;
    }
    public static function run(array $plan,array $formMap,string $journal,bool $isolated=false): array {
        if(!$isolated||($plan['schema']??'')!=='owr-normal-flamingo-registration-2'||untrailingslashit($plan['source_url'])===untrailingslashit(home_url()))throw new \RuntimeException('Isolated destination and valid plan required');
        if(!current_user_can('flamingo_edit_inbound_messages')||!current_user_can('wpcf7_edit_contact_forms'))throw new \RuntimeException('Prepared administrator permissions required');
        if(!class_exists('Flamingo_Inbound_Message')||!function_exists('wpcf7_flamingo_add_channel'))throw new \RuntimeException('Prepare CF7 and Flamingo before reconstruction');
        $s=['state'=>'registering','through'=>$plan['through'],'receipts'=>[],'channels'=>[],'verified'=>[],'held'=>$plan['held'],'failed'=>[]];
        $identity=hash('sha256',wp_json_encode([$plan,$formMap,home_url()]));
        $f=fopen($journal,'c+');if(!$f||!flock($f,LOCK_EX|LOCK_NB))throw new \RuntimeException('Private registration journal is busy');chmod($journal,0600);
        try {
        $previous=stream_get_contents($f);
        if($previous!==''){$s=json_decode($previous,true,512,JSON_THROW_ON_ERROR);if(($s['identity']??'')!==$identity)throw new \RuntimeException('Different reconstruction attempt; journal unchanged');}
        else {$s['identity']=$identity;$s['attempting']=[];}
        $record=static function()use(&$s,$f){$raw=wp_json_encode($s);rewind($f);if(fwrite($f,$raw)!==strlen($raw)||!ftruncate($f,strlen($raw))||!fflush($f))throw new \RuntimeException('Cannot persist registration journal');};$record();
        foreach($plan['receipts'] as $item){
            $old=(string)$item['origin_id'];$new=null;
            if(isset($s['attempting'][$old])&&!isset($s['receipts'][$old])){$s['held'][$old]='Interrupted registration: outcome unknown; not registered again automatically';$record();continue;}
            try {
                $fid=(int)($formMap[(string)$item['form_origin_id']]??0);$form=$fid?wpcf7_contact_form($fid):null;
                if(!$form){$s['held'][$old]='Prepared new CF7 form mapping missing';$record();continue;}
                // Same channel choice as normal CF7 submission; do not write _flamingo ourselves.
                foreach($item['dependencies'] as $plugin=>$version)FormHistory::checkDependency($plugin,$version);
                $pointer=get_post_meta($fid,'_flamingo',true);
                $tid=isset($pointer['channel'])?(int)$pointer['channel']:wpcf7_flamingo_add_channel($form->name(),$form->title());
                $term=$tid?get_term($tid,\Flamingo_Inbound_Message::channel_taxonomy):null;
                if(!$term||is_wp_error($term))throw new \RuntimeException('Normal channel registration failed');
                if(hash('sha256',$item['input_json'])!==$item['input_sha256']||json_decode($item['input_json'],true,512,JSON_THROW_ON_ERROR)!==$item['input'])throw new \RuntimeException('Immutable input mismatch.');
                $a=$item['input'];self::plain($a);$a['channel']=$term->slug;
                // Only the new channel identity changes; no slashing or output repair.
                if(isset($s['receipts'][$old]))$new=(int)$s['receipts'][$old];
                else {
                    $s['attempting'][$old]=true;$record();
                    $capture=null;
                    if(defined('OWR_CONSTRUCTION_ISOLATED')&&OWR_CONSTRUCTION_ISOLATED===true){
                        require_once __DIR__.'/ConstructionOperations.php';
                        $capture=ConstructionOperations::begin('flamingo-add',['form_id'=>$fid,'arguments'=>$a,'dependencies'=>$item['dependencies']]);
                    }
                    $message=\Flamingo_Inbound_Message::add($a);$new=$message->id();
                    if($capture!==null&&$new)ConstructionOperations::finish($capture,['id'=>$new,'receipt'=>ReceiptInputs::result($new)]);
                }
                if(!$new)throw new \RuntimeException('Normal inbound registration failed');
                $s['receipts'][$old]=$new;$s['channels'][(string)$item['form_origin_id']]=['form_id'=>$fid,'term_id'=>$term->term_id,'slug'=>$term->slug];$record();
                $read=ReceiptInputs::result($new);$expected=$item['expected'];$expected['channel']=$term->slug;
                // When no timestamp was supplied, normal registration chooses now.
                if(!isset($a['timestamp']))unset($read['received_gmt'],$expected['received_gmt']);
                if($read!==$expected)throw new \RuntimeException('Normal registration result differs from source registration; no repair attempted');
                unset($s['failed'][$old]);if(!in_array($old,$s['verified'],true))$s['verified'][]=$old;$record();
            }catch(\Throwable $e){$s['failed'][$old]=['created_id'=>$new,'reason'=>$e->getMessage()];$record();}
        }
        $s['state']=$s['failed']?'completed_with_failures':($s['held']?'completed_with_holds':'completed');$record();return $s;
        } finally {flock($f,LOCK_UN);fclose($f);}
    }
}
