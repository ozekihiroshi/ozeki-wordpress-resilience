<?php
namespace OzekiResilience\M1 {
    final class Plugin {function config(){return ['protect'=>true];}}
    final class CommentHistory {public static array $calls=[];function enqueue($asset,$source,$attrs){self::$calls[]=[$asset,$source,$attrs];}}
}
namespace {
    // Standalone WordPress API fixture for guarded product includes.
    if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
    require __DIR__.'/../src/Store.php';require __DIR__.'/../src/TableHistory.php';
    class TablePress {const version='3.4.1';}
    function get_option($key){return $key==='active_plugins'?['tablepress/tablepress.php']:'{"last_id":2,"table_post":{}}';}
    $adapter=new OzekiResilience\M1\TableHistory();
    $adapter->capture('delete','settings');$adapter->capture('settings','','','{"custom_css":"original"}');
    $calls=OzekiResilience\M1\CommentHistory::$calls;
    if(count($calls)!==2||$calls[0][0]===$calls[1][0]||json_decode($calls[1][1],true)['settings']!=='{"custom_css":"original"}')throw new RuntimeException('Table ID must not collide with the settings asset.');
    echo "TablePress queue identity and frozen settings checks PASS\n";
}
