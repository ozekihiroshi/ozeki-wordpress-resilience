<?php
/**
 * Plugin Name: Ozeki WordPress Resilience
 * Description: Notification settings and independent delivery status (development version).
 * Version: 0.1.0-alpha.5
 * Requires PHP: 8.1
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }
require_once __DIR__ . '/src/NotificationAdmin.php';
\Ozeki\Resilience\NotificationAdmin::boot();

require_once __DIR__ . '/src/DailyAdmin.php';
\Ozeki\Resilience\DailyAdmin::boot();

require_once __DIR__ . '/src/DailyWatchdogAdmin.php';
\Ozeki\Resilience\DailyWatchdogAdmin::boot();

require_once __DIR__ . '/src/PreflightAdmin.php';
\Ozeki\Resilience\PreflightAdmin::boot();

require_once __DIR__ . '/src/PreflightWatchdogAdmin.php';
\Ozeki\Resilience\PreflightWatchdogAdmin::boot();
