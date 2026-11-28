<?php
add_filter('pre_wp_mail',function($return,$args){$f='/tmp/member-mail.json';$a=is_file($f)?json_decode(file_get_contents($f),true):[];$a[]=['to'=>$args['to'],'message'=>$args['message']];file_put_contents($f,json_encode($a));return true;},10,2);
add_action('shutdown',function(){foreach(get_included_files() as $p)if(str_ends_with(str_replace('\\','/',$p),'/wp-members/includes/install.php'))file_put_contents('/tmp/member-initializer-used','yes');});
