<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Immutable CF7 registration input, separately from its normal Flamingo result. */
final class ReceiptInputs {
    public const SCHEMA='owr-flamingo-input-1';
    public const SNAPSHOT_FORMAT='owr-separated-assets-flamingo-input-1';
    public const PREFIX='ozeki_resilience_receipt_input_';
    private ?string $active=null;
    public function boot(): void {
        add_filter('wpcf7_flamingo_inbound_message_parameters',[$this,'stage'],PHP_INT_MAX);
        add_filter('flamingo_add_inbound',[$this,'observe'],PHP_INT_MAX);
        add_action('init',function(){try{$this->resume();}catch(\Throwable $e){update_option('ozeki_resilience_m1_comment_error',$e->getMessage(),false);}},99);
        add_action('admin_notices',function(){if(current_user_can('manage_options')&&self::pending())echo '<div class="notice notice-warning"><p>'.esc_html__('Resilience: receipt inputs await registration confirmation or formal history. Unconfirmed inputs are not recovery candidates.','ozeki-resilience').'</p></div>';});
    }
    private static function json(array $a): string {
        $plain=static function($v)use(&$plain){if(is_array($v)){foreach($v as $child)$plain($child);}elseif(!is_scalar($v)&&$v!==null)throw new \RuntimeException('Unsupported object-valued receipt input.');};$plain($a);
        $s=json_encode($a,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
        if(strlen($s)>5*1024*1024)throw new \RuntimeException('Receipt input exceeds 5 MiB; not confirmed.');
        return $s;
    }
    private static function save(string $op,array $r): void {
        $key=self::PREFIX.$op;
        if(get_option($key,null)===$r)return;
        if(!update_option($key,$r,false))throw new \RuntimeException('Cannot persist receipt input state.');
    }
    public function stage(array $args): array {
        if(empty((new Plugin())->config()['protect']))return $args;
        return SaveFailure::run('Receipt input capture',function()use($args){
            if($this->active!==null)throw new \RuntimeException('Nested CF7 receipt registration is not supported.');
            $form=\WPCF7_ContactForm::get_current();if(!$form)throw new \RuntimeException('Missing CF7 input identity.');
            $op=wp_generate_uuid4();$raw=self::json($args);
            $r=['state'=>'staged','operation'=>$op,'form_origin_id'=>$form->id(),'input_json'=>$raw,'input_sha256'=>hash('sha256',$raw),'observed'=>false];
            if(!add_option(self::PREFIX.$op,$r,'',false))throw new \RuntimeException('Cannot stage receipt input.');
            $this->active=$op;return $args;
        });
    }
    public function observe(array $args): array {
        if($this->active===null)return $args;
        $r=get_option(self::PREFIX.$this->active);
        if($r['observed'])throw new \RuntimeException('Repeated Flamingo registration; input remains unconfirmed.');
        // Flamingo adds its normal default arguments before this filter.
        $r['registration_json']=self::json($args);$r['registration_sha256']=hash('sha256',$r['registration_json']);
        $r['observed']=true;self::save($this->active,$r);return $args;
    }
    public static function result(int $id): array {
        $m=new \Flamingo_Inbound_Message($id);$r=[];
        foreach(['subject','from','from_name','from_email','fields','meta','akismet','recaptcha','spam_log','consent','spam','channel','submission_status'] as $k)$r[$k]=$m->$k;
        $r['received_gmt']=get_post($id)->post_date_gmt;$r['posted_data_hash']=get_post_meta($id,'_hash',true);return $r;
    }
    public function completed(int $id,int $form,array $items): bool {
        if($this->active===null)return false;
        $op=$this->active;$r=get_option(self::PREFIX.$op);
        if(!$id||!$r['observed']||$r['form_origin_id']!==$form||get_post_type($id)!=='flamingo_inbound')throw new \RuntimeException('Cannot confirm receipt registration identity.');
        $r['receipt_origin_id']=$id;$r['result']=self::result($id);$r['items']=$items;$r['state']='registered';
        $r['dependencies']=[];foreach(FormHistory::DEPENDENCIES as $p)$r['dependencies'][$p]=get_file_data(WP_PLUGIN_DIR.'/'.$p,['Version'=>'Version'])['Version'];
        self::save($op,$r);$this->active=null;self::submit($r);return true;
    }
    private static function submit(array $r): void {
        $id=$r['receipt_origin_id'];$payload=$r;unset($payload['state'],$payload['observed']);$payload['schema']=self::SCHEMA;
        $attrs=['post_type'=>'owr_form_input','content_format'=>'form-json','origin_id'=>$id,'title'=>$r['result']['subject'],'status'=>'registered','dependencies'=>$r['dependencies']];
        (new CommentHistory())->enqueueOnce('receipt-input-'.$r['operation'],self::json($payload),$attrs,$r['operation']);
    }
    public static function committed(array $entry): void {
        if(($entry['attributes']['post_type']??'')!=='owr_form_input')return;
        $op=$entry['operation'];$r=get_option(self::PREFIX.$op);
        if(!$r||$r['input_sha256']!==json_decode($entry['source'],true,512,JSON_THROW_ON_ERROR)['input_sha256'])throw new \RuntimeException('Receipt input confirmation mismatch.');
        $r['state']='confirmed';self::save($op,$r);
    }
    public static function all(): array {
        global $wpdb;$out=[];
        $keys=$wpdb->get_col($wpdb->prepare("SELECT option_name FROM {$wpdb->options} WHERE option_name LIKE %s",$wpdb->esc_like(self::PREFIX).'%'));
        foreach($keys as $k){$r=get_option($k);if(is_array($r))$out[]=$r;}return $out;
    }
    public static function pending(): array {return array_values(array_filter(self::all(),fn($r)=>$r['state']!=='confirmed'));}
    public function resume(): void {
        if(empty((new Plugin())->config()['protect']))return;
        foreach(self::all() as $r)if($r['state']==='registered')self::submit($r);
    }
    public static function baseline(array &$data): void {
        $data['flamingo_inputs']=[];
        foreach(self::all() as $r){
            if($r['state']!=='confirmed')throw new \RuntimeException('Resolve unconfirmed receipt inputs before a new initial save.');
            $payload=$r;unset($payload['state'],$payload['observed']);$payload['schema']=self::SCHEMA;
            $data['flamingo_inputs'][(string)$r['receipt_origin_id']]=$payload;
        }
    }
    public static function validate(array $r): void {
        if(($r['schema']??'')!==self::SCHEMA||!is_string($r['input_json']??null)||hash('sha256',$r['input_json'])!==($r['input_sha256']??null)||!is_array($r['result']??null)||!is_array($r['items']??null)||(int)($r['receipt_origin_id']??0)<=0||(int)($r['form_origin_id']??0)<=0)throw new \RuntimeException('Invalid immutable receipt input.');
        $a=json_decode($r['input_json'],true,512,JSON_THROW_ON_ERROR);if(!is_array($a))throw new \RuntimeException('Invalid receipt argument map.');
        if(!is_string($r['registration_json']??null)||hash('sha256',$r['registration_json'])!==($r['registration_sha256']??null)||!is_array($r['dependencies']??null))throw new \RuntimeException('Missing observed registration contract.');
    }
    public static function replay(array &$data,string $source,array $attrs): void {
        $r=json_decode($source,true,512,JSON_THROW_ON_ERROR);self::validate($r);
        if($r['receipt_origin_id']!==(int)$attrs['origin_id'])throw new \RuntimeException('Receipt identity mismatch.');
        FormHistory::replay($data,Store::json(['schema'=>'owr-form-1','items'=>$r['items']]),$attrs);
        $data['flamingo_inputs'][(string)$r['receipt_origin_id']]=$r;
    }
}
