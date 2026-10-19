<?php
require '/var/www/html/wp-load.php';
if (!current_user_can('manage_options')) { http_response_code(403); exit; }
header('Content-Type: application/json');
echo json_encode(['rest'=>wp_create_nonce('wp_rest'),'tag'=>wp_create_nonce('add-tag'),
 'shutdown'=>wp_create_nonce('owr_shutdown'), 'prepend'=>ini_get('auto_prepend_file')]);
