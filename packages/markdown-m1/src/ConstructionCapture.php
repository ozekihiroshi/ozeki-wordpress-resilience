<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/ConstructionOperations.php';
require_once __DIR__.'/ReceiptInputs.php';
require_once __DIR__.'/ConstructionResultReferences.php';

/** Opt-in isolated observer of actual requests; never invoked by a test driver per operation. */
final class ConstructionCapture {
    private static bool $booted=false;
    private ?int $active=null;
    private array $effects=[];
    private ?string $kind=null;
    private bool $redirect=false;
    private string $redirectUrl='';
    private ?int $restRequest=null;
    private array $importedGroups=[];
    public function boot(): void {
        if(!defined('OWR_CONSTRUCTION_ISOLATED') || OWR_CONSTRUCTION_ISOLATED!==true)throw new \RuntimeException('Isolated construction experiment only');
        if(self::$booted)return;self::$booted=true;
        add_filter('rest_request_before_callbacks',[$this,'restBefore'],PHP_INT_MAX,3);
        add_filter('rest_request_after_callbacks',[$this,'restAfter'],PHP_INT_MAX,3);
        // WP-Members executes field updates from load_admin() on init, before
        // core admin_init. Capture the request before any normal handler runs.
        add_action('init',[$this,'adminBefore'],PHP_INT_MIN);
        add_action('wp_after_insert_post',function($id,$p,$update,$before){
            if($p->post_type==='revision'||$p->post_status==='auto-draft')return;
            if($this->active===null&&!in_array($p->post_status,['publish','private','inherit'],true)&&(!$before||!in_array($before->post_status,['publish','private','inherit'],true)))return;
            $this->effect('post',['id'=>$id,'post_type'=>$p->post_type]);
        },PHP_INT_MAX,4);
        add_action('delete_attachment',fn($id)=>$this->effect('attachment-delete-attempt',['id'=>$id]),PHP_INT_MAX);
        add_action('deleted_post',function($id,$p){if($p&&$p->post_type!=='revision')$this->effect('post-delete',['id'=>$id,'post_type'=>$p->post_type]);},PHP_INT_MAX,2);
        add_action('user_register',fn($id)=>$this->effect('user',['id'=>$id]),PHP_INT_MAX);
        add_action('profile_update',fn($id)=>$this->effect('user',['id'=>$id]),PHP_INT_MAX);
        add_action('acf/import_field_group',[$this,'acfImported'],PHP_INT_MAX);
        add_action('tablepress_event_saved_table',fn($id)=>$this->effect('table-saved',['id'=>(string)$id]),PHP_INT_MAX);
        foreach(['added_option','updated_option'] as $hook)add_action($hook,function($key){if(in_array($key,['wpmembers_settings','wpmembers_fields'],true))$this->effect('option',['name'=>$key]);},PHP_INT_MAX);
        foreach(['created_term','edited_term','delete_term'] as $hook)add_action($hook,function($id,$tt,$taxonomy){
            if(in_array($taxonomy,['category','post_tag','nav_menu'],true))$this->effect('taxonomy',['id'=>(int)$id,'taxonomy'=>$taxonomy]);
        },PHP_INT_MAX,3);
        add_action('set_object_terms',function($id,$terms,$tt,$taxonomy){
            if($this->active===null&&in_array(get_post_status($id),['publish','private','inherit'],true)&&in_array($taxonomy,['category','post_tag','nav_menu'],true))$this->effect('term-relationship',['id'=>(int)$id,'taxonomy'=>$taxonomy]);
        },PHP_INT_MAX,4);
        foreach(['added_user_meta','updated_user_meta','deleted_user_meta'] as $hook)add_action($hook,function($unused,$id,$key){
            if($this->active!==null||in_array($key,['session_tokens','community-events-location','dismissed_wp_pointers'],true)||str_starts_with($key,'_ozeki_resilience'))return;
            $keys=['first_name','last_name','nickname','description','active','wpmem_block'];
            foreach((array)get_option('wpmembers_fields',[]) as $f)if(is_array($f)&&isset($f[2]))$keys[]=$f[2];
            if(in_array($key,$keys,true))$this->effect('member-meta',['id'=>(int)$id,'key'=>$key]);
        },PHP_INT_MAX,3);
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $hook)add_action($hook,function($unused,$id,$key){
            if(str_starts_with($key,'_ozeki_resilience')||in_array($key,['_edit_lock','_edit_last'],true))return;
            if(!in_array(get_post_type($id),['post','page','attachment','ozmd_document','wpcf7_contact_form','flamingo_inbound','acf-field','acf-field-group'],true))return;
            if(!in_array(get_post_status($id),['publish','private','inherit'],true))return;
            if($this->active===null)$this->effect('unrecorded-meta',['id'=>(int)$id,'key'=>(string)$key]);
        },PHP_INT_MAX,3);
        add_filter('wp_redirect',function($url){if($this->active!==null){$this->redirect=true;$this->redirectUrl=$url;}return $url;},PHP_INT_MAX);
        add_action('shutdown',[$this,'shutdown'],PHP_INT_MAX);
        add_filter('wpcf7_flamingo_inbound_message_parameters',[$this,'receiptBefore'],PHP_INT_MAX);
        add_action('wpcf7_after_flamingo',[$this,'receiptAfter'],PHP_INT_MAX);
    }
    private static function withoutCredentials(array $p): array {
        // post_password is a content access condition, not an account credential.
        foreach(array_keys($p) as $key)if(preg_match('/nonce|^password$|^pass[12]$|^pwd$|^user_pass$|^_wp_http_referer$/i',(string)$key))unset($p[$key]);
        return $p;
    }
    private function effect(string $type,array $data): void {
        if($this->active!==null){$this->effects[]=['type'=>$type]+$data;return;}
        // A prepared recovery destination is not yet a protected source. Its
        // normal preparation is covered by a NEW baseline before source use.
        $config=(array)get_option('ozeki_resilience_m1_config',[]);
        $protected=get_option('ozeki_resilience_construction_preservation_v1',null)!==null||get_option('ozeki_resilience_construction_preservation_v1_capture',null)!==null;
        if(ConstructionJournal::enabled()&&$protected&&($config['setup_role']??'source')==='source')ConstructionJournal::gap('unrecorded_change',['type'=>$type]+$data);
    }
    public function acfImported(array $group): void {
        if($this->active===null||$this->kind!=='admin'||empty($group['ID'])||empty($group['key']))return;
        $this->importedGroups[$group['key']]=(int)$group['ID'];
        $this->effect('acf-import',['id'=>(int)$group['ID'],'key'=>$group['key']]);
    }
    private function importCompleted(): bool {
        if(!$this->importedGroups||$this->active===null)return false;
        $entry=ConstructionOperations::read()['entries'][$this->active-1];$i=$entry['input'];
        if(($i['query']['page']??'')!=='acf-tools'||($i['body']['import_type']??'')!=='json')return false;
        $raw=base64_decode($i['files']['acf_import_file']['base64']??'',true);
        $groups=$raw===false?null:json_decode($raw,true);if(!is_array($groups)||!$groups)return false;
        $keys=[];foreach($groups as $group){if(!is_array($group)||empty($group['key'])||isset($keys[$group['key']]))return false;$keys[$group['key']]=true;}
        $expected=array_keys($keys);$actual=array_keys($this->importedGroups);sort($expected);sort($actual);return $expected===$actual;
    }
    public function restBefore($response,$handler,$request) {
        if($this->active!==null || $response!==null || !current_user_can('manage_options') || !in_array($request->get_method(),['POST','PUT','PATCH','DELETE'],true))return $response;
        $route=$request->get_route();
        if(!preg_match('~^/(wp/v2/(posts|pages|media|categories)(/\d+)?|wp/v2/media/\d+/edit|contact-form-7/v1/contact-forms(/\d+)?)$~D',$route))return $response;
        $this->kind='rest';$this->restRequest=spl_object_id($request);$this->effects=[];$p=$request->get_json_params()??$request->get_body_params();
        $body=self::withoutCredentials($p);
        // REST posts/pages use "password" for content access, not account login.
        if(preg_match('~^/wp/v2/(posts|pages)(/\d+)?$~D',$route)&&array_key_exists('password',$p))$body['password']=$p['password'];
        $input=['actor'=>get_current_user_id(),'route'=>$route,'method'=>$request->get_method(),'body'=>$body];
        if($request->get_method()==='DELETE')$input['query']=self::withoutCredentials($request->get_query_params());
        if($route==='/wp/v2/media'){
            $raw=$request->get_body();$disposition=$request->get_header('content-disposition');
            if(strlen($raw)>5*1024*1024)throw new \RuntimeException('Isolated media capture limit');
            $input['upload']=['base64'=>base64_encode($raw),'content_type'=>$request->get_header('content-type'),'content_disposition'=>$disposition];
        }
        $this->active=ConstructionOperations::begin('rest',$input);return $response;
    }
    public function restAfter($response,$handler,$request) {
        if($this->kind!=='rest'||$this->active===null||$this->restRequest!==spl_object_id($request))return $response;
        $ok=!is_wp_error($response);$r=$ok?rest_ensure_response($response):null;
        $ok=$ok&&$r->get_status()<400;
        // A failed response after a write is not proof that nothing happened.
        // Keep the attempt unresolved rather than discarding a partial operation.
        if(!$ok&&$this->effects){$this->active=null;$this->kind=null;return $response;}
        $data=$ok?$r->get_data():null;
        ConstructionOperations::finish($this->active,['response'=>$data,'effects'=>$this->effects,'reference_values'=>$ok&&is_array($data)?ConstructionResultReferences::read($request->get_route(),$data):[]],$ok);
        $this->active=null;$this->kind=null;return $response;
    }
    public function adminBefore(): void {
        if(($_SERVER['REQUEST_METHOD']??'')!=='POST'||!current_user_can('manage_options'))return;
        $p=wp_unslash($_POST);$action=(string)($p['action']??'');$path=basename($_SERVER['SCRIPT_NAME']??'');$page=(string)($_GET['page']??'');
        $known=($path==='post.php'&&$action==='editpost') || ($path==='admin-post.php'&&$action==='ozmd_import_document')
            || ($page==='wpmem-settings'&&isset($p['wpmem_admin_a']))
            || ($path==='user-new.php'&&$action==='createuser') || ($path==='user-edit.php'&&$action==='update')
            || ($path==='admin-post.php'&&$action==='tablepress_import') || ($path==='admin-ajax.php'&&$action==='tablepress_save_table')
            || ($page==='acf-tools'&&isset($p['import_type']));
        if(!$known)return;
        $files=[];foreach($_FILES as $key=>$f){if(!is_array($f['tmp_name']??null)&&($f['error']??1)===UPLOAD_ERR_OK&&is_uploaded_file($f['tmp_name'])){
            if(filesize($f['tmp_name'])>5*1024*1024)throw new \RuntimeException('Construction upload exceeds development limit');
            $files[$key]=['name'=>$f['name'],'base64'=>base64_encode(file_get_contents($f['tmp_name']))];
        }}
        $fields=[];if(isset($p['acf'])&&is_array($p['acf'])&&function_exists('acf_get_field'))foreach($p['acf'] as $key=>$unused){$field=acf_get_field($key);if($field)$fields[$key]=['key'=>$field['key'],'type'=>$field['type']];}
        $nonceFields=array_values(array_filter(array_keys($p),fn($key)=>stripos((string)$key,'nonce')!==false));
        $memberFields=[];if(in_array($path,['user-new.php','user-edit.php'],true))foreach((array)get_option('wpmembers_fields',[]) as $f)if(is_array($f)&&isset($f[2],$f[3])&&array_key_exists($f[2],$p))$memberFields[$f[2]]=['type'=>$f[3]];
        $this->kind='admin';$this->active=ConstructionOperations::begin('admin',['actor'=>get_current_user_id(),'path'=>$path,'query'=>self::withoutCredentials(wp_unslash($_GET)),'body'=>self::withoutCredentials($p),'files'=>$files,'field_contracts'=>$fields,'member_fields'=>$memberFields,'nonce_fields'=>$nonceFields]);
    }
    public function shutdown(): void {
        if($this->active===null || $this->kind!=='admin')return;
        $last=error_get_last();if($last&&in_array($last['type'],[E_ERROR,E_PARSE,E_CORE_ERROR,E_COMPILE_ERROR],true))return;
        // No success inferred from a 200 response. Unobserved/no-op saves stay pending.
        $optionSaved=(bool)array_filter($this->effects,fn($e)=>$e['type']==='option');
        if($this->effects&&($this->redirect||wp_doing_ajax()||$optionSaved||$this->importCompleted())){
            ConstructionOperations::finish($this->active,['effects'=>$this->effects,'redirect'=>$this->redirectUrl]);$this->active=null;
        }
    }
    public function receiptBefore(array $input): array {
        if($this->active!==null)throw new \RuntimeException('Nested construction receipt');
        $form=\WPCF7_ContactForm::get_current();if(!$form)throw new \RuntimeException('Missing form identity');
        $dependencies=[];foreach(['contact-form-7/wp-contact-form-7.php','flamingo/flamingo.php'] as $file)$dependencies[$file]=get_file_data(WP_PLUGIN_DIR.'/'.$file,['Version'=>'Version'])['Version'];
        $this->kind='receipt';$this->active=ConstructionOperations::begin('flamingo-add',['form_id'=>$form->id(),'arguments'=>$input,'dependencies'=>$dependencies]);return $input;
    }
    public function receiptAfter(array $result): void {
        if($this->kind!=='receipt'||$this->active===null)return;
        $id=(int)($result['flamingo_inbound_id']??0);if(!$id)return;
        ConstructionOperations::finish($this->active,['id'=>$id,'receipt'=>ReceiptInputs::result($id)]);$this->active=null;
    }
}
