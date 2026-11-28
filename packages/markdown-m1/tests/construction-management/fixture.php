<?php
define('OWR_CONSTRUCTION_ISOLATED',true);define('OWR_CONSTRUCTION_PERSISTENT',true);
spl_autoload_register(function($name){$prefix='OzekiResilience\\M1\\';if(str_starts_with($name,$prefix)){$file='/tmp/product/src/'.substr($name,strlen($prefix)).'.php';if(is_file($file))require_once $file;}});
final class ManagedFixtureObjects {
    private function path($k){return '/tmp/construction-objects/'.hash('sha256',$k).'.json';}
    function putObject($a){
        if(!is_dir('/tmp/construction-objects'))mkdir('/tmp/construction-objects',0700);
        $p=$this->path($a['Key']);$f=fopen($p,'x');if(!$f)throw new RuntimeException('exists');
        $r=['key'=>$a['Key'],'base64'=>base64_encode($a['Body']),'VersionId'=>hash('sha256',$a['Body'])];
        $raw=json_encode($r);if(fwrite($f,$raw)!==strlen($raw))throw new RuntimeException('short write');fclose($f);chmod($p,0600);return $r;
    }
    function getObject($a){$p=$this->path($a['Key']);if(!is_file($p))throw new RuntimeException('missing',404);$r=json_decode(file_get_contents($p),true);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return ['Body'=>base64_decode($r['base64']),'VersionId'=>$r['VersionId']];}
    function listObjectsV2($a){$rows=[];foreach(glob('/tmp/construction-objects/*.json') as $p){$r=json_decode(file_get_contents($p),true);if(str_starts_with($r['key'],$a['Prefix'])&&$r['key']>($a['StartAfter']??''))$rows[]=['Key'=>$r['key']];}return ['Contents'=>$rows];}
}
add_action('plugins_loaded',function(){
    $config=(array)get_option('ozeki_resilience_m1_config',[]);
    OzekiResilience\M1\ConstructionAdmin::boot(new OzekiResilience\M1\Store(new ManagedFixtureObjects(),$config));
});
