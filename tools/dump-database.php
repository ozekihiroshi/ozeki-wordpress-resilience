<?php
declare(strict_types=1);
require dirname(__DIR__).'/packages/backup-core/autoload.php';
use Ozeki\BackupCore\V0_1_0\Database\DatabaseConnection;
use Ozeki\BackupCore\V0_1_0\Database\Php\PhpMySqlDumper;
try {
 foreach (['OWR_DB_HOST','OWR_DB_NAME','OWR_DB_USER','OWR_DB_PASSWORD'] as $name) {
  if (getenv($name)===false || getenv($name)==='') throw new RuntimeException('Missing database environment');
 }
 $c=new DatabaseConnection(getenv('OWR_DB_HOST'),(int)(getenv('OWR_DB_PORT')?:3306),getenv('OWR_DB_NAME'),getenv('OWR_DB_USER'),getenv('OWR_DB_PASSWORD'));
 $r=(new PhpMySqlDumper())->dump($c);
 try {if(readfile($r->getPath())===false)throw new RuntimeException('Unable to stream dump');}
 finally {unlink($r->getPath());}
} catch(Throwable $e) {fwrite(STDERR,'Database dump failed: '.get_class($e)."\n");exit(1);}
