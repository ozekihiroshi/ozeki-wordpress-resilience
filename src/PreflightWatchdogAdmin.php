<?php
namespace Ozeki\Resilience;

/** Uses the existing bounded observer reader and read-only two-target view. */
final class PreflightWatchdogAdmin extends DailyWatchdogAdmin {
    protected static function site(): ?string { return defined('OWR_PREFLIGHT_SITE_ID') ? OWR_PREFLIGHT_SITE_ID : null; }
    protected static function reports() { return defined('OWR_PREFLIGHT_WATCHDOG_REPORTS') ? OWR_PREFLIGHT_WATCHDOG_REPORTS : null; }
    protected static function slug(): string { return 'owr-preflight-watchdog'; }
    protected static function title(): string { return '導入前検査の独立監視'; }
    protected static function roles(): array { return ['source'=>'検査側','receiver'=>'受渡し側']; }
}
