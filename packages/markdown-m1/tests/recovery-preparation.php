<?php
// Run against an isolated WordPress with this plugin active. No S3 or option writes.
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\RecoveryPreparation;
function mustPreparation(bool $ok,string $message): void {if(!$ok)throw new RuntimeException($message);}
$m=['wordpress'=>$wp_version,'source_url'=>'https://source.example.invalid','plugins'=>[]];
foreach(['en_US','ja'] as $locale){
    $filter=static fn()=>$locale;add_filter('determine_locale',$filter);
    $label=$locale==='ja'?'サイトの言語パック':'Site language pack';
    foreach([false,'','en_US','zz_OWR_MISSING','../../invalid',true,42,[]] as $language){
        $rows=RecoveryPreparation::checks($m,['options'=>['WPLANG'=>$language]]);
        $row=array_values(array_filter($rows,static fn($r)=>$r['label']===$label))[0];
        mustPreparation($row['ok']===in_array($language,[false,'','en_US'],true),'Language availability must match WordPress installation requirements');
        if(!$row['ok'])mustPreparation(str_contains($row['next'],$locale==='ja'?'サイトの言語':'Site Language'),'Missing language must identify next action');
    }
    $missing=$m;$missing['wordpress']='999.0';$missing['plugins']=['owr-nonexistent/absent.php'];$missing['software_inventory']['plugins']['owr-nonexistent/absent.php']['version']='1.0';
    $rows=RecoveryPreparation::checks($missing,['options'=>['WPLANG'=>'zz_OWR_MISSING']]);
    $failed=array_column(array_filter($rows,static fn($r)=>!$r['ok']),'label');
    mustPreparation(in_array('WordPress',$failed,true)&&in_array('owr-nonexistent/absent.php',$failed,true)&&in_array($label,$failed,true),'Report multiple missing requirements together');
    $blocked=false;try{RecoveryPreparation::requireReady($missing,['options'=>['WPLANG'=>'zz_OWR_MISSING']]);}catch(RuntimeException $e){$blocked=str_contains($e->getMessage(),$label)&&str_contains($e->getMessage(),'owr-nonexistent/absent.php');}
    mustPreparation($blocked,'Restore guard must use the same requirements as the UI');
    remove_filter('determine_locale',$filter);
}
echo "Recovery preparation language and software contracts PASS\n";
