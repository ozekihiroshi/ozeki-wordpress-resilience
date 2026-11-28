<?php
/** Runs only in the disposable, network-isolated WordPress fixture. */
use OzekiResilience\M1\{Store,SiteSnapshot,UpdateContract,NativeReconstruction};
spl_autoload_register(static function($name){$prefix='OzekiResilience\\M1\\';if(str_starts_with($name,$prefix)){ $p='/tmp/product/src/'.substr($name,strlen($prefix)).'.php';if(is_file($p))require_once $p;}});
require_once '/tmp/product/tests/retention-memory.php';
class NativeMemoryObjects {
    use RetentionMemory;
    public array $objects=[];public int $n=0;
    function putObject($a){if(isset($this->objects[$a['Key']]))throw new RuntimeException('duplicate object');return $this->objects[$a['Key']]=['Body'=>(string)$a['Body'],'VersionId'=>'v'.++$this->n];}
    function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return $r;}
    function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&(!isset($a['StartAfter'])||strcmp($k,$a['StartAfter'])>0))$out[]=['Key'=>$k];usort($out,fn($x,$y)=>strcmp($x['Key'],$y['Key']));return ['Contents'=>$out];}
}
function ok($x){if(is_wp_error($x))throw new RuntimeException($x->get_error_message());return $x;}
function must_native($x,$m){if(!$x)throw new RuntimeException($m);}
wp_set_current_user(1);
$mode=$args[0]??'source';$size=(int)($args[1]??10);
$object=new NativeMemoryObjects();$store=new Store($object,['bucket'=>'local-only','prefix'=>'fixture/','retention_days'=>0]);$site=new SiteSnapshot($store);
if($mode==='source'){
    require_once ABSPATH.'wp-admin/includes/file.php';require_once ABSPATH.'wp-admin/includes/media.php';require_once ABSPATH.'wp-admin/includes/image.php';
    $ids=[];$cat=ok(wp_insert_term('Technical','category',['slug'=>'technical']))['term_id'];$sub=ok(wp_insert_term('Monitoring','category',['slug'=>'monitoring','parent'=>$cat]))['term_id'];$tag=ok(wp_insert_term('PLC','post_tag'))['term_id'];
    $png=imagecreatetruecolor(1200,800);$color=imagecolorallocate($png,30,80,170);imagefill($png,0,0,$color);imagepng($png,'/tmp/source-image.png');imagedestroy($png);
    $image=ok(media_handle_sideload(['name'=>'diagram.png','tmp_name'=>'/tmp/source-image.png'],0,'Diagram'));update_post_meta($image,'_wp_attachment_image_alt','Diagram 日本語');
    foreach(['home'=>'page','parent'=>'page','child'=>'page','news'=>'page','article'=>'post','unpublish'=>'post','delete'=>'post','first_draft'=>'post','restricted'=>'page','password'=>'page'] as $key=>$type){
        $ids[$key]=ok(wp_insert_post(wp_slash(['post_type'=>$type,'post_title'=>'Fixture '.$key,'post_name'=>$key,'post_status'=>$key==='first_draft'?'draft':'publish','post_content'=>'<!-- wp:paragraph --><p>CONTENT-'.$key.'</p><!-- /wp:paragraph -->','post_password'=>$key==='password'?'private-fixture':'','post_author'=>1]),true));
    }
    update_post_meta($ids['restricted'],'_wpmem_block','1');
    ok(wp_update_post(['ID'=>$ids['child'],'post_parent'=>$ids['parent']],true));
    $body='<!-- wp:paragraph --><p>NATIVE-ARTICLE <a href="'.get_permalink($ids['child']).'">Child</a> <a href="https://source.invalid.evil/child/">External</a></p><!-- /wp:paragraph -->';
    $body.='<!-- wp:image {"id":'.$image.',"sizeSlug":"full","linkDestination":"none"} --><figure class="wp-block-image size-full"><img src="'.wp_get_attachment_url($image).'" alt="Diagram 日本語" class="wp-image-'.$image.'"/></figure><!-- /wp:image -->';
    ok(wp_update_post(wp_slash(['ID'=>$ids['article'],'post_content'=>$body]),true));
    ok(wp_set_post_terms($ids['article'],[$sub],'category'));ok(wp_set_post_terms($ids['article'],[$tag],'post_tag'));set_post_thumbnail($ids['article'],$image);
    $menu=ok(wp_create_nav_menu('Fixture menu'));$parentItem=ok(wp_update_nav_menu_item($menu,0,['menu-item-title'=>'Parent menu','menu-item-object-id'=>$ids['parent'],'menu-item-object'=>'page','menu-item-type'=>'post_type','menu-item-status'=>'publish']));
    $childItem=ok(wp_update_nav_menu_item($menu,0,['menu-item-title'=>'Child menu','menu-item-object-id'=>$ids['child'],'menu-item-object'=>'page','menu-item-type'=>'post_type','menu-item-parent-id'=>$parentItem,'menu-item-status'=>'publish']));
    $nav=['blockName'=>'core/navigation-link','attrs'=>['label'=>'Native child navigation','type'=>'page','id'=>$ids['child'],'url'=>get_permalink($ids['child']),'kind'=>'post-type'],'innerBlocks'=>[],'innerHTML'=>'','innerContent'=>[]];
    $ids['navigation']=ok(wp_insert_post(wp_slash(['post_type'=>'wp_navigation','post_status'=>'publish','post_title'=>'Native navigation','post_content'=>serialize_blocks([$nav]),'post_author'=>1]),true));
    ok(wp_update_post(wp_slash(['ID'=>$ids['home'],'post_content'=>get_post($ids['home'])->post_content.'<!-- wp:navigation {"ref":'.$ids['navigation'].',"overlayMenu":"never"} /-->']),true));
    for($i=0;$i<$size;$i++)ok(wp_insert_post(['post_type'=>'post','post_title'=>'Scale '.$i,'post_status'=>'publish','post_content'=>'<!-- wp:paragraph --><p>Scale content '.$i.'</p><!-- /wp:paragraph -->','post_author'=>1],true));
    update_option('show_on_front','page');update_option('page_on_front',$ids['home']);update_option('page_for_posts',$ids['news']);
    // Capture the production data shape, not a parallel fixture-only schema.
    $data=(new ReflectionMethod($site,'data'))->invoke($site);$files=[];
    $upload=wp_upload_dir();foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($upload['basedir'],FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$files['uploads/'.substr($f->getPathname(),strlen($upload['basedir'])+1)]=file_get_contents($f->getPathname());
    $files['content.json']=Store::json($data);$manifest=['schema'=>'owr-site-snapshot-1','source_url'=>home_url(),'source_upload_url'=>$upload['baseurl'],'through'=>0,'wordpress'=>$GLOBALS['wp_version'],'plugins'=>[]];
    $initial=$site->save($files,$manifest);$sequence=0;
    $record=function($id,$status,$raw)use(&$sequence,$store){$p=get_post($id,ARRAY_A);$a=['post_type'=>$p['post_type'],'content_format'=>'wordpress-block-html','origin_id'=>$id,'origin_url'=>get_permalink($id),'title'=>$p['post_title'],'slug'=>$p['post_name'],'status'=>$status,'date'=>$p['post_date'],'date_gmt'=>$p['post_date_gmt']]+UpdateContract::capture($p);$original=$store->prepare('article-'.$id,'event-'.++$sequence,$raw,$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>$sequence,'original'=>$original,'attributes'=>$a]);};
    $record($ids['article'],'publish',$body.'<!-- wp:paragraph --><p>FORMAL-APPEND</p><!-- /wp:paragraph -->');
    $ids['added']=ok(wp_insert_post(['post_type'=>'page','post_title'=>'Formal added','post_name'=>'formal-added','post_status'=>'publish','post_author'=>1,'post_content'=>'FORMAL-ADDED'],true));$record($ids['added'],'publish','<!-- wp:paragraph --><p>FORMAL-ADDED</p><!-- /wp:paragraph -->');
    $record($ids['unpublish'],'draft','FORMALLY-UNPUBLISHED');
    $a=['post_type'=>'owr_native','content_format'=>'native-state-json','origin_id'=>$ids['delete']];$raw=Store::json(['schema'=>'owr-native-state-2','id'=>$ids['delete'],'type'=>'post','deleted'=>true,'thumbnail'=>0,'terms'=>[],'assigned'=>[],'parent'=>0]);$original=$store->prepare('deleted','event-'.++$sequence,$raw,$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>$sequence,'original'=>$original,'attributes'=>$a]);
    $fixture=['objects'=>$object->objects,'ref'=>$initial['manifest'],'ids'=>$ids,'image'=>$image,'category'=>$cat,'subcategory'=>$sub,'tag'=>$tag,'menu'=>$menu,'menu_parent'=>$parentItem,'menu_child'=>$childItem,'through'=>$sequence,'image_hash'=>hash_file('sha256',get_attached_file($image))];
    $diffs=[];foreach(parse_blocks($body) as $b)if(wp_kses_post($b['innerHTML'])!==$b['innerHTML'])$diffs[]=['before'=>$b['innerHTML'],'after'=>wp_kses_post($b['innerHTML'])];
    file_put_contents('/tmp/materials.bin',serialize($fixture));echo wp_json_encode(['source_count'=>count($data['tables']['posts']),'through'=>$sequence,'html_diffs'=>$diffs]);return;
}
$fixture=unserialize(file_get_contents('/tmp/materials.bin'),['allowed_classes'=>false]);$object->objects=$fixture['objects'];$ids=$fixture['ids'];
if($mode==='apply'){
    $method=$args[2]??'native';$sentinel=ok(wp_insert_post(['post_title'=>'Prepared sentinel','post_status'=>'private'],true));update_option('native_prepared_marker','keep');
    // Force destination-generated IDs apart from the source's IDs.
    for($i=0;$i<120;$i++)ok(wp_insert_post(['post_title'=>'Prepared '.$i,'post_status'=>'draft'],true));
    [$earlyManifest,$earlyFiles]=$site->reconstructionMaterials($fixture['ref'],1);$early=json_decode($earlyFiles['content.json'],true);$earlyIds=array_column($early['tables']['posts'],'ID');
    must_native($earlyManifest['through']===1&&!in_array($ids['added'],$earlyIds)&&in_array($ids['delete'],$earlyIds),'Recovery point selection');
    $before=serialize($object->objects);$q=$GLOBALS['wpdb']->num_queries;$start=microtime(true);
    if($method==='native')$result=$site->reconstructNative($fixture['ref'],['isolated'=>true,'author_map'=>[1=>1]],$fixture['through']);
    else $result=$site->restore($fixture['ref'],true,'/tmp',$fixture['through']);
    $stats=['seconds'=>microtime(true)-$start,'queries'=>$GLOBALS['wpdb']->num_queries-$q,'peak_bytes'=>memory_get_peak_usage(true)];
    must_native($before===serialize($object->objects),'Source material changed');
    file_put_contents('/tmp/native-result.json',wp_json_encode($result));
    echo wp_json_encode(['method'=>$method,'stats'=>$stats,'result'=>$result,'source_unchanged'=>true,'recovery_point_selection'=>true,'prepared_page_preserved'=>(bool)get_post($sentinel),'prepared_setting_preserved'=>get_option('native_prepared_marker')==='keep']);return;
}
$r=json_decode(file_get_contents('/tmp/native-result.json'),true);$map=$r['posts'];$terms=$r['terms'];
$article=$map[$ids['article']];$child=$map[$ids['child']];$body=get_post($article)->post_content;$image=$map[$fixture['image']];
$checks=['append'=>str_contains($body,'FORMAL-APPEND'),'addition'=>str_contains(get_post($map[$ids['added']])->post_content,'FORMAL-ADDED'),'draft_excluded'=>!isset($map[$ids['first_draft']]),'unpublished_excluded'=>!isset($map[$ids['unpublish']]),'deleted_excluded'=>!isset($map[$ids['delete']]),'restricted_held'=>!isset($map[$ids['restricted']]),'password_preserved'=>get_post($map[$ids['password']])->post_password==='private-fixture','new_ids'=>true,'parent'=>(int)get_post($child)->post_parent===$map[$ids['parent']],'thumbnail'=>(int)get_post_thumbnail_id($article)===$image,'image_hash'=>hash_file('sha256',get_attached_file($image))===$fixture['image_hash'],'category_parent'=>(int)get_term($terms['category:'.$fixture['subcategory']],'category')->parent===$terms['category:'.$fixture['category']],'category_assignment'=>in_array($terms['category:'.$fixture['subcategory']],wp_get_post_categories($article),true),'tag_assignment'=>in_array($terms['post_tag:'.$fixture['tag']],wp_get_post_terms($article,'post_tag',['fields'=>'ids']),true),'home'=>(int)get_option('page_on_front')===$map[$ids['home']],'news'=>(int)get_option('page_for_posts')===$map[$ids['news']],'old_url_absent'=>!str_contains($body,'http://source.invalid/'),'similar_external_preserved'=>str_contains($body,'https://source.invalid.evil/child/')];
foreach($map as $old=>$new)if((int)$old===$new)$checks['new_ids']=false;
$blocks=parse_blocks($body);$checks['image_editable']=false;foreach($blocks as $block)if($block['blockName']==='core/image'&&($block['attrs']['id']??null)===$image)$checks['image_editable']=true;
$menuItems=wp_get_nav_menu_items($r['menus'][$fixture['menu']]);$checks['menu_relation']=count($menuItems)===2&&(int)$menuItems[1]->menu_item_parent===(int)$menuItems[0]->ID&&(int)$menuItems[1]->object_id===$child;
if($mode==='verify'){echo wp_json_encode(['checks'=>$checks,'article'=>$article,'child'=>$child,'navigation'=>$map[$ids['navigation']],'password'=>$map[$ids['password']],'image_url'=>wp_get_attachment_url($image),'menu'=>$r['menus'][$fixture['menu']],'home'=>$map[$ids['home']]]);return;}
throw new RuntimeException('unknown fixture mode');
