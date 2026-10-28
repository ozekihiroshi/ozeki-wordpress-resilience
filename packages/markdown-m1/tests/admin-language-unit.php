<?php
define('ABSPATH',__DIR__.'/');
require $argv[1].'/src/Plugin.php';
$locale='ja';
function determine_locale(){return $GLOBALS['locale'];}
function esc_html($v){return htmlspecialchars((string)$v,ENT_QUOTES,'UTF-8');}
function esc_attr($v){return esc_html($v);}
function esc_url($v){return esc_html($v);}
function wp_timezone(){return new DateTimeZone('Asia/Tokyo');}
function checked($a,$b,$echo=false){return $a==$b?'checked="checked"':'';}
function selected($a,$b,$echo=false){return $a==$b?'selected="selected"':'';}
function admin_url($p){return '/wp-admin/'.$p;}
function wp_nonce_field($v){echo '<input name="_wpnonce" value="fixture">';}
function checkLanguage($v,$why){if(!$v)throw new RuntimeException($why);}
ob_start();OzekiResilience\M1\Plugin::renderGfsSettings([]);$ja=ob_get_clean();
checkLanguage(str_contains($ja,'定期保存')&&str_contains($ja,'日曜日')&&str_contains($ja,'開始時刻')&&str_contains($ja,'保持期間'),'Japanese optional settings');
$method=new ReflectionMethod(OzekiResilience\M1\Plugin::class,'form');$method->setAccessible(true);
ob_start();$method->invoke(new OzekiResilience\M1\Plugin(),'whole_initial');$jaForm=ob_get_clean();
$locale='en_US';ob_start();OzekiResilience\M1\Plugin::renderGfsSettings([]);$en=ob_get_clean();
checkLanguage(str_contains($en,'Weekly / monthly / yearly Checkpoints')&&str_contains($en,'Sunday')&&!preg_match('/[ぁ-んァ-ヶ一-龠]/u',$en),'English optional settings');
ob_start();$method->invoke(new OzekiResilience\M1\Plugin(),'whole_initial');$enForm=ob_get_clean();
checkLanguage($enForm===$jaForm&&str_contains($enForm,'value="whole_initial"'),'Form action and operation values unchanged');
checkLanguage(OzekiResilience\M1\AdminText::message('接続とバージョン管理を確認しました。')==='Connection and versioning confirmed.','Cached result follows English language');
$locale='ja';checkLanguage(OzekiResilience\M1\AdminText::message('Connection and versioning confirmed.')==='接続とバージョン管理を確認しました。','Cached result follows Japanese language');
echo "PASS Japanese/English schedule fields, unchanged form parameters and cached result localization.\n";
