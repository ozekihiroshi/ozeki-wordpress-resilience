<?php
require $argv[1].'/src/SiteSnapshot.php';
define('ARRAY_A','ARRAY_A');
function maybe_serialize($v){return is_array($v)?serialize($v):$v;}
function update_option($k,$v,$autoload=null){global $wpdb;if($wpdb->failWrite){$wpdb->last_error='Injected option write failure';return false;}$next=(string)maybe_serialize($v);$old=$wpdb->values[$k]??null;$wpdb->values[$k]=$next;return $old!==$next;}
class ErrorDB {
 public string $last_error='';public string $options='options';public array $values=[];public bool $failWrite=false,$failRead=false,$failQuery=false;public array $queries=[];
 function prepare($q,...$a){return $a[0];}
 function get_row($key,$format){if($this->failRead){$this->last_error='Injected read failure';return null;}return array_key_exists($key,$this->values)?['option_value'=>$this->values[$key]]:null;}
 function query($sql){$this->queries[]=$sql;if($this->failQuery){$this->last_error='Injected transaction failure';return false;}return 0;}
}
function ck($b,$m){if(!$b)throw new RuntimeException($m);}
function rejects($f,$text){try{$f();}catch(RuntimeException $e){ck(str_contains($e->getMessage(),$text),'Cause retained');return;}throw new RuntimeException('Failure not detected');}
$wpdb=new ErrorDB();
foreach(['value','',false,0,['nested'=>['value'=>1]]] as $v){Owr\M1\SiteSnapshot::writeOption('test',$v);Owr\M1\SiteSnapshot::writeOption('test',$v);}
$wpdb->failWrite=true;rejects(fn()=>Owr\M1\SiteSnapshot::writeOption('test','new'),'Injected option write failure');$wpdb->failWrite=false;
$wpdb->failRead=true;rejects(fn()=>Owr\M1\SiteSnapshot::writeOption('test','new'),'Cannot persist recovery option');$wpdb->failRead=false;$wpdb->last_error='';
$m=new ReflectionMethod(Owr\M1\SiteSnapshot::class,'transaction');$m->setAccessible(true);
foreach(['START TRANSACTION','COMMIT'] as $sql){$wpdb->failQuery=false;$m->invoke(null,$sql);$wpdb->failQuery=true;rejects(fn()=>$m->invoke(null,$sql),$sql.' failed');}
echo "PASS unchanged/empty/false/zero/array options; failed write/read; failed START/COMMIT. Synthetic DB failures, not interruption/restart acceptance.\n";
