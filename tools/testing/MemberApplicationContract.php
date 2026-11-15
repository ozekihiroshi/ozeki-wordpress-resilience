<?php
declare(strict_types=1);

/** Development-only oracle. Never used to filter or rewrite archived originals. */
final class MemberApplicationContract
{
    public const VERSION='wp-members-application-2';
    public const TYPES=['text','textarea','email','url','password','checkbox','select','radio','multiselect','number','date','hidden'];
    public const USER=['ID','user_login','user_pass','user_nicename','user_email','user_url','user_registered','user_status','display_name'];
    public const META=['first_name','last_name','nickname','description','active','_wpmem_user_confirmed','_wpmem_activation_confirm'];

    public static function settings(): array {
        $pair=['post'=>'number','page'=>'number'];
        return ['wpmembers_settings'=>['version'=>'text','db_version'=>'version','block'=>$pair,'show_excerpt'=>$pair,'show_reg'=>$pair,'show_login'=>$pair,'autoex'=>['post'=>['enabled'=>'number','length'=>'number-empty'],'page'=>['enabled'=>'number','length'=>'number-empty']],'mod_reg'=>'number','notify'=>'number','warnings'=>'number','attrib'=>'number','user_pages'=>['profile'=>'page','register'=>'page','login'=>'page'],'shortcodes'=>['enable_field'=>'number']], 'wpmembers_dialogs'=>array_fill_keys(['restricted_msg','user','email','success','editsuccess','pwdchangerr','pwdchangesuccess','pwdreseterr','pwdresetsuccess'],'text'),'wpmembers_tos'=>'text'];
    }
    public static function fieldRules(string $type): array {
        $r=[0=>'number',1=>'text',2=>'text',3=>'text',4=>'text',5=>'text',6=>'text','profile'=>'bool','native'=>'bool','value'=>'plain','values'=>'plain'];
        if(in_array($type,['text','textarea','email','url','password','number','date'],true))$r['placeholder']='text';
        if(in_array($type,['text','email','url','password','number','date'],true))$r+=['pattern'=>'text','title'=>'text'];
        if(in_array($type,['number','date'],true))$r+=['min'=>'number-empty','max'=>'number-empty'];
        if($type==='textarea')$r+=['rows'=>'number-empty','cols'=>'number-empty'];
        if(in_array($type,['select','radio','multiselect'],true))$r[7]='strings';
        if($type==='multiselect')$r[8]='delimiter';
        if($type==='checkbox')$r+=[7=>'text',8=>'yes-no','checkbox_label'=>'number'];
        if($type==='hidden')$r[7]='text';
        return $r;
    }
    private static function plain(mixed $v): bool {if(is_array($v)){foreach($v as $x)if(!self::plain($x))return false;return true;}return is_scalar($v)||$v===null;}
    private static function valid(mixed $v,string $type): bool {
        return match($type){
            'text'=>is_string($v), 'bool'=>in_array($v,[true,false,0,1,'0','1'],true),
            'number'=>is_int($v)||is_float($v)||(is_string($v)&&is_numeric($v)),
            'number-empty'=>$v===''||is_int($v)||(is_string($v)&&is_numeric($v)),
            'version'=>(is_string($v)||is_int($v)||is_float($v))&&preg_match('/^[0-9]+(?:\.[0-9]+)*$/D',(string)$v)===1,
            'page'=>is_string($v)||(is_int($v)&&$v>=0),
            'strings'=>is_array($v)&&!array_filter($v,fn($x)=>!is_string($x)),
            'delimiter'=>in_array($v,[',','|'],true),'yes-no'=>in_array($v,['y','n'],true),
            'plain'=>self::plain($v),default=>false};
    }
    private static function select(mixed $v,array|string $rules,string $path,array &$excluded): mixed {
        if(is_string($rules)){
            if(!self::valid($v,$rules))throw new RuntimeException('invalid-input:'.$path);
            return $rules==='bool'?(bool)(int)$v:$v;
        }
        if(!is_array($v))throw new RuntimeException('invalid-input:'.$path);
        $out=[];foreach($v as $key=>$value){
            if(!array_key_exists($key,$rules)){$excluded[]=$path.'.'.$key;continue;}
            $out[$key]=self::select($value,$rules[$key],$path.'.'.$key,$excluded);
        }return $out;
    }
    public static function safeMeta(string $key): bool {return !preg_match('/password|pass$|session|capabilities|user_level|activation_key|application|^_(?:owr|ozeki_resilience)_/i',$key);}

    /** Expected requirements come from raw captured membership, never the product projection. */
    public static function expected(array $raw): array {
        if(!is_string($raw['version']??null)||!is_array($raw['settings']??null)||!is_array($raw['users']??null))throw new RuntimeException('invalid-input:membership');
        $excluded=[];$out=['version'=>$raw['version'],'settings'=>[],'users'=>[]];$keys=self::META;$seen=[];
        foreach($raw['settings'] as $key=>$v){
            if($key==='wpmembers_fields'){
                if($v===false){$out['settings'][$key]=false;continue;}
                if(!is_array($v))throw new RuntimeException('invalid-input:settings.wpmembers_fields');
                $out['settings'][$key]=[];
                foreach($v as $i=>$f){
                    $path='settings.wpmembers_fields.'.$i;
                    if(!is_array($f)||!isset($f[2],$f[3])||!is_string($f[2]))throw new RuntimeException('invalid-input:'.$path);
                    if(!in_array($f[3],self::TYPES,true)){$excluded[]=$path;continue;}
                    if(isset($seen[$f[2]]))throw new RuntimeException('duplicate-field:'.$path);$seen[$f[2]]=true;
                    foreach([0,1,2,3,4,5,6] as $required)if(!array_key_exists($required,$f))throw new RuntimeException('missing-definition:'.$path.'.'.$required);
                    if(in_array($f[3],['select','radio','multiselect','checkbox','hidden'],true)&&!array_key_exists(7,$f))throw new RuntimeException('missing-definition:'.$path.'.7');
                    $out['settings'][$key][]=self::select($f,self::fieldRules($f[3]),$path,$excluded);
                    if(self::safeMeta($f[2]))$keys[]=$f[2];
                }
            }elseif(isset(self::settings()[$key]))$out['settings'][$key]=$v===false?false:self::select($v,self::settings()[$key],'settings.'.$key,$excluded);
            else $excluded[]='settings.'.$key;
        }
        foreach($raw['users'] as $id=>$entry){
            if(!is_array($entry)||!is_array($entry['user']??null)||!is_array($entry['meta']??null)||(int)$id<=0||($entry['user']['ID']??null)!==(string)$id)throw new RuntimeException('invalid-identity:users.'.$id);
            foreach(self::USER as $key)if(!array_key_exists($key,$entry['user'])||!is_string($entry['user'][$key]))throw new RuntimeException('invalid-identity:users.'.$id.'.'.$key);
            $out['users'][$id]=['user'=>array_intersect_key($entry['user'],array_flip(self::USER)),'meta'=>[]];
            foreach($entry['meta'] as $key=>$v){
                if(!in_array($key,$keys,true)){$excluded[]='users.'.$id.'.meta.'.$key;continue;}
                if(!is_array($v)||!self::plain($v))throw new RuntimeException('invalid-input:users.'.$id.'.meta.'.$key);
                $out['users'][$id]['meta'][$key]=$v;
            }
        }
        return ['data'=>$out,'excluded'=>$excluded];
    }
    private static function diff(mixed $expected,mixed $actual,string $path,array &$errors): void {
        if(is_array($expected)&&is_array($actual)){
            foreach($expected as $k=>$v){if(!array_key_exists($k,$actual))$errors[]=['path'=>$path.'.'.$k,'code'=>'missing'];else self::diff($v,$actual[$k],$path.'.'.$k,$errors);}
            foreach($actual as $k=>$v)if(!array_key_exists($k,$expected))$errors[]=['path'=>$path.'.'.$k,'code'=>'unexpected'];
        }elseif($expected!==$actual)$errors[]=['path'=>$path,'code'=>'changed'];
    }
    /** Actual values are not filtered: doing so could hide unexpected restoration. */
    public static function compare(array $raw,array $actual,array $preparedSettings=[]): array {
        try{$expect=self::expected($raw);}catch(RuntimeException $e){return ['contract'=>self::VERSION,'pass'=>false,'errors'=>[['code'=>'invalid-source','path'=>$e->getMessage()]]];}
        $e=$expect['data'];
        if($preparedSettings){
            $wanted=$preparedSettings;
            foreach($e['settings'] as $key=>$value){
                if($value===false)continue;
                if($key==='wpmembers_settings'){
                    unset($value['version'],$value['db_version']);
                    $wanted[$key]=array_replace_recursive($wanted[$key]??[],$value);
                }elseif($key==='wpmembers_dialogs')$wanted[$key]=array_replace($wanted[$key]??[],$value);
                else $wanted[$key]=$value;
            }
            $e['settings']=$wanted;
        }
        if(is_array($actual['settings']['wpmembers_fields']??null))foreach($actual['settings']['wpmembers_fields'] as &$f)foreach(['profile','native'] as $key)if(isset($f[$key])&&self::valid($f[$key],'bool'))$f[$key]=(bool)(int)$f[$key];unset($f);
        $errors=[];self::diff($e,$actual,'membership',$errors);
        return ['contract'=>self::VERSION,'stage'=>$preparedSettings?'prepared-destination-application':'projection-only','pass'=>!$errors,'errors'=>$errors,'excluded'=>$expect['excluded']];
    }
}
