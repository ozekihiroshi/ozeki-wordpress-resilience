<?php
/** Test-only Object Lock metadata; no AWS credentials or requests. */
trait RetentionMemory {
 public array $retentions=[],$extensions=[];
 function rememberRetention($a){if(isset($a['ObjectLockRetainUntilDate']))$this->retentions[$a['Key']]=['Mode'=>$a['ObjectLockMode'],'RetainUntilDate'=>$a['ObjectLockRetainUntilDate']];}
 function getObjectRetention($a){$this->getObject($a);return ['Retention'=>$this->retentions[$a['Key']]??[]];}
 function putObjectRetention($a){$this->getObject($a);if(isset($a['BypassGovernanceRetention']))throw new RuntimeException('Bypass forbidden');$this->extensions[]=$a;$this->retentions[$a['Key']]=$a['Retention'];return [];}
}
