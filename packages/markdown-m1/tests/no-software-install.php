<?php
// Regression guard for the recovery contract. Runtime round trips additionally
// verify prepared settings and run with WP-Members initialization forbidden.
$forbidden=['wpmem_install_settings','activate_plugin','activate_plugins','deactivate_plugins','wp_install','wp_upgrade','download_url','plugins_api'];
foreach(glob(__DIR__.'/../src/*.php') as $path){
 $source=file_get_contents($path);$tokens=token_get_all($source);
 foreach($tokens as $token)if(is_array($token)&&$token[0]===T_STRING&&(in_array(strtolower($token[1]),$forbidden,true)||in_array($token[1],['Plugin_Upgrader','Theme_Upgrader','Core_Upgrader'],true)))throw new RuntimeException('Software lifecycle dependency: '.basename($path).' '.$token[1]);
 if(preg_match('~(?:require|include)(?:_once)?[^;]+WP_PLUGIN_DIR~',$source))throw new RuntimeException('Third-party include in recovery code: '.basename($path));
}
echo "No software installation or initialization dependencies PASS\n";
