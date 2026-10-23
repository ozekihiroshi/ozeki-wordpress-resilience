<?php
declare(strict_types=1);
namespace Owr;

/** Opt-in three-page projection. Dedicated mysqli never reconnects/replays SQL. */
final class RbrWordPressSave
{
    private string $table;
    public function __construct(private \mysqli $db, private string $posts, private array $ids,
        private array $seed, private RbrObjectStore $store, private string $work,
        private array $images, private ?\Closure $fault = null)
    {
        if (!preg_match('/^[A-Za-z0-9_]+$/D',$posts) || array_keys($ids)!==['company','services','contact']
            || count(array_unique($ids))!==3 || array_filter($ids,fn($v)=>!is_int($v)||$v<1)
            || !is_dir($work) || is_link($work) || wp_using_ext_object_cache()) {
            throw new \RuntimeException('Unsupported dedicated projection configuration');
        }
        $this->table=$posts.'_owr_projection';
        $this->db->set_charset('utf8mb4');
        foreach([$this->posts,$this->table] as $table) {
            $s=$this->sql('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=?',[$table])->get_result()->fetch_assoc();
            if (($s['ENGINE']??null)!=='InnoDB') throw new \RuntimeException('Provision InnoDB projection tables first');
        }
    }
    private function sql(string $query,array $args=[]): \mysqli_stmt {
        $s=$this->db->prepare($query);if($args){$s->bind_param(str_repeat('s',count($args)),...$args);}$s->execute();return $s;
    }
    private function tx(\Closure $fn): mixed {
        $this->db->begin_transaction();
        try {$r=$fn();$this->db->commit();return $r;}
        catch(\Throwable $e){try{$this->db->rollback();}catch(\Throwable){}throw $e;}
    }
    private function state(): array {
        $r=$this->sql("SELECT state FROM {$this->table} WHERE id=1 FOR UPDATE")->get_result()->fetch_assoc();
        if(!$r)throw new \RuntimeException('Projection not enrolled');return json_decode($r['state'],true,64,JSON_THROW_ON_ERROR);
    }
    private function write(array $state): void {$this->sql("UPDATE {$this->table} SET state=? WHERE id=1",[RbrGenerationCoordinator::encode($state)]);}
    private function pages(): array {
        $out=[];
        foreach($this->ids as $role=>$id){
            $row=$this->sql("SELECT ID,post_title,post_name,post_content,post_status,post_type,post_parent,post_modified,post_modified_gmt FROM {$this->posts} WHERE ID=? FOR UPDATE",[$id])->get_result()->fetch_assoc();
            if(!$row || $row['post_type']!=='page' || $row['post_status']!=='publish' || (int)$row['post_parent']!==0)throw new \RuntimeException('Only enrolled published root pages');
            $out[$role]=$row;
        }return $out;
    }
    private function snapshot(): string {return hash('sha256',RbrGenerationCoordinator::encode($this->pages()));}
    public function enroll(): void {
        $this->tx(function(){
            $s=$this->state();if(($s['enrolled']??false))throw new \RuntimeException('Already enrolled');
            $initial=[];foreach($this->pages() as $role=>$row){
                $html=$row['post_content'];preg_match_all('~<p>([^<]*)</p>~s',$html,$m);
                if(!$m[0] || implode('', $m[0])!==$html)throw new \RuntimeException('Initial editor content must be plain paragraphs');
                $initial[$role]=['title'=>$row['post_title'],'slug'=>$row['post_name'],'paragraphs'=>array_map(fn($v)=>html_entity_decode($v,ENT_QUOTES|ENT_HTML5,'UTF-8'),$m[1])];
            }
            $this->write(['expected_context'=>$this->expectedContext(),'editor_pages'=>$initial,'enrolled'=>true,'sequence'=>0,'generation'=>null,'manifest'=>null,'pending'=>null,'operations'=>[],
                'fingerprint'=>$this->snapshot(),'configuration'=>$this->configuration()]);
        });
    }
    /** Local journal only. No S3 calls, path/credentials exposure or state mutation. */
    public function editorState(): array {
        return $this->tx(function(){
            $s=$this->state();
            if(($s['configuration']??'')!==$this->configuration() || !isset($s['editor_pages']))throw new \RuntimeException('Editor enrollment unavailable');
            $pending=null;
            if($s['pending']!==null){
                $e=$s['operations'][$s['pending']];
                if(!isset($e['input']))throw new \RuntimeException('Legacy pending input unavailable');
                $pending=['input'=>$e['input'],'phase'=>$e['state']];
            }
            $applied=null;foreach($s['operations'] as $id=>$e){if($e['state']==='applied' && $e['job']['sequence']===$s['sequence'])$applied=$id;}
            return ['applied_operation'=>$applied,'sequence'=>$s['sequence'],'pages'=>$s['editor_pages'],'pending'=>$pending,'drift'=>$s['fingerprint']!==$this->snapshot()];
        });
    }
    private function configuration(): string {return hash('sha256',RbrGenerationCoordinator::encode(['ids'=>$this->ids,'seed'=>$this->seed,'images'=>$this->images]));}
    private function validate(array $input): void {
        $keys=array_keys($input);sort($keys);if($keys!==['expected_sequence','operation_id','pages']
            || !is_string($input['operation_id']) || !preg_match('/^[a-zA-Z0-9_-]{8,64}$/D',$input['operation_id'])
            || !is_int($input['expected_sequence']) || $input['expected_sequence']<0 || !is_array($input['pages']))throw new \InvalidArgumentException('Invalid save request');
        $roles=array_keys($input['pages']);sort($roles);if($roles!==['company','contact','services'])throw new \InvalidArgumentException('All three pages required');
        $slugs=[];
        foreach($input['pages'] as $page){
            if(!is_array($page))throw new \InvalidArgumentException('Page object required');
            $keys=array_keys($page);sort($keys);
            if($keys!==['paragraphs','slug','title']||!is_string($page['title'])||trim($page['title'])===''||strlen($page['title'])>200||preg_match('/[<>\x00-\x1F\x7F]/',$page['title'])
                ||!is_string($page['slug'])||!preg_match('/^[a-z0-9-]{1,100}$/D',$page['slug'])||isset($slugs[$page['slug']])
                ||!is_array($page['paragraphs'])||!array_is_list($page['paragraphs'])||count($page['paragraphs'])<1||count($page['paragraphs'])>100)throw new \InvalidArgumentException('Unsupported page');
            foreach($page['paragraphs'] as $p){if(!is_string($p)||strlen($p)>10000)throw new \InvalidArgumentException('Bounded plain text only');}
            $slugs[$page['slug']]=true;
        }
        if(strlen(RbrGenerationCoordinator::encode($input))>262144)throw new \InvalidArgumentException('Request too large');
    }
    /** Enrollment metadata only: no reconstructed DB or served HTML is observed. */
    private function expectedContext(): array {
        $c=['roles'=>[],'images'=>[],'relations'=>[]];
        foreach($this->seed as $a){
            if($a['id']==='request-expectation')throw new \RuntimeException('Reserved expectation asset identity');
            if($a['kind']==='page'){$c['roles'][$a['role']]=$a['id'];continue;}
            if(!in_array($a['kind'],['image','relations'],true))continue;
            if(isset($a['storage']))$raw=$this->store->bytes($a['storage']);
            elseif(isset($a['existing']))$raw=$this->store->bytes($a['existing']);
            else {if(is_link($a['path']))throw new \RuntimeException('Invalid enrollment original');$raw=file_get_contents($a['path']);}
            if(!is_string($raw)||strlen($raw)!==$a['size_bytes']||hash('sha256',$raw)!==$a['sha256'])throw new \RuntimeException('Enrollment original differs');
            if($a['kind']==='image'){
                $im=getimagesizefromstring($raw);if(!$im||!in_array($im[2],[IMAGETYPE_PNG,IMAGETYPE_JPEG],true))throw new \RuntimeException('Unsupported expected image');
                $c['images'][$a['id']]=['sha256'=>$a['sha256'],'width'=>$im[0],'height'=>$im[1],'alt'=>''];
            }else $c['relations']=json_decode($raw,true,64,JSON_THROW_ON_ERROR)['edges'];
        }
        ksort($c['images']);return $c;
    }
    /** Pure request-to-Q projection. Context is frozen at explicit enrollment. */
    public static function expectedFromRequest(array $input,array $context): array {
        $q=['schema'=>'owr-rbr-expected-v1','actual_status'=>'draft','scope'=>['roles'=>['company','services','contact'],'images'=>array_keys($context['images']),'business_expectations'=>[]],
            'pages'=>[],'images'=>$context['images'],'relations'=>$context['relations']];
        foreach(['company','services','contact'] as $role){
            $p=$input['pages'][$role];$q['pages'][$context['roles'][$role]]=array_merge($p,['role'=>$role]);
            $texts=array_values(array_filter($p['paragraphs'],fn($v)=>trim($v)!==''));
            if(!$texts)throw new \InvalidArgumentException('Expected business text required');
            $q['scope']['business_expectations'][$role]=$texts;
        }
        foreach($q['relations'] as $e){
            if(!isset($q['pages'][$e['from']])||($e['type']!=='navigation'&&$e['position']>count($q['pages'][$e['from']]['paragraphs'])))throw new \InvalidArgumentException('Expected relation outside edited page');
        }
        return $q;
    }
    private function job(array $input,array $state): array {
        $now=$this->store->now();$assets=[];$prior=$state['manifest']['assets']??$this->seed;
        foreach($prior as $asset){
            if($asset['kind']==='page'){
                $role=$asset['role'];$raw=RbrGenerationCoordinator::encode($input['pages'][$role]);
                $asset=['id'=>$asset['id'],'revision'=>'save-'.$input['operation_id'],'kind'=>'page','role'=>$role,'provenance'=>'s3-first',
                    'size_bytes'=>strlen($raw),'sha256'=>hash('sha256',$raw),'path'=>$this->work.'/'.$input['operation_id'].'-'.$role.'.json'];
            }elseif(isset($asset['storage'])){$asset['existing']=$asset['storage'];unset($asset['storage']);}
            $assets[]=$asset;
        }
        return ['schema'=>'owr-rbr-save-v1','site_id'=>$this->store->siteId(),'operation_id'=>$input['operation_id'],
            'sequence'=>$state['sequence']+1,'parent'=>$state['generation'],'prepared_at'=>$now,'deadline'=>$now+3600,'assets'=>$assets];
    }
    public function save(array $input): array {
        $this->validate($input);$digest=hash('sha256',RbrGenerationCoordinator::encode($input));$op=$input['operation_id'];
        $entry=$this->tx(function()use($input,$digest,$op){
            $s=$this->state();if(($s['configuration']??'')!==$this->configuration())throw new \RuntimeException('Enrolled configuration changed');
            if(isset($s['operations'][$op])){
                $e=$s['operations'][$op];if($e['digest']!==$digest)throw new \RuntimeException('Operation input conflict');
                if($e['state']==='applied')return $e;
                if($s['pending']!==$op)throw new \RuntimeException('Pending operation mismatch');
            }else{
                if($s['pending']!==null)throw new \RuntimeException('Pending save must be reconciled');
                if($s['sequence']!==$input['expected_sequence'])throw new \RuntimeException('Stale generation');
                if(count($s['operations'])>=100)throw new \RuntimeException('Prototype operation limit');
                if(!isset($s['expected_context']))throw new \RuntimeException('Expected-state enrollment required');
                $q=self::expectedFromRequest($input,$s['expected_context']);$job=$this->job($input,$s);
                $job['expected_sha256']=hash('sha256',RbrGenerationCoordinator::encode($q));
                $e=['input'=>$input,'digest'=>$digest,'expected'=>$q,'state'=>'prepared','job'=>$job];
                $s['operations'][$op]=$e;$s['pending']=$op;
            }
            if($s['fingerprint']!==$this->snapshot())throw new \RuntimeException('Protected page drift');
            $this->write($s);return $e;
        });
        if($entry['state']==='applied')return ['state'=>'applied','replayed'=>true,'generation'=>$entry['generation'],'sequence'=>$entry['job']['sequence']]+(isset($entry['expected_ref'])?['expected_ref'=>$entry['expected_ref']]:[]);
        // This journal's per-operation source files are immutable; no DB transaction spans S3.
        foreach($entry['job']['assets'] as $a){if($a['kind']!=='page')continue;
            $raw=RbrGenerationCoordinator::encode($input['pages'][$a['role']]);
            $f=@fopen($a['path'],'x');if($f){chmod($a['path'],0600);fwrite($f,$raw);fflush($f);fclose($f);}
            if(is_link($a['path'])||file_get_contents($a['path'])!==$raw)throw new \RuntimeException('Local original differs');
        }
        if(!isset($entry['expected'])||hash('sha256',RbrGenerationCoordinator::encode($entry['expected']))!==($entry['job']['expected_sha256']??''))throw new \RuntimeException('Frozen expected state unavailable');
        $result=(new RbrGenerationCoordinator($this->store))->save($entry['job']);
        $intent=$entry['job'];foreach($intent['assets'] as &$a){unset($a['path']);}unset($a);
        $bound=['schema'=>'owr-rbr-bound-expected-v1','generation'=>$result['generation'],'intent'=>$intent,'expected'=>$entry['expected']];
        $expectedRef=$this->store->ensureBytes($this->store->key('originals/request-expectation/'.$op.'/source'),RbrGenerationCoordinator::encode($bound));
        if($expectedRef['retain_until']<$result['manifest']['protect_until'])throw new \RuntimeException('Expected-state retention insufficient');

        $this->tx(function()use($op,$digest,$result,$expectedRef){
            $s=$this->state();$e=$s['operations'][$op]??null;
            if(!$e || $e['digest']!==$digest)throw new \RuntimeException('Operation input conflict');
            if($e['state']==='applied')return;
            if($s['pending']!==$op)throw new \RuntimeException('Pending operation mismatch');
            $s['operations'][$op]['expected_ref']=$expectedRef;$s['operations'][$op]['state']='stored';$s['operations'][$op]['generation']=$result['generation'];$this->write($s);
        });
        $this->fault?->__invoke('after_s3');
        // Read exact originals from the confirmed manifest; never project unconfirmed request bytes.
        $rendered=$this->render($result['manifest']);
        $this->tx(function()use($op,$digest,$result,$rendered){
            $s=$this->state();$e=$s['operations'][$op]??null;
            if($e && $e['state']==='applied')return; // another same-operation request completed it
            if(!$e||$e['digest']!==$digest||$s['pending']!==$op||$s['sequence']+1!==$result['manifest']['sequence'])throw new \RuntimeException('Superseded operation');
            if($s['fingerprint']!==$this->snapshot())throw new \RuntimeException('Protected page drift');
            foreach($rendered as $role=>$page){
                $id=$this->ids[$role];$other=$this->sql("SELECT ID FROM {$this->posts} WHERE post_name=? AND ID NOT IN (".implode(',',$this->ids).") AND post_status NOT IN ('trash','auto-draft') LIMIT 1",[$page['slug']])->get_result()->fetch_assoc();
                if($other)throw new \RuntimeException('Slug collision');
                $this->sql("UPDATE {$this->posts} SET post_title=?,post_name=?,post_content=?,post_modified=?,post_modified_gmt=? WHERE ID=?",[$page['title'],$page['slug'],$page['html'],current_time('mysql'),current_time('mysql',true),$id]);
                $this->fault?->__invoke('after_page_'.$role);
            }
            $s['editor_pages']=$e['input']['pages'];$s['sequence']=$result['manifest']['sequence'];$s['generation']=$result['generation'];$s['manifest']=$result['manifest'];$s['pending']=null;
            $s['operations'][$op]['state']='applied';$s['operations'][$op]['generation']=$result['generation'];$s['fingerprint']=$this->snapshot();$this->write($s);
        });
        foreach($this->ids as $id){wp_cache_delete($id,'posts');wp_cache_delete($id,'post_meta');}
        wp_cache_set_posts_last_changed();
        return ['state'=>'applied','replayed'=>false,'generation'=>$result['generation'],'sequence'=>$result['manifest']['sequence'],'expected_ref'=>$expectedRef];
    }
    private function render(array $manifest): array {
        $pages=[];$byId=[];$edges=[];
        foreach($manifest['assets'] as $a){
            $raw=$this->store->bytes($a['storage']);
            if($a['kind']==='page'){$pages[$a['role']]=json_decode($raw,true,64,JSON_THROW_ON_ERROR);$byId[$a['id']]=['kind'=>'page','id'=>$this->ids[$a['role']],'title'=>$pages[$a['role']]['title']];}
            if($a['kind']==='image'){
                $i=$this->images[$a['id']]??null;
                if(!$i||is_link($i['path'])||hash_file('sha256',$i['path'])!==hash('sha256',$raw))throw new \RuntimeException('Enrolled media differs from S3');
                $byId[$a['id']]=['kind'=>'image','url'=>$i['url']];
            }
            if($a['kind']==='relations')$edges=json_decode($raw,true,64,JSON_THROW_ON_ERROR)['edges'];
        }
        foreach($manifest['assets'] as $a){if($a['kind']!=='page')continue;$p=&$pages[$a['role']];$html='';$nav='';
            for($n=0;$n<=count($p['paragraphs']);$n++){
                foreach($edges as $edge){if($edge['from']!==$a['id']||$edge['position']!==$n)continue;
                    $to=$byId[$edge['to']];$fragment=$edge['type']==='image'?'<img src="'.esc_url($to['url']).'" alt="">':'<a href="'.esc_url(home_url('/?page_id='.$to['id'])).'">'.esc_html($to['title']).'</a>';
                    if($edge['type']==='navigation')$nav.=$fragment;else $html.=$fragment;
                }
                if($n<count($p['paragraphs']))$html.='<p>'.esc_html($p['paragraphs'][$n]).'</p>';
            }
            foreach($edges as $edge)if($edge['from']===$a['id'] && $edge['position']>count($p['paragraphs']))throw new \RuntimeException('Relation outside page');
            $p['html']=$html.($nav!==''?'<nav class="related">'.$nav.'</nav>':'');unset($p);
        }return $pages;
    }
}
