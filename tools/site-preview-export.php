<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'||getenv('OWR_RBR_DISPOSABLE')!=='1')throw new RuntimeException('Dedicated CLI required');
require '/var/www/html/wp-load.php';
require_once __DIR__.'/../src/SiteMaterialsProjection.php';
if(!DISABLE_WP_CRON||!WP_HTTP_BLOCK_EXTERNAL)throw new RuntimeException('Guards required');
$input=json_decode(file_get_contents('/bundle/received.json'),true,64,JSON_THROW_ON_ERROR);
$projection=get_option('owr_site_projection');
if(($projection['state']??null)!=='verified-private'||$projection['receipt']!==$input['receipt'])throw new RuntimeException('Verified target required');
$map=$projection['map'];$replace=[];$pages=[];
foreach($input['site']['entries'] as $row){
 $id=$row['id'];$post=get_post($map[$id]);if(!$post)throw new RuntimeException('Missing target material');
 if($row['kind']==='image'){
  $raw=file_get_contents(get_attached_file($post->ID));$expected=base64_decode($row['data'],true);
  if($raw!==$expected||get_post_meta($post->ID,'_wp_attachment_image_alt',true)!==$row['alt'])throw new RuntimeException('Target image changed');
  $replace[esc_url(wp_get_attachment_url($post->ID))]='data:'.$row['mime'].';base64,'.base64_encode($raw);
 }else{
  if($post->post_status!=='draft'||$post->post_title!==$row['title']||$post->post_content!==owr_material_body($row,$map))throw new RuntimeException('Target content changed');
  $replace[esc_url(home_url('/?p='.$post->ID))]='about:srcdoc#material-'.$id;
  $pages[]=['id'=>$id,'title'=>$post->post_title,'body'=>$post->post_content];
 }
}
$csp="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'";
$html='<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="'.esc_attr($csp).'"><meta name="referrer" content="no-referrer"><title>Private reconstruction preview</title><style>body{font:16px/1.7 sans-serif;margin:24px;max-width:960px}nav{padding:12px;background:#eef2f6}nav a{margin-right:16px}section{border-top:1px solid #ccd;margin-top:32px;padding-top:16px}img{max-width:100%;height:auto}a{color:#174ea6}</style></head><body><p>再構築先から取得した非公開スナップショット。テーマ・動的機能のプレビューではありません。</p><nav>';
foreach($pages as $page)$html.='<a href="about:srcdoc#material-'.esc_attr($page['id']).'">'.esc_html($page['title']).'</a>';
$html.='</nav>';
foreach($pages as $page)$html.='<section id="material-'.esc_attr($page['id']).'"><h1>'.esc_html($page['title']).'</h1>'.strtr($page['body'],$replace).'</section>';
$html.='</body></html>';
echo json_encode(['schema'=>'owr-private-preview-v1','generation'=>$input['receipt']['sha256'],'captured_at'=>time(),'pages'=>array_column($pages,'id'),'html'=>$html],JSON_THROW_ON_ERROR);
