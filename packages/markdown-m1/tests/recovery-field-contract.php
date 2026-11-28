<?php
// wp eval-file, disposable WordPress with CF7 and the candidate activated.
use OzekiResilience\M1\RecoveryRules;
require_once WP_PLUGIN_DIR.'/ozeki-resilience/src/RecoveryRules.php';
function field_check($ok,$why){if(!$ok)throw new RuntimeException($why);}
$posts=[];foreach([1=>'ozmd_document',2=>'revision',3=>'revision',4=>'wpcf7_contact_form']as $id=>$type)$posts[]=['ID'=>$id,'post_type'=>$type,'post_parent'=>$id===2?1:999];
$meta=[];foreach([[1,'_ozmd_source','<script>original</script>'],[2,'_ozmd_source','# Old source'],[3,'_ozmd_source','Unrelated source'],[1,'_ozmd_original_filename','../technical.md'],[4,'_form','[text custom-name][email custom-email][text custom-subject]'],[4,'_additional_settings',"skip_mail: on\nflamingo_name: \"[custom-name]\"\nflamingo_email: [custom-email]\nflamingo_subject: \"[missing-field]\"\nflamingo_subject: \"[_site_title]\"\nflamingo_subject: \"[custom-subject]<script>bad</script>\"\narbitrary: execute"]]as $i=>$r)$meta[]=['meta_id'=>$i+1,'post_id'=>$r[0],'meta_key'=>$r[1],'meta_value'=>$r[2]];
$data=['tables'=>['posts'=>$posts,'postmeta'=>$meta,'comments'=>[],'commentmeta'=>[],'terms'=>[],'term_taxonomy'=>[],'term_relationships'=>[],'termmeta'=>[]],'options'=>[]];$before=serialize($data);
$result=RecoveryRules::project($data,[]);$out=[];foreach($result['data']['tables']['postmeta']as $m)$out[$m['post_id']][$m['meta_key']]=$m['meta_value'];
field_check(($out[2]['_ozmd_source']??null)==='# Old source','Markdown revision source lost');
field_check(!isset($out[3]['_ozmd_source']),'Unrelated revision allowed');
field_check($out[1]['_ozmd_source']==='<script>original</script>','Original transformed');
field_check($out[1]['_ozmd_original_filename']==='technical.md','Filename treated as a path');
$lines=$out[4]['_additional_settings'];field_check(str_contains($lines,'[custom-name]')&&str_contains($lines,'[custom-email]'),'Existing form field mapping lost');
field_check(!str_contains($lines,'missing-field')&&!str_contains($lines,'_site_title')&&!str_contains($lines,'script')&&!str_contains($lines,'arbitrary'),'Unrecognized CF7 directive applied');
field_check(serialize($data)===$before,'Input original mutated');
echo "Field contracts: revision parent, original, filename, existing CF7 field references PASS\n";
