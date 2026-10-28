<?php
// Run with wp eval-file in an isolated installed WordPress, never a production site.
function ozekre_assert($ok,$message){if(!$ok)throw new RuntimeException($message);}
function ozekre_reject($value){try{OzekiResilience\M1\Plugin::snapshotReference($value);}catch(Throwable $e){return;}throw new RuntimeException('Invalid reference accepted');}
$ref=['key'=>'site-snapshots/'.str_repeat('a',64).'/manifest.json','version'=>'aB_+/.=-123','sha256'=>str_repeat('b',64)];
ozekre_assert(OzekiResilience\M1\Plugin::snapshotReference(wp_json_encode($ref))===$ref,'Valid fixed reference changed');
foreach([null,[],1,'null','[]','{}','{"key":[]}',str_repeat(' ',4097)] as $value)ozekre_reject($value);
foreach(['key'=>['../manifest.json','site-snapshots/x/manifest.json','<script>','https://other.test/a',[]],'version'=>['','null','<script>',"a\n",[],str_repeat('a',1025)],'sha256'=>['x',str_repeat('G',64),[]]] as $key=>$values)foreach($values as $value){$bad=$ref;$bad[$key]=$value;ozekre_reject(wp_json_encode($bad));}
ozekre_reject(wp_json_encode($ref+['injected'=>'<script>']));
foreach(["# 日本語\n\n```html\n<script>alert(1)</script>\n```\n",'a:0:{}',"![image](https://example.test/a.png)\n"] as $source)ozekre_assert(OzekiResilience\M1\Plugin::validatedMarkdown($source)===$source,'Original bytes changed');
foreach([[],null,"a\0b","\xff",str_repeat('x',5*1024*1024+1)] as $source){$rejected=false;try{OzekiResilience\M1\Plugin::validatedMarkdown($source);}catch(Throwable $e){$rejected=true;}ozekre_assert($rejected,'Invalid Markdown accepted');}
update_option('owr_site_origin_url','https://old.example');
$p=new OzekiResilience\M1\Plugin();
$html='<form action="https://old.example/send"><input name="test" value="retained"></form><a href="https://old.example/a?x=1&amp;y=2">Link</a><img src="https://old.example/a.jpg" srcset="https://old.example/a.jpg 1x, https://old.example/b.jpg 2x"><p>https://old.example/raw</p><script type="application/json">{"url":"https://old.example/data"}</script><a href="https://old.example.evil/a">Other host</a>';
$result=$p->relocateContent($html);$to=rtrim(home_url(),'/');
$tags=new WP_HTML_Tag_Processor($result);$attributes=[];
while($tags->next_tag())foreach(['action','href','srcset'] as $name){$value=$tags->get_attribute($name);if(is_string($value))$attributes[$name][]=$value;}
ozekre_assert(in_array($to.'/send',$attributes['action']??[],true)&&in_array($to.'/a?x=1&y=2',$attributes['href']??[],true),'URLs not escaped/rebased: '.$result);
ozekre_assert(str_contains($result,'srcset="'.$to.'/a.jpg 1x, '.$to.'/b.jpg 2x"'),'Responsive images not rebased');
ozekre_assert(str_contains($result,'<input name="test" value="retained">')&&str_contains($result,'<p>https://old.example/raw</p>')&&str_contains($result,'"https://old.example/data"'),'Unrelated shortcode HTML/text changed');
ozekre_assert(str_contains($result,'https://old.example.evil/a'),'Host boundary broken');
update_option('owr_site_origin_url','javascript:alert(1)');ozekre_assert($p->relocateContent($html)===$html,'Unsafe origin accepted');delete_option('owr_site_origin_url');
add_filter('file_mod_allowed','__return_false');$denied=false;
try{(new OzekiResilience\M1\SiteSnapshot($p->store()))->restore($ref,true,'/tmp/not-used');}catch(Throwable $e){$denied=str_contains($e->getMessage(),'does not allow theme/plugin file changes');}
remove_filter('file_mod_allowed','__return_false');ozekre_assert($denied,'Host file policy ignored');
echo "PASS review input rejection, byte-preserved Markdown, escaped URL attributes, shortcode/form preservation, srcset and host file policy.\n";
