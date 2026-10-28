<?php
/**
 * Plugin Name: Ozeki Resilience
 * Description: Preserve supported site content and confirmed history in Amazon S3; reconstruct it on a prepared WordPress.
 * Plugin URI: https://github.com/ozekihiroshi/ozeki-wordpress-resilience
 * Author: Hiroshi Ozeki
 * Author URI: https://github.com/ozekihiroshi
 * Text Domain: ozeki-resilience
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Version: 0.3.3
 * Requires PHP: 8.1
 * Requires at least: 6.4
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/vendor/autoload.php';
// A scoped Composer package in another plugin can retain the original files ID.
// Load these function namespaces when that shared ID skipped our unscoped file.
if (!function_exists('Aws\\constantly')) {
    require_once __DIR__.'/vendor/aws/aws-sdk-php/src/functions.php';
}
if (!function_exists('JmesPath\\search')) {
    require_once __DIR__.'/vendor/mtdowling/jmespath.php/src/JmesPath.php';
}
require_once __DIR__.'/src/Identifiers.php';
require_once __DIR__.'/src/Startup.php';
add_action('plugins_loaded', [\OzekiResilience\M1\Startup::class, 'prepare'], -100);
require_once __DIR__.'/src/Store.php';
require_once __DIR__.'/src/SiteSnapshot.php';
require_once __DIR__.'/src/Plugin.php';
require_once __DIR__.'/src/CommentHistory.php';
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\CommentHistory())->boot(); });
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\Plugin())->boot(); });

require_once __DIR__.'/src/FormHistory.php';
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\FormHistory())->boot(); });

require_once __DIR__.'/src/MemberHistory.php';
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\MemberHistory())->boot(); });

require_once __DIR__.'/src/TableHistory.php';
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\TableHistory())->boot(); });

require_once __DIR__.'/src/NativeHistory.php';
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\NativeHistory())->boot(); });

require_once __DIR__.'/src/AcfHistory.php';
add_action('plugins_loaded',static function () { if (\OzekiResilience\M1\Startup::ready()) (new \OzekiResilience\M1\AcfHistory())->boot(); });
