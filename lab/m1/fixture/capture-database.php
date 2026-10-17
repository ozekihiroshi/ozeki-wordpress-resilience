<?php
declare(strict_types=1);
use Ozeki\BackupCore\V0_1_0\Database\DatabaseConnection;
use Ozeki\BackupCore\V0_1_0\Database\Php\PhpMySqlDumper;
if (getenv('OWR_FIXTURE') !== '1' || getenv('WORDPRESS_DB_NAME') !== 'owr_source') {
    throw new RuntimeException('Dedicated synthetic source required');
}
require '/backup-core/autoload.php';
$c = new DatabaseConnection('source-db', 3306, 'owr_source', 'owr_source',
    getenv('WORDPRESS_DB_PASSWORD'));
$result = (new PhpMySqlDumper())->dump($c);
try {
    if (readfile($result->getPath()) === false) {
        throw new RuntimeException('Cannot stream database dump');
    }
} finally {
    unlink($result->getPath());
}