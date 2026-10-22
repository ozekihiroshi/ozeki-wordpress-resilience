<?php
declare(strict_types=1);
/** Generates private synthetic inputs; never connects to AWS or WordPress. */
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
use Owr\RbrGenerationCoordinator as Coordinator;
$o=getopt('', ['output:', 'from-result:']);
if (!isset($o['output']) || file_exists($o['output']) || is_link($o['output'])) {
    fwrite(STDERR,"Specify a new --output directory\n");exit(1);
}
mkdir($o['output'],0700,true);$dir=realpath($o['output']);$now=time();
if (isset($o['from-result'])) {
    $previous=json_decode(file_get_contents($o['from-result']),true,64,JSON_THROW_ON_ERROR);
    if (($previous['state']??null)!=='committed' || ($previous['manifest']['site_id']??null)!=='corporate-test') {
        throw new RuntimeException('Expected committed synthetic fixture result');
    }
    $assets=[];
    foreach($previous['manifest']['assets'] as $a){$a['existing']=$a['storage'];unset($a['storage']);$assets[]=$a;}
    $sequence=$previous['manifest']['sequence']+1;$parent=$previous['generation'];
} else {
    $assets=[];
    $add=function(string $id,string $kind,string $bytes,?string $role=null)use(&$assets,$dir):void{
        $path=$dir.'/'.$id.'.input';file_put_contents($path,$bytes);chmod($path,0600);
        $a=['id'=>$id,'revision'=>'rev1','kind'=>$kind,'provenance'=>'s3-first',
            'size_bytes'=>strlen($bytes),'sha256'=>hash('sha256',$bytes),'path'=>$path];
        if($role!==null){$a['role']=$role;}$assets[]=$a;
    };
    foreach(['company','services','contact']as$role){$add($role,'page',Coordinator::encode([
        'title'=>ucfirst($role),'slug'=>$role,'paragraphs'=>['Synthetic corporate '.$role.'; not a real business.']]),$role);}
    $im=imagecreatetruecolor(2,2);ob_start();imagepng($im);$png=ob_get_clean();imagedestroy($im);$add('logo','image',$png);
    $add('profile','profile',Coordinator::encode(['schema'=>'owr-rbr-profile-v1','roles'=>[
        'company'=>'company','services'=>'services','contact'=>'contact']]));
    $add('relations','relations',Coordinator::encode(['edges'=>[
        ['from'=>'company','to'=>'logo','type'=>'image','position'=>0],
        ['from'=>'company','to'=>'services','type'=>'link','position'=>1],
        ['from'=>'services','to'=>'contact','type'=>'navigation','position'=>0]]]));
    $sequence=1;$parent=null;
}
$job=['schema'=>'owr-rbr-save-v1','site_id'=>'corporate-test','sequence'=>$sequence,'parent'=>$parent,
    'operation_id'=>bin2hex(random_bytes(16)),'prepared_at'=>$now,'deadline'=>$now+3600,'assets'=>$assets];
file_put_contents($dir.'/job.json',Coordinator::encode($job));chmod($dir.'/job.json',0600);
echo $dir."/job.json\n";
