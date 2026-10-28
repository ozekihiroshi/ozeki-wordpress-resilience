<?php
// Test infrastructure only. Never included in the product ZIP.
add_filter('pre_wp_mail',fn()=>false);
$ozeki_resilience_test_transport=function($options){
    $options['credentials']=['key'=>'test','secret'=>'test'];
    $options['handler']=function($command){
        $name=$command->getName();$args=$command->toArray();
        if(is_file('/lab/setup-commands.log'))file_put_contents('/lab/setup-commands.log',$name."\n",FILE_APPEND);
        $control=json_decode(@file_get_contents('/lab/control.json')?:'{}',true);
        if (($control['fail']??'')==='s3' && $name==='PutObject') throw new RuntimeException('Injected S3 failure');
        if (($control['fail']??'')==='history' && $name==='PutObject' && str_contains($args['Key'],'/history/')) throw new RuntimeException('Injected formal history failure');
        if (is_file('/lab/live')) {
            $id=bin2hex(random_bytes(12));
            if (isset($args['Body'])) {$args['body64']=base64_encode((string)$args['Body']);unset($args['Body']);}
            if (isset($args['ObjectLockRetainUntilDate'])) $args['ObjectLockRetainUntilDate']=$args['ObjectLockRetainUntilDate']->format(DATE_ATOM);
            file_put_contents('/lab/ipc/'.$id.'.tmp',json_encode(['operation'=>$name,'args'=>$args]));
            rename('/lab/ipc/'.$id.'.tmp','/lab/ipc/'.$id.'.request');
            $end=microtime(true)+180;
            while (!is_file('/lab/ipc/'.$id.'.response') && microtime(true)<$end) usleep(100000);
            $reply=json_decode(file_get_contents('/lab/ipc/'.$id.'.response'),true);
            if (empty($reply['success'])) throw new RuntimeException('Live S3 test transport: '.($reply['error']??'unknown'));
            $r=$reply['result'];if(isset($r['body64'])){$r['Body']=base64_decode($r['body64']);unset($r['body64']);}
        } else {
            $root='/lab/objects/';$key=$args['Key']??'';$path=$root.$key;
            if (($control['fail']??'')==='setup') throw new RuntimeException('Injected access failure with private request details');
            if ($name==='GetBucketVersioning') {$r=['Status'=>($control['versioning']??'Enabled')];}
            elseif ($name==='PutObject') {
                if (is_file($path)) throw new RuntimeException('412 create-only');
                if (!is_dir(dirname($path))) mkdir(dirname($path),0777,true);
                file_put_contents($path,(string)$args['Body']);$r=['VersionId'=>hash_file('sha256',$path)];
            } elseif ($name==='GetObject') {
                if (!is_file($path)) throw new RuntimeException('404');
                $version=hash_file('sha256',$path);
                if (isset($args['VersionId']) && $args['VersionId']!==$version) throw new RuntimeException('Wrong version');
                $r=['Body'=>file_get_contents($path),'VersionId'=>$version];
            } elseif ($name==='ListObjectsV2') {
                $r=['Contents'=>[]];
                if (is_dir($root)) foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $file) {
                    $k=substr($file->getPathname(),strlen($root));
                    if (str_starts_with($k,$args['Prefix']) && (!isset($args['StartAfter']) || strcmp($k,$args['StartAfter'])>0)) $r['Contents'][]=['Key'=>$k];
                }
            } else throw new RuntimeException('Unexpected SDK command: '.$name);
        }
        return \GuzzleHttp\Promise\Create::promiseFor(new \Aws\Result($r));
    };
    return $options;
};
add_filter('ozeki_resilience_m1_s3_options',$ozeki_resilience_test_transport);
add_filter('owr_m1_s3_options',$ozeki_resilience_test_transport); // Previous submitted version, isolated upgrade fixture only.
add_action('save_post_ozmd_document',function($id){
    $c=json_decode(@file_get_contents('/lab/control.json')?:'{}',true);
    if (($c['fail']??'')==='wordpress') update_post_meta($id,'_ozmd_source','INJECTED INCOMPLETE APPLY');
    if (($c['fail']??'')==='stop') exit;
},100);
