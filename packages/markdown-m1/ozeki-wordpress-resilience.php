<?php
/**
 * Plugin Name: Ozeki WordPress Resilience
 * Description: Independent Markdown originals and successful history in S3; recover into a new WordPress.
 * Version: 0.3.1
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
require_once __DIR__.'/src/Store.php';
require_once __DIR__.'/src/SiteSnapshot.php';
require_once __DIR__.'/src/Plugin.php';
require_once __DIR__.'/src/CommentHistory.php';
add_action('plugins_loaded',static function () { (new \Owr\M1\CommentHistory())->boot(); });
add_action('plugins_loaded',static function () { (new \Owr\M1\Plugin())->boot(); });

require_once __DIR__.'/src/FormHistory.php';
add_action('plugins_loaded',static function () { (new \Owr\M1\FormHistory())->boot(); });
