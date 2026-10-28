<?php
// Isolated preparation states; no WordPress, storage or network access.
define('ABSPATH',__DIR__.'/');
if(!class_exists('ZipArchive')){class ZipArchive{}}
if(($argv[2]??'')==='pro')define('ACF_PRO',true);
require $argv[1].'/src/SetupReadiness.php';
use Owr\M1\SetupReadiness as R;
function determine_locale(){return $GLOBALS['locale']??'en_US';}
function get_option($k,$default=false){return $GLOBALS['options'][$k]??$default;}
function acf_get_field_groups(){return [];}
function acf_get_setting($k){return $GLOBALS['acf_version'];}
function esc_html($s){return htmlspecialchars($s,ENT_QUOTES,'UTF-8');}
function check($v,$m){if(!$v)throw new RuntimeException($m);}
class AcfSetupDB {public $posts='posts',$postmeta='postmeta',$options='options';public $definitions=false;function prepare($q,$v){return [$q,$v];}function get_var($q){return is_array($q)?'InnoDB':(str_contains($q,'acf-field-group')&&$this->definitions?1:null);}}
$wpdb=new AcfSetupDB();$wp_version='7.1';$options=[];$acf_version='6.8.10';$c=['bucket'=>'example','region'=>'ap-northeast-1','prefix'=>'site/'];
if(defined('ACF_PRO')){
 check(R::acfMode()==='pro'&&R::acfReady($c),'PRO never blocks article protection');
 $options['owr_setup_baseline']=R::baselineRecord($c,['key'=>'native']);R::requireStart($c);
 foreach(['en_US'=>'ACF PRO fields are outside protection','ja'=>'ACF PROのフィールドは保護対象外'] as $locale=>$message){ob_start();R::render($c);$html=ob_get_clean();check(str_contains($html,$message),'Explicit PRO exclusion');}
 echo "PASS ACF PRO exclusion, bilingual display and unchanged article eligibility.\n";exit;
}
check(R::acfMode()==='unused'&&R::acfRow($c)['unused'],'Unused ACF requires no action');
$wpdb->definitions=true;check(R::acfMode()==='inactive'&&R::acfRow($c)['excluded'],'Inactive stored definitions are not marked unused');
$options['active_plugins']=['advanced-custom-fields/acf.php'];check(!R::acfReady($c),'Free requires an initial save');
$options['owr_setup_baseline']=['identity'=>R::identity($c),'manifest'=>['key'=>'legacy']];check(!R::acfReady($c),'Old marker is not retroactive ACF coverage');
try{R::requireStart($c);throw new LogicException('Missing ACF capture allowed start');}catch(RuntimeException $e){check(str_contains($e->getMessage(),'new trusted initial snapshot'),'Start rejected with next action');}
foreach(['en_US'=>'Create a new trusted initial snapshot','ja'=>'新しい信頼済みの初期保存'] as $locale=>$message){ob_start();R::render($c+['protect'=>true]);$html=ob_get_clean();check(str_contains($html,$message),'Bilingual next step when existing protection is enabled');}
$options['owr_setup_baseline']=R::baselineRecord($c,['key'=>'new']);check(R::acfReady($c),'Matching ACF capture accepted');R::requireStart($c);
check(!R::acfReady(array_replace($c,['prefix'=>'other/'])),'Destination binding');
$acf_version='6.8.11';check(!R::acfReady($c),'Version change requires new capture');
$options['active_plugins']=[];check(R::acfReady($c),'Inactive ACF does not block existing article scope');
echo "PASS unused/inactive/free, legacy marker, initial capture, changed version/destination and bilingual next steps.\n";
