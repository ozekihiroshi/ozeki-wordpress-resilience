<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\SiteSnapshot;
use OzekiResilience\M1\Plugin;
if(!str_starts_with(home_url(),'http://owr-coexist-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);
function mustExtra($x,$m){if(!$x)throw new RuntimeException($m);}
$u=wp_upload_dir();$image=$u['basedir'].'/coexist.png';$original=file_get_contents($image);$snapshot=new SiteSnapshot((new Plugin())->store());
$unknown=$u['basedir'].'/coexist:unknown.pdf';mustExtra(!file_exists($unknown),'Never replace an existing fixture');
try{
 file_put_contents($unknown,'Nonconfidential unsupported fixture');$r=$snapshot->capture(true,[]);
 mustExtra(in_array('uploads/coexist:unknown.pdf',array_column($r['excluded_files'],'item'),true),'Unsafe unsupported path must be reported without blocking supported capture');
}finally{unlink($unknown);}
try{
 $f=fopen($image,'wb');ftruncate($f,33*1024*1024);fclose($f);$blocked=false;
 try{$snapshot->capture(true,[]);}catch(RuntimeException $e){$blocked=str_contains($e->getMessage(),'32 MiB');}
 mustExtra($blocked,'Supported oversized media must not be silently omitted');
}finally{file_put_contents($image,$original);}
$guard=$u['basedir'].'/.htaccess';mustExtra(!file_exists($guard),'Never replace an existing guard');
try{
 file_put_contents($guard,"Require all denied\n");$r=$snapshot->capture(true,[]);[$m,$files]=$snapshot->load($r['manifest']);
 mustExtra(!isset($files['uploads/coexist.png']),'Guarded registered file must not be saved as public');
 mustExtra(in_array('uploads/coexist.png',array_column($r['excluded_files'],'item'),true),'Guarded omission must be visible');
}finally{unlink($guard);}
echo "Supported limit and guarded media capture PASS\n";
