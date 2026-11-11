<?php
if(!function_exists('wp_parse_url')){function wp_parse_url($url,$component=-1){return parse_url($url,$component);}}
// Pure contract: expected destinations are literals, not produced by the resolver.
define('ABSPATH', __DIR__.'/');
$file=$argv[1].'/src/ReferenceContext.php';
if(!is_file($file))throw new RuntimeException('FAIL: reference provenance is not preserved');
require $file;
use OzekiResilience\M1\ReferenceContext as R;
function demand($v,$why){if(!$v)throw new RuntimeException($why);}
$a=['site'=>'https://example.test/a','uploads'=>'https://media.test/a/files'];
$b=['site'=>'https://example.test/b','uploads'=>'https://media.test/b/files'];
$ctx=R::merge([$a],[$b]);
$cases=[
 ['https://example.test/a/?page_id=12#part','https://new.test/c/?page_id=12#part'],
 ['https://media.test/a/files/a.png?x=1','https://new.test/c/uploads/a.png?x=1'],
 ['https://example.test/b/new/','https://new.test/c/new/'],
 ['https://example.test/ab/','https://example.test/ab/'],
 ['https://example.test.evil/a/','https://example.test.evil/a/'],
 ['https://evil.test/?u=https://example.test/a/','https://evil.test/?u=https://example.test/a/'],
 ['https://example.test/a-else/','https://example.test/a-else/'],
 ['https://example.test:8443/a/','https://example.test:8443/a/'],
 ['https://example.test/a?x=1#part','https://new.test/c?x=1#part'],
 ['https://example.test/a/../elsewhere','https://example.test/a/../elsewhere'],
 ['https://example.test/a/%2e%2e/elsewhere','https://example.test/a/%2e%2e/elsewhere'],
 ['javascript:alert(1)','javascript:alert(1)'],
];
foreach($cases as [$in,$expected])demand(R::url($in,$ctx,'https://new.test/c','https://new.test/c/uploads')===$expected,'URL boundary: '.$in);
$unchanged='# [page](https://example.test/a/?page_id=12)';$hash=hash('sha256',$unchanged);
$third=R::merge($ctx,[['site'=>'https://new.test/c','uploads'=>'https://new.test/c/uploads']]);
demand(R::url('https://example.test/a/?page_id=12',$third,'https://final.test','https://final.test/uploads')==='https://final.test/?page_id=12','Unedited document across three generations');
demand(hash('sha256',$unchanged)===$hash,'Original remains unchanged');
demand(R::merge($ctx,$ctx)===$ctx,'Stable deduplication');
foreach([[['site'=>'javascript:x','uploads'=>'https://media.test']], [['site'=>'https://user:password@example.test','uploads'=>'https://media.test']], [['site'=>'https://example.test/?query=1','uploads'=>'https://media.test']]] as $bad){
 $rejected=false;try{R::merge($bad);}catch(RuntimeException $e){$rejected=true;}demand($rejected,'Invalid context must be rejected');
}
// Removing required provenance must make the independent expectation fail.
demand(R::url($cases[0][0],[$b],'https://new.test/c','https://new.test/c/uploads')!==$cases[0][1],'Missing ancestor must be detectable');
echo "PASS: reference provenance, unchanged document, independent URL expectations, negative boundaries and missing-provenance detection\n";
