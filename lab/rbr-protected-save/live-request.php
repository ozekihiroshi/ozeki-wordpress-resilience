<?php
// Test-only private Unix socket transport; no AWS credentials in WordPress.
final class OwrLiveFailure extends RuntimeException {
 public function __construct(private int $status){parent::__construct('Experiment transport HTTP '.$status);}
 public function getStatusCode():int{return $this->status;}
}
function owr_live_request(string $op,array $args):array {
 if(isset($args['Body'])){$args['body64']=base64_encode(stream_get_contents($args['Body']));unset($args['Body']);}
 if(isset($args['ObjectLockRetainUntilDate']))$args['ObjectLockRetainUntilDate']=$args['ObjectLockRetainUntilDate']->format(DATE_ATOM);
 $socket=stream_socket_client('unix:///lab/broker.sock',$errno,$error,5);
 if(!$socket)throw new OwrLiveFailure(502);
 try{
  stream_set_timeout($socket,240);
  $data=json_encode(['operation'=>$op,'args'=>$args],JSON_THROW_ON_ERROR)."\n";
  while($data!==''){$n=fwrite($socket,$data);if(!$n)throw new OwrLiveFailure(502);$data=substr($data,$n);}
  $line=fgets($socket,12*1024*1024);if($line===false)throw new OwrLiveFailure(502);
  $reply=json_decode($line,true,64,JSON_THROW_ON_ERROR);if(!$reply['success'])throw new OwrLiveFailure($reply['status']);
  $r=$reply['result'];
  if(isset($r['body64'])){$r['Body']=GuzzleHttp\Psr7\Utils::streamFor(base64_decode($r['body64'],true));unset($r['body64']);}
  if(isset($r['LastModified']))$r['LastModified']=new DateTimeImmutable($r['LastModified']);
  if(isset($r['Retention']['RetainUntilDate']))$r['Retention']['RetainUntilDate']=new DateTimeImmutable($r['Retention']['RetainUntilDate']);
  return $r;
 }finally{fclose($socket);}
}
