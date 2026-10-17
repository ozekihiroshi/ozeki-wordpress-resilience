<?php
declare(strict_types=1);
require dirname(__DIR__).'/packages/backup-core/autoload.php';
use Ozeki\BackupCore\V0_1_0\Database\DatabaseConnection;
use Ozeki\BackupCore\V0_1_0\Database\Php\PhpMySqlDumper;
use Ozeki\BackupCore\V0_1_0\CompleteStreamWriter;
use Ozeki\BackupCore\V0_1_0\SecureTemporaryFile;
$checks=0;
function check(bool $ok):void { global $checks; if (!$ok) throw new RuntimeException('Contract failed'); ++$checks; }
function rejects(callable $fn):void {try {$fn();} catch (Throwable $e) {check(true);return;} throw new RuntimeException('Expected failure');}
check(!defined('ABSPATH') && !function_exists('add_action'));
rejects(fn()=>new PhpMySqlDumper(chunkSize:0));
$c=new DatabaseConnection('localhost',3306,'synthetic','reader','never-log-me','/tmp/mysql.sock');
check($c->hasSocket() && $c->getSocket()==='/tmp/mysql.sock');
$written='';CompleteStreamWriter::writeAll('abcdef',function($s)use(&$written){$part=substr($s,0,2);$written.=$part;return strlen($part);},'failure');check($written==='abcdef');
rejects(fn()=>CompleteStreamWriter::writeAll('a',fn()=>0,'failure'));
$p=sys_get_temp_dir().'/core-contract-'.bin2hex(random_bytes(8));
try {$h=SecureTemporaryFile::openForWriting($p);fwrite($h,'original');fclose($h);check((fileperms($p)&0777)===0600);rejects(fn()=>SecureTemporaryFile::openForWriting($p));check(file_get_contents($p)==='original');}finally {if(is_file($p))unlink($p);}
$before=glob(sys_get_temp_dir().'/secure-s3-php-dump-*.sql');
rejects(fn()=>(new PhpMySqlDumper())->dump(new DatabaseConnection('127.0.0.1',1,'missing','invalid','invalid')));
check($before===glob(sys_get_temp_dir().'/secure-s3-php-dump-*.sql'));
echo json_encode(['kind'=>'backup_core_contract','passed'=>true,'checks'=>$checks,'wordpress_loaded'=>false]),"\n";
