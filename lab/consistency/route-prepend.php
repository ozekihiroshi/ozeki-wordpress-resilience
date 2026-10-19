<?php
// Dedicated lab deployment control, deliberately before WordPress bootstrap.
// php -r, -n, config overrides and non-PHP writers are outside this profile.
if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === '/lab/gate.php') { return; }
function owr_route_reject() {
    http_response_code(503);
    header('Retry-After: 5');
    echo '{"state":"fenced"}';
    exit(PHP_SAPI === 'cli' ? 3 : 0);
}
if (file_exists('/tmp/owr-gate.fence')) { owr_route_reject(); }
$GLOBALS['owr_request_lock'] = fopen('/tmp/owr-gate.lock', 'c');
if (!$GLOBALS['owr_request_lock'] || !flock($GLOBALS['owr_request_lock'], LOCK_SH | LOCK_NB)) { owr_route_reject(); }
clearstatcache(true, '/tmp/owr-gate.fence');
if (file_exists('/tmp/owr-gate.fence')) { owr_route_reject(); }
$counter = fopen('/tmp/owr-route-generation', 'c+');
if (!$counter || !flock($counter, LOCK_EX)) { owr_route_reject(); }
$n = (int)stream_get_contents($counter);
rewind($counter); ftruncate($counter, 0); fwrite($counter, (string)($n+1)); fflush($counter);
flock($counter, LOCK_UN); fclose($counter);
// Keep the request lock alive through ALL WordPress and PHP shutdown callbacks.
// PHP closes the resource at request teardown; do not unlock in an early shutdown hook.
