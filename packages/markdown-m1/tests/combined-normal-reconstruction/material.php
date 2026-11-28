<?php
use OzekiResilience\M1\{Store,SiteSnapshot,NativeReconstruction,MarkdownReconstruction,TableReconstruction,ContactFormReconstruction,FlamingoReconstruction,MemberReconstruction,AcfReconstruction,AcfHistory,UpdateContract};
spl_autoload_register(function($n){$p='OzekiResilience\\M1\\';if(str_starts_with($n,$p)){$f='/tmp/product/src/'.substr($n,strlen($p)).'.php';if(is_file($f))require_once $f;}});
wp_set_current_user(1);$mode=$args[0];
if($mode==='native-source'){
 require_once ABSPATH.'wp-admin/includes/file.php';require_once ABSPATH.'wp-admin/includes/media.php';require_once ABSPATH.'wp-admin/includes/image.php';
 file_put_contents('/tmp/diagram.png',base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jp1sAAAAASUVORK5CYII='));
 $image=media_handle_sideload(['name'=>'diagram.png','tmp_name'=>'/tmp/diagram.png'],0,'Diagram');if(is_wp_error($image))throw new RuntimeException($image->get_error_message());
 $cat=wp_insert_term('Technical','category')['term_id'];
 $page=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_title'=>'Public explanation','post_content'=>'PUBLIC-EXPLANATION <img src="'.wp_get_attachment_url($image).'" alt="Diagram"/>','post_author'=>1]);
 $article=wp_insert_post(['post_type'=>'post','post_status'=>'publish','post_title'=>'Public article','post_content'=>'ARTICLE-MATERIAL','post_author'=>1]);wp_set_object_terms($article,[$cat],'category');
 $menu=wp_create_nav_menu('Technical menu');wp_update_nav_menu_item($menu,0,['menu-item-object-id'=>$page,'menu-item-object'=>'page','menu-item-type'=>'post_type','menu-item-status'=>'publish']);
 $g=acf_import_field_group(['key'=>'group_combined','title'=>'Technical fields','fields'=>[['key'=>'field_combined_caption','name'=>'technical_caption','label'=>'Technical caption','type'=>'text','instructions'=>'説明を入力']],'location'=>[[['param'=>'post_type','operator'=>'==','value'=>'page']]],'active'=>true]);
 echo wp_json_encode(['image'=>$image,'url'=>wp_get_attachment_url($image),'page'=>$page,'article'=>$article,'menu'=>$menu,'acf_group'=>$g['ID']]);return;
}
if($mode==='capture'){
 // Production capture and formal replay contracts; only storage is kept local.
 $site=new SiteSnapshot(new Store(new stdClass(),['bucket'=>'not-used','prefix'=>'isolated/']));
 $d=(new ReflectionMethod($site,'data'))->invoke($site);$files=[];$u=wp_upload_dir();
 foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($u['basedir'],FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$files['uploads/'.substr($f->getPathname(),strlen($u['basedir'])+1)]=file_get_contents($f->getPathname());
 $m=['source_url'=>home_url(),'source_upload_url'=>$u['baseurl'],'through'=>0];
 $files['content.json']=Store::json($d);file_put_contents('/tmp/combined-baseline.bin',serialize([$m,$files]));
 echo wp_json_encode(['post_count'=>count($d['tables']['posts']),'member_count'=>count($d['membership']['users']),'has_membership'=>isset($d['membership']),'receipts'=>count($d['flamingo_inputs']??[])]);return;
}
if($mode==='select'){
 [$m,$files]=unserialize(file_get_contents('/tmp/combined-baseline.bin'),['allowed_classes'=>false]);$d=json_decode($files['content.json'],true);
 $id=(int)$args[1];AcfHistory::replay($d,Store::json(AcfHistory::capture($id)),['origin_id'=>$id]);$m['through']=1;$files['content.json']=Store::json($d);
 file_put_contents('/tmp/combined-selected.bin',serialize([$m,$files]));
 $plans=[];foreach(['markdown'=>MarkdownReconstruction::class,'table'=>TableReconstruction::class,'cf7'=>ContactFormReconstruction::class,'flamingo'=>FlamingoReconstruction::class,'members'=>MemberReconstruction::class,'acf'=>AcfReconstruction::class] as $name=>$class){try{$plans[$name]=$class::plan($m,$files);}catch(Throwable $e){$plans[$name]=['error'=>$e->getMessage()];}}
 echo Store::json($plans);return;
}
if($mode==='native'){
 [$m,$files]=unserialize(file_get_contents('/tmp/combined-selected.bin'),['allowed_classes'=>false]);
 try{$r=(new NativeReconstruction())->run($m,$files,['isolated'=>true,'author_map'=>[1=>1]]);echo Store::json(['result'=>$r]);}
 catch(Throwable $e){echo Store::json(['error'=>$e->getMessage(),'journal'=>get_option('ozeki_resilience_native_reconstruction')]);}return;
}
if($mode==='flamingo'){
 $p=json_decode(file_get_contents('/tmp/fl-plan.json'),true);$map=json_decode(file_get_contents('/tmp/cf-map.json'),true);
 echo Store::json(FlamingoReconstruction::run($p,$map,'/tmp/fl-journal.json',true));return;
}
throw new RuntimeException('Unknown test mode');
