<?php
/** Read-only selected-content collector. Invoke after trusted WP bootstrap in CLI only. */
if (PHP_SAPI !== 'cli' || !isset($wpdb)) { throw new RuntimeException('CLI WordPress bootstrap required'); }
$selection = json_decode($argv[1] ?? '', true, 8, JSON_THROW_ON_ERROR);
if (!is_array($selection) || !$selection || count($selection) > 200 || count(array_unique($selection)) !== count($selection)) { throw new RuntimeException('Invalid selection'); }
foreach ($selection as $id) { if (!is_int($id) || $id < 1) { throw new RuntimeException('Invalid ID'); } }
$ids = implode(',', $selection);
$query = "SELECT ID,post_type,post_status,post_password,post_title,post_content,post_excerpt,post_name,post_parent,menu_order,post_date_gmt,post_modified_gmt FROM {$wpdb->posts} WHERE ID IN ($ids) ORDER BY ID";
$meta_query = "SELECT post_id,meta_key,meta_value FROM {$wpdb->postmeta} WHERE post_id IN ($ids) ORDER BY meta_id";
$before = $wpdb->get_results($query, ARRAY_A);
$meta = $wpdb->get_results($meta_query, ARRAY_A);
if ($wpdb->last_error) { throw new RuntimeException('Source query failed'); }
$records = []; $images = []; $references = [];
foreach ($before as $row) {
    if (!in_array($row['post_type'], ['post','page'], true) || $row['post_status'] !== 'publish' || $row['post_password'] !== '') { continue; }
    if (strlen($row['post_content']) > 2097152) { throw new RuntimeException('Content limit'); }
    $blocks = [];
    $walk = function ($items, $depth = 0) use (&$walk, &$blocks) {
        if ($depth > 32) { throw new RuntimeException('Block nesting limit'); }
        foreach ($items as $block) {
            if ($block['blockName']) { $blocks[] = ['name'=>$block['blockName']]; }
            $walk($block['innerBlocks'], $depth+1);
        }
    };
    $walk(parse_blocks($row['post_content'])); // Parse only: never render blocks/shortcodes.
    $keys = []; $featured = null;
    foreach ($meta as $m) {
        if ((int)$m['post_id'] !== (int)$row['ID']) { continue; }
        if ($m['meta_key'] === '_thumbnail_id') { $featured = (int)$m['meta_value']; }
        elseif (!in_array($m['meta_key'], ['_edit_lock','_edit_last'], true)) { $keys[] = $m['meta_key']; }
    }
    $records[] = ['id'=>(int)$row['ID'], 'type'=>$row['post_type'], 'status'=>'publish', 'title'=>$row['post_title'],
        'body'=>$row['post_content'], 'excerpt'=>$row['post_excerpt'], 'slug'=>$row['post_name'],
        'url'=>get_permalink((int)$row['ID']), 'parent'=>(int)$row['post_parent'], 'order'=>(int)$row['menu_order'],
        'date'=>$row['post_date_gmt'], 'modified'=>$row['post_modified_gmt'], 'featured'=>$featured,
        'blocks'=>$blocks, 'unmapped_meta_keys'=>array_values(array_unique($keys))];
    if ($featured) { $references[$featured] = true; }
}
$uploads = wp_upload_dir(null, false); // Do not create upload directories.
$root = realpath($uploads['basedir']);
$attachments = $wpdb->get_results("SELECT p.ID,m.meta_value AS file FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON p.ID=m.post_id AND m.meta_key='_wp_attached_file' WHERE p.post_type='attachment' ORDER BY p.ID LIMIT 2001", ARRAY_A);
if ($wpdb->last_error || count($attachments) > 2000) { throw new RuntimeException('Attachment enumeration limit/failure'); }
$total = 0;
foreach ($attachments as $a) {
    $url = rtrim($uploads['baseurl'], '/').'/'.$a['file'];
    $needed = isset($references[(int)$a['ID']]);
    foreach ($records as $record) { if (strpos($record['body'], $url) !== false) { $needed = true; } }
    if (!$needed) { continue; }
    $item = ['id'=>(int)$a['ID'], 'url'=>$url, 'name'=>basename($a['file']), 'alt'=>'', 'state'=>'missing'];
    $alt = $wpdb->get_var($wpdb->prepare("SELECT meta_value FROM {$wpdb->postmeta} WHERE post_id=%d AND meta_key='_wp_attachment_image_alt' LIMIT 1", (int)$a['ID']));
    $item['alt'] = is_string($alt) ? $alt : '';
    $path = $root ? realpath($root.'/'.$a['file']) : false;
    $lexical = str_replace('\\', '/', $a['file']);
    $safe = $root && $path && strpos($path, $root.DIRECTORY_SEPARATOR) === 0 && is_file($path)
        && !preg_match('~(^/|(^|/)\.\.(/|$))~', $lexical);
    if ($safe) {
        $cursor = $root;
        foreach (explode('/', $lexical) as $part) { $cursor .= '/'.$part; if (is_link($cursor)) { $safe = false; } }
    }
    if ($safe) {
        $f = fopen($path, 'rb');
        $bytes = $f ? stream_get_contents($f, 8388609) : false;
        if ($f) { fclose($f); }
        if ($bytes === false || strlen($bytes) > 8388608) { $item['state']='over_limit_or_unreadable'; }
        else {
            $total += strlen($bytes); if ($total > 33554432) { throw new RuntimeException('Total image limit'); }
            $item['state']='copied'; $item['base64']=base64_encode($bytes); $item['sha256']=hash('sha256',$bytes);
        }
    } elseif ($path) { $item['state']='unsafe_path'; }
    $images[] = $item;
}
$after = $wpdb->get_results($query, ARRAY_A);
$after_meta = $wpdb->get_results($meta_query, ARRAY_A);
if ($wpdb->last_error) { throw new RuntimeException('Recheck failed'); }
echo json_encode(['format'=>'owr-portable-source-v1', 'selected'=>$selection, 'records'=>$records, 'media'=>$images,
    'observation'=>['records_unchanged'=>$before===$after && $meta===$after_meta, 'atomic_snapshot'=>false],
    'dependencies'=>['theme_header_footer_not_collected','navigation_not_collected','taxonomy_not_collected']], JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE);
