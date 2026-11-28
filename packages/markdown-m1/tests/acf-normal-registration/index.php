<?php
while(have_posts()){the_post();the_title('<h1>','</h1>');the_content();
 echo '<pre id="acf-material-view">'.esc_html(wp_json_encode(get_fields(get_the_ID()),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)).'</pre>';
}
