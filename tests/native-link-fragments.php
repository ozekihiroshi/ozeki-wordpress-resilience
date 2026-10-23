<?php
require __DIR__.'/../src/NativeMaterialsEditor.php';
function wp_parse_url($url,$part){return parse_url($url,$part);}
function home_url(){return 'https://source.invalid';}
function url_to_postid($url){return str_starts_with($url,'https://source.invalid/')?7:0;}
function attachment_url_to_postid($url){return 0;}
function get_post_meta(...$args){return 'company';}
$method=new ReflectionMethod(Owr\NativeMaterialsEditor::class,'portable');$method->setAccessible(true);
foreach(['https://source.invalid/?p=7#section','#section'] as $url){
 $rejected=false;try{$method->invoke(null,'<p><a href="'.$url.'">text</a></p>');}catch(InvalidArgumentException){$rejected=true;}
 if(!$rejected)throw new RuntimeException('Internal fragment silently lost');
}
$html=$method->invoke(null,'<p><a href="https://external.invalid/page#section">text</a></p>');
if(!str_contains($html,'#section'))throw new RuntimeException('External fragment lost');
$html=$method->invoke(null,'<p><a href="https://source.invalid/?p=7">text</a></p>');
if(!str_contains($html,'asset:company'))throw new RuntimeException('Protected page link broken');
echo "Native link fragments: 4 checks PASS\n";
