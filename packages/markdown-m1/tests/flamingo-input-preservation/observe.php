<?php
// Isolated fixture observers only. Values are returned unchanged.
function fixture_trace($kind,$value){$p='/tmp/fl-contract-trace.json';$a=is_file($p)?json_decode(file_get_contents($p),true):[];$a[]=['kind'=>$kind,'value'=>$value];file_put_contents($p,wp_json_encode($a));}
add_filter('wpcf7_posted_data',function($v){fixture_trace('cf7_posted_data',$v);return $v;},PHP_INT_MAX);
add_filter('wpcf7_flamingo_inbound_message_parameters',function($v){fixture_trace('cf7_to_flamingo',$v);return $v;},PHP_INT_MAX);
add_filter('flamingo_add_inbound',function($v){fixture_trace('flamingo_add_args',$v);return $v;},PHP_INT_MAX);
add_filter('pre_wp_mail',function($v,$args){fixture_trace('mail_intercepted',true);return true;},PHP_INT_MAX,2);
add_action('wpcf7_after_flamingo',function($r){fixture_trace('cf7_receipt_result',$r);},PHP_INT_MAX);
