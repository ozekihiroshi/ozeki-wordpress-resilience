<?php
/**
 * Plugin Name: Ozeki WordPress Resilience
 * Description: S3-first immutable content and WordPress reconstruction; explicit worker configuration required.
 * Version: 0.2.0
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

// Enrollment is explicit. Upgrading never enables S3-first editing on an existing site.
if (defined('OWR_SITE_MATERIALS_BRIDGE') && is_string(OWR_SITE_MATERIALS_BRIDGE)) {
    require_once __DIR__ . '/src/SiteMaterialsEditor.php';
    \Owr\SiteMaterialsEditor::boot(OWR_SITE_MATERIALS_BRIDGE);
}
