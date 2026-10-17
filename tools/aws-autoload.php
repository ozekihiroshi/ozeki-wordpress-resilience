<?php
$root = dirname(__DIR__);
foreach ([$root.'/vendor/autoload.php', $root.'/.local/backup-plugin/vendor/autoload.php'] as $autoload) {
    if (is_file($autoload)) { require_once $autoload; return; }
}
throw new RuntimeException('Run composer install before using AWS tools.');
