<?php
declare(strict_types=1);
// Developer CLI only. Input must be captured from the verified pre-application original.
if(PHP_SAPI!=='cli'||$argc!==3){fwrite(STDERR,"Usage: php member-contract-check.php /isolated/site/wp-load.php /private/expected.json\n");exit(2);}
require_once __DIR__.'/MemberContractReadback.php';
try{
    $input=json_decode(file_get_contents($argv[2]),true,512,JSON_THROW_ON_ERROR);
    if(!is_array($input['raw']['membership']??null)||!is_string($input['source_url']??null))throw new RuntimeException('Invalid expected input');
    require $argv[1];
    $raw=$input['raw'];$source=$input['source_url'];
    $observed=MemberContractReadback::observe($raw['membership'],$source);
    // Capture ALL MemberHistory::OPTIONS from the prepared destination BEFORE recovery.
    // Generic installation defaults cannot prove that operator preparation was preserved.
    if(($input['prepared_destination']['version']??null)!==$observed['data']['version']||!is_array($input['prepared_destination']['settings']['wpmembers_settings']??null))throw new RuntimeException('Missing pre-recovery destination settings');
    $prepared=$input['prepared_destination']['settings'];
    if(array_diff(['wpmembers_settings','wpmembers_fields','wpmembers_dialogs','wpmembers_tos'],array_keys($prepared)))throw new RuntimeException('Incomplete pre-recovery destination settings');
    $expected=MemberContractReadback::destinationExpected($raw['membership'],$source,home_url());
    $result=MemberApplicationContract::compare($expected,$observed['data'],$prepared);
    $restrictions=MemberContractReadback::restrictions($raw['tables']['postmeta'],$raw['tables']['posts']);
    $result['errors']=array_merge($result['errors'],$observed['errors'],$restrictions['errors']);$result['pass']=!$result['errors'];
    $result['stage']='separate-request-readback';$result['restrictions_checked']=$restrictions['checked'];
    echo json_encode($result,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n";exit($result['pass']?0:1);
}catch(Throwable $e){echo json_encode(['pass'=>false,'errors'=>[['code'=>'check-failed','path'=>'input-or-runtime']]])."\n";exit(1);}
