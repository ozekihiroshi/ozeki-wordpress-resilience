<?php
if (getenv('OWR_FIXTURE') !== '1' || getenv('WORDPRESS_DB_NAME') !== 'owr_source') { throw new RuntimeException('Source fixture required.'); }
$_SERVER['HTTP_HOST'] = 'localhost:18081'; $_SERVER['SERVER_PORT'] = '18081'; $_SERVER['REQUEST_URI'] = '/';
define('WP_INSTALLING', true);
require '/var/www/html/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/upgrade.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
if (is_blog_installed()) { throw new RuntimeException('Already installed; use verify. No reseeding existing data.'); }
wp_install('OWR Model A synthetic site', 'owradmin', 'admin@example.invalid', false, '', getenv('OWR_ADMIN_PASSWORD'));
update_option('home', 'http://localhost:18081'); update_option('siteurl', 'http://localhost:18081');
update_option('permalink_structure', '');
switch_theme('twentytwentyfive');
if (! wp_get_theme()->exists()) { throw new RuntimeException('Expected theme missing.'); }
$activated = activate_plugin('ozeki-database-backup-for-s3/ozeki-database-backup-for-s3.php');
if (is_wp_error($activated)) { throw new RuntimeException('Backup plugin activation failed.'); }
// Never configure cloud credentials or a bucket in this phase.
update_option('owr_fixture_nested', ['message' => '復旧基準 🌱', 'enabled' => true, 'count' => 7], false);
function insertFixture(array $data): int {
    $id = wp_insert_post($data, true); if (is_wp_error($id)) { throw new RuntimeException('Fixture creation failed.'); } return $id;
}
$home = insertFixture(['post_type'=>'page','post_status'=>'publish','post_name'=>'owr-home','post_title'=>'会社案内','post_content'=>'<p>OWR-HOME 日本語と絵文字 🌱</p>']);
$services = insertFixture(['post_type'=>'page','post_status'=>'publish','post_name'=>'owr-services','post_title'=>'サービス','post_content'=>'<p>OWR-SERVICES 技術支援</p>']);
$contact = insertFixture(['post_type'=>'page','post_status'=>'publish','post_name'=>'owr-contact','post_title'=>'お問い合わせ','post_content'=>'<p>OWR-CONTACT 模擬問い合わせ</p>[owr_contact]']);
$post = insertFixture(['post_type'=>'post','post_status'=>'publish','post_name'=>'owr-news','post_title'=>'復旧検証のお知らせ','post_content'=>'<p>OWR-NEWS 検証用の記事</p>']);
$image = imagecreatetruecolor(64, 48); imagefill($image,0,0,imagecolorallocate($image,20,100,130)); ob_start(); imagepng($image); $png=ob_get_clean(); imagedestroy($image);
// Fixed minimal PDF with computed byte offsets.
$stream = "BT /F1 12 Tf 20 70 Td (OWR synthetic PDF) Tj ET\n";
$objects = ['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 240 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',"<< /Length " . strlen($stream) . " >>\nstream\n" . $stream . 'endstream'];
$pdf = "%PDF-1.4\n"; $offsets = [0];
foreach ($objects as $i=>$object) { $offsets[]=strlen($pdf); $pdf.=($i+1)." 0 obj\n".$object."\nendobj\n"; }
$xref=strlen($pdf); $pdf.="xref\n0 6\n0000000000 65535 f \n";
foreach(array_slice($offsets,1) as $offset){$pdf.=sprintf("%010d 00000 n \n",$offset);}
$pdf.="trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n$xref\n%%EOF\n";
$assets=[];
foreach ([['owr-image.png','image/png',$png],['owr-guide.pdf','application/pdf',$pdf]] as [$name,$mime,$bytes]) {
    $upload=wp_upload_bits($name,null,$bytes); if($upload['error']){throw new RuntimeException('Upload failed.');}
    $id=wp_insert_attachment(['post_title'=>$name,'post_mime_type'=>$mime,'post_status'=>'inherit'],$upload['file'],$home,true);
    if(is_wp_error($id)){throw new RuntimeException('Attachment failed.');}
    wp_update_attachment_metadata($id,wp_generate_attachment_metadata($id,$upload['file']));
    $assets[$name]=['id'=>$id,'relative'=>get_post_meta($id,'_wp_attached_file',true),'sha256'=>hash_file('sha256',$upload['file']),'bytes'=>filesize($upload['file'])];
}
$homeContent='<p>OWR-HOME 日本語と絵文字 🌱</p><a href="'.esc_url(get_permalink($services)).'">Services</a> <a href="'.esc_url(get_permalink($contact)).'">Contact</a><img alt="OWR image" src="'.esc_url(wp_get_attachment_url($assets['owr-image.png']['id'])).'"><a href="'.esc_url(wp_get_attachment_url($assets['owr-guide.pdf']['id'])).'">PDF</a>';
wp_update_post(['ID'=>$home,'post_content'=>$homeContent]);
update_option('show_on_front','page'); update_option('page_on_front',$home);
update_option('owr_fixture_ids',compact('home','services','contact','post','assets'),false);
if(!is_dir('/private/media')){mkdir('/private/media',0700,true);} chmod('/private/media',0700); chown('/private/media','www-data'); chgrp('/private/media','www-data');
echo "Fixture seeded.\n";
