<?php
require '/lab/gate.php';
try {
    $result = gate_write(function () {
        require '/var/www/html/wp-load.php';
        global $wpdb;
        $delay = PHP_SAPI === 'cli' ? (float)($GLOBALS['argv'][1] ?? 0) : 0;
        $wpdb->query('START TRANSACTION');
        try {
            file_put_contents('/tmp/owr-writer-active', '1');
            usleep((int)($delay * 1000000));
            $payload = bin2hex(random_bytes(16));
            $path = WP_CONTENT_DIR . '/uploads/lab-' . $payload . '.txt';
            if (file_put_contents($path, $payload) === false) { throw new RuntimeException('file failed'); }
            $id = wp_insert_post(['post_title'=>'Lab ' . $payload, 'post_content'=>$payload, 'post_status'=>'publish'], true);
            if (is_wp_error($id)) { throw new RuntimeException('post failed'); }
            update_post_meta($id, '_lab_file', basename($path));
            update_post_meta($id, '_lab_sha256', hash_file('sha256', $path));
            $wpdb->query('COMMIT');
            return ['state'=>'written', 'post_id'=>$id];
        } finally { $wpdb->query('ROLLBACK'); @unlink('/tmp/owr-writer-active'); }
    });
    echo json_encode($result) . "\n";
} catch (Throwable $e) {
    http_response_code(503);
    echo json_encode(['state'=>$e->getMessage()]) . "\n";
    if (PHP_SAPI === 'cli') { exit(3); }
}
