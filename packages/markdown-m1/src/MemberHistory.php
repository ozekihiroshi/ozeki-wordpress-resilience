<?php
declare(strict_types=1);
namespace Owr\M1;

/** WP-Members free/core membership. Accounts are distinct from inert content authors. */
final class MemberHistory
{
    public const PLUGIN='wp-members/wp-members.php';
    public const OPTIONS=['wpmembers_settings','wpmembers_fields','wpmembers_dialogs','wpmembers_tos'];
    private array $dirty=[];
    public static function enabled(): bool {return in_array(self::PLUGIN,(array)get_option('active_plugins'),true);}
    private function mark(string $kind,int $id=0): void {
        if(self::enabled()&&!empty((new Plugin())->config()['protect']))$this->dirty[$kind.':'.$id]=[$kind,$id];
    }
    public function boot(): void {
        foreach(['user_register','profile_update','set_user_role','wp_set_password'] as $h)
            if($h==='wp_set_password')add_action($h,fn($password,$id)=>$this->mark('user',(int)$id),PHP_INT_MAX,2);
            else add_action($h,fn($id)=>$this->mark('user',(int)$id),PHP_INT_MAX);
        foreach(['added_user_meta','updated_user_meta','deleted_user_meta'] as $h)
            add_action($h,fn($mid,$id,$key)=>in_array($key,self::metaKeys(),true)?$this->mark('user',(int)$id):null,PHP_INT_MAX,3);
        add_action('deleted_user',fn($id)=>$this->mark('user',(int)$id),PHP_INT_MAX);
        foreach(['added_option','updated_option','deleted_option'] as $h)
            add_action($h,fn($key)=>in_array($key,self::OPTIONS,true)?$this->mark('settings'):null,PHP_INT_MAX);
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $h)
            add_action($h,fn($mid,$id,$key)=>$key==='_wpmem_block'?$this->mark('restriction',(int)$id):null,PHP_INT_MAX,3);
        add_action('shutdown',[$this,'flush'],PHP_INT_MAX);
    }
    public static function metaKeys(?array $fields=null): array {
        $keys=['first_name','last_name','nickname','description','active','_wpmem_user_confirmed','_wpmem_activation_confirm'];
        foreach($fields??(array)get_option('wpmembers_fields',[]) as $field)if(is_array($field)&&isset($field[2])&&is_string($field[2]))$keys[]=$field[2];
        // Never transport sessions, reset tokens, application passwords or capabilities.
        return array_values(array_filter(array_unique($keys),fn($k)=>!preg_match('/password|pass$|session|capabilities|user_level|activation_key|application|^_owr_/i',$k)));
    }
    private static function user(int $id): ?array {
        $u=get_userdata($id);if(!$u||$u->roles!==['subscriber']||array_diff_key($u->caps,['subscriber'=>true]))return null;
        $row=[];foreach(['ID','user_login','user_pass','user_nicename','user_email','user_url','user_registered','user_status','display_name'] as $k)$row[$k]=(string)$u->data->$k;
        $meta=[];foreach(self::metaKeys() as $k){$v=get_user_meta($id,$k,false);if($v)$meta[$k]=$v;}
        return ['user'=>$row,'meta'=>$meta];
    }
    private static function settings(): array {$v=[];foreach(self::OPTIONS as $k)$v[$k]=get_option($k,false);return $v;}
    public static function baseline(): array {
        $users=[];foreach(get_users(['role'=>'subscriber','fields'=>'ID']) as $id){$u=self::user((int)$id);if($u)$users[(string)$id]=$u;}
        return ['version'=>get_file_data(WP_PLUGIN_DIR.'/'.self::PLUGIN,['Version'=>'Version'])['Version'],'settings'=>self::settings(),'users'=>$users];
    }
    public function flush(): void {
        foreach($this->dirty as $key=>[$kind,$id]){
            $value=match($kind){'user'=>self::user($id),'settings'=>self::settings(),'restriction'=>get_post_meta($id,'_wpmem_block',true)};
            $version=get_file_data(WP_PLUGIN_DIR.'/'.self::PLUGIN,['Version'=>'Version'])['Version'];
            (new CommentHistory())->enqueue('member-'.$key,Store::json(['schema'=>'owr-member-1','kind'=>$kind,'id'=>$id,'value'=>$value]),['post_type'=>'owr_member','content_format'=>'member-json','origin_id'=>$id,'title'=>'WP-Members '.$key,'status'=>$value===null?'deleted':'saved','member_version'=>$version]);
            unset($this->dirty[$key]);
        }
    }
    public static function replay(array &$data,string $source,array $attrs): void {
        $v=json_decode($source,true,512,JSON_THROW_ON_ERROR);
        if(($v['schema']??'')!=='owr-member-1'||($v['id']??null)!==($attrs['origin_id']??null))throw new \RuntimeException('Invalid membership record.');
        if(!isset($data['membership']))throw new \RuntimeException('Create a trusted WP-Members baseline before membership history.');
        $id=(string)$v['id'];$data['membership']['version']=$attrs['member_version'];
        switch($v['kind']){
            case 'user': if($v['value']===null)unset($data['membership']['users'][$id]);else $data['membership']['users'][$id]=$v['value'];break;
            case 'settings': $data['membership']['settings']=$v['value'];break;
            case 'restriction':
                if(!in_array((string)$v['value'],['','0','1','2'],true))throw new \RuntimeException('Unsupported membership restriction.');
                $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($m)=>!((string)$m['post_id']===$id&&$m['meta_key']==='_wpmem_block')));
                if($v['value']!==''){$next=max(array_merge([0],array_map('intval',array_column($data['tables']['postmeta'],'meta_id'))))+1;$data['tables']['postmeta'][]=['meta_id'=>(string)$next,'post_id'=>$id,'meta_key'=>'_wpmem_block','meta_value'=>(string)$v['value']];}break;
            default: throw new \RuntimeException('Unknown membership operation.');
        }
    }
    /** Validate every identity before destination mutation; never claim a pre-existing account. */
    public static function plan(array $state,string $from): array {
        global $wpdb;
        if(!is_file(WP_PLUGIN_DIR.'/'.self::PLUGIN))throw new \RuntimeException('Install recorded WP-Members before recovery.');
        $version=get_file_data(WP_PLUGIN_DIR.'/'.self::PLUGIN,['Version'=>'Version'])['Version']??'';
        if($version!==$state['version'])throw new \RuntimeException('Install recorded WP-Members version before recovery.');
        if(array_diff(array_keys($state['settings']),self::OPTIONS))throw new \RuntimeException('Unexpected membership setting.');
        foreach([$wpdb->users,$wpdb->usermeta,$wpdb->options] as $t){$s=$wpdb->get_row($wpdb->prepare('SHOW TABLE STATUS WHERE Name=%s',$t));if(strtolower($s->Engine??'')!=='innodb')throw new \RuntimeException('Transactional membership tables required.');}
        $plan=[];$seen=[];
        foreach($state['users'] as $id=>$entry){
            $u=$entry['user'];$marker=hash('sha256',$from.'|'.$id);
            if((int)$id<=0||(string)$u['ID']!==(string)$id||!is_email($u['user_email'])||!is_string($u['user_pass'])||strlen($u['user_pass'])<20||!$u['user_login'])throw new \RuntimeException('Invalid member identity.');
            foreach($u as $value)if(!is_string($value))throw new \RuntimeException('Invalid member field type.');
            if(array_diff(array_keys($u),['ID','user_login','user_pass','user_nicename','user_email','user_url','user_registered','user_status','display_name']))throw new \RuntimeException('Unexpected member field.');
            foreach($entry['meta'] as $k=>$values)if(!in_array($k,self::metaKeys((array)($state['settings']['wpmembers_fields']??[])),true)||!is_array($values))throw new \RuntimeException('Disallowed member metadata.');
            foreach(['user_login','user_email'] as $k){$s=$k.':'.strtolower($u[$k]);if(isset($seen[$s]))throw new \RuntimeException('Duplicate member identity.');$seen[$s]=true;}
            $found=get_users(['meta_key'=>'_owr_member_origin','meta_value'=>$marker]);if(count($found)>1)throw new \RuntimeException('Duplicate recovery mapping.');$target=$found[0]??null;
            foreach(['login'=>$u['user_login'],'email'=>$u['user_email']] as $field=>$value){$old=get_user_by($field,$value);if($old&&(!$target||$old->ID!==$target->ID))throw new \RuntimeException('Member identity conflicts with an existing destination account.');}
            if($target&&($target->roles!==['subscriber']||array_diff_key($target->caps,['subscriber'=>true])))throw new \RuntimeException('Refusing to replace privileged destination member.');
            $plan[(string)$id]=['target'=>$target?$target->ID:0,'marker'=>$marker,'entry'=>$entry];
        }
        return $plan;
    }
    /** Called inside the site's DB transaction. Direct records avoid email/reset hooks. */
    public static function install(array $state,array $plan,string $from,string $to): array {
        global $wpdb;$map=[];$source=hash('sha256',$from);
        foreach($plan as $id=>$p){
            $u=$p['entry']['user'];unset($u['ID']);$u['user_activation_key']='';
            $uid=(int)$p['target'];$ok=$uid?$wpdb->update($wpdb->users,$u,['ID'=>$uid]):$wpdb->insert($wpdb->users,$u);
            if($ok===false)throw new \RuntimeException('Cannot restore member.');if(!$uid)$uid=(int)$wpdb->insert_id;
            if($wpdb->delete($wpdb->usermeta,['user_id'=>$uid])===false)throw new \RuntimeException('Cannot replace recovered member metadata.');
            $meta=$p['entry']['meta']+['_owr_member_origin'=>[$p['marker']],'_owr_member_source'=>[$source],$wpdb->prefix.'capabilities'=>[['subscriber'=>true]],$wpdb->prefix.'user_level'=>[0]];
            foreach($meta as $k=>$values)foreach($values as $value)if($wpdb->insert($wpdb->usermeta,['user_id'=>$uid,'meta_key'=>$k,'meta_value'=>maybe_serialize($value)])===false)throw new \RuntimeException('Cannot restore member metadata.');
            $map[(string)$id]=$uid;
        }
        // Remove only accounts created by this recovery source, never unrelated users.
        foreach(get_users(['meta_key'=>'_owr_member_source','meta_value'=>$source]) as $u)if(!in_array($u->ID,$map,true)){
            if($u->roles!==['subscriber']||array_diff_key($u->caps,['subscriber'=>true]))throw new \RuntimeException('Removed member has privileged destination role.');
            if($wpdb->delete($wpdb->usermeta,['user_id'=>$u->ID])===false||$wpdb->delete($wpdb->users,['ID'=>$u->ID])===false)throw new \RuntimeException('Cannot remove recovered member.');
        }
        foreach($state['settings'] as $k=>$value)update_option($k,SiteSnapshot::relocate($value,$from,$to));
        return $map;
    }
}
