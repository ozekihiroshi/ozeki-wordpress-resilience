<?php
/**
 * Plugin Name: Ozeki WordPress Resilience
 * Description: Notification settings and independent delivery status (development version).
 * Version: 0.1.0-dev.1
 * Requires PHP: 8.1
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }
require_once __DIR__ . '/src/NotificationAdmin.php';
\Ozeki\Resilience\NotificationAdmin::boot();
