<?php
// Isolated live-AWS fixture only. Credentials remain on the EC2 host.
add_filter('pre_wp_mail','__return_false');
add_filter('ozeki_resilience_m1_s3_options',function($options){
    $scope=json_decode(file_get_contents('/lab/aws.json'),true);
    $options['credentials']=['key'=>'isolated','secret'=>'isolated'];
    $options['handler']=function($command)use($scope){
        $a=$command->toArray();$name=$command->getName();
        if(($a['Bucket']??'')!==$scope['bucket']||!in_array($name,['GetObject','PutObject','ListObjectsV2','GetBucketVersioning','GetObjectLockConfiguration','GetObjectRetention'],true))throw new RuntimeException('Outside isolated AWS scope');
        if(isset($a['Key'])&&!str_starts_with($a['Key'],$scope['prefix']))throw new RuntimeException('Outside isolated object prefix');
        if($name==='ListObjectsV2'&&!str_starts_with($a['Prefix']??'',$scope['prefix']))throw new RuntimeException('Unscoped listing');
        $a['ExpectedBucketOwner']=$scope['owner'];
        $control=json_decode(file_get_contents('/lab/control.json'),true);
        if(($control['fail']??'')==='history'&&$name==='PutObject'&&str_contains($a['Key'],'/history/'))throw new RuntimeException('Injected formal-history interruption');
        static $s3=null;
        if(!$s3)$s3=new Aws\S3\S3Client(['version'=>'latest','region'=>'ap-northeast-1','credentials'=>Aws\Credentials\CredentialProvider::instanceProfile(),'http'=>['connect_timeout'=>5,'timeout'=>30],'retries'=>1]);
        return $s3->executeAsync($s3->getCommand($name,$a));
    };
    return $options;
});
