<?php
require '/var/www/html/wp-load.php';
wp_insert_post(['post_title'=>'CLI route','post_status'=>'publish']);
echo 'written';
