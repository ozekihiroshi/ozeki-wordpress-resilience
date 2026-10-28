<?php
// Standalone WordPress API fixture for guarded product includes.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require __DIR__.'/../src/SiteSnapshot.php';
use OzekiResilience\M1\SiteSnapshot;
$guard="# Apache 2.4+\n<IfModule authz_core_module>\n    Require all denied\n</IfModule>\n\n# Apache 2.2\n<IfModule !authz_core_module>\n    Deny from all\n</IfModule>\n";
SiteSnapshot::validateUpload('uploads/wpcf7_uploads/.htaccess',$guard);
SiteSnapshot::validateUpload('uploads/wpcf7_uploads/.htaccess',str_replace("\n","\r\n",$guard));
SiteSnapshot::validateUpload('uploads/image.png','image');
foreach([['uploads/.htaccess',$guard],['uploads/wpcf7_uploads/.htaccess',$guard."Require all granted\n"],['uploads/wpcf7_uploads/.htaccess',''],['uploads/a.php','<?php'],['uploads/a.PHAR','binary']] as [$path,$body]){
 $blocked=false;try{SiteSnapshot::validateUpload($path,$body);}catch(RuntimeException $e){$blocked=true;}if(!$blocked)throw new RuntimeException('Accepted forbidden upload '.$path);
}
echo "PASS CF7 deny-only upload guard and executable rejection\n";