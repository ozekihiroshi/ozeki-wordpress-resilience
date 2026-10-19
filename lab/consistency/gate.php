<?php
// Dedicated lab only: all fixture writers must hold a shared lock across DB + file updates.
const GATE = '/tmp/owr-gate';
function gate_write(callable $write) {
    if (file_exists(GATE . '.fence')) { throw new RuntimeException('fenced'); }
    $h = fopen(GATE . '.lock', 'c');
    if (!flock($h, LOCK_SH | LOCK_NB)) { fclose($h); throw new RuntimeException('fenced'); }
    try {
        clearstatcache();
        if (file_exists(GATE . '.fence')) { throw new RuntimeException('fenced'); }
        return $write();
    } finally { flock($h, LOCK_UN); fclose($h); }
}
function event_line($state) { echo json_encode(['state'=>$state, 'time'=>microtime(true)]) . "\n"; flush(); }
if (PHP_SAPI !== 'cli' || ($argv[1] ?? '') !== 'hold') { return; }
$token = $argv[2];
$wait = (float)$argv[3];
$lease = (float)$argv[4];
$owner = fopen(GATE . '.owner', 'c');
if (!flock($owner, LOCK_EX | LOCK_NB)) { event_line('busy'); exit(2); }
$lock = null; $db = null; $owned = false;
try {
    if (file_exists(GATE . '.fence')) { throw new RuntimeException('stale_fence'); }
    $marker = fopen(GATE . '.fence', 'x');
    if (!$marker) { throw new RuntimeException('marker_failure'); }
    fwrite($marker, $token); fclose($marker); $owned = true;
    event_line('fenced');
    $lock = fopen(GATE . '.lock', 'c');
    $deadline = microtime(true) + $wait;
    while (!flock($lock, LOCK_EX | LOCK_NB)) {
        if (microtime(true) >= $deadline) { throw new RuntimeException('drain_timeout'); }
        usleep(20000);
    }
    event_line('drained');
    $db = new mysqli('127.0.0.1', 'root', getenv('LAB_ROOT_PASSWORD'), 'lab');
    $db->query('SET SESSION lock_wait_timeout=3');
    $db->query('FLUSH TABLES WITH READ LOCK');
    event_line('ready');
    $read = [STDIN]; $write = null; $except = null;
    $n = stream_select($read, $write, $except, (int)$lease);
    if (!$n) { throw new RuntimeException('lease_expired'); }
    if (trim(fgets(STDIN) ?: '') !== $token) { throw new RuntimeException('owner_disconnected'); }
    event_line('release_requested');
} catch (Throwable $e) { event_line($e->getMessage()); }
finally {
    if ($db) { $db->close(); }
    if ($lock) { flock($lock, LOCK_UN); fclose($lock); }
    if ($owned && @file_get_contents(GATE . '.fence') === $token) { unlink(GATE . '.fence'); }
    event_line('released');
    flock($owner, LOCK_UN); fclose($owner);
}
