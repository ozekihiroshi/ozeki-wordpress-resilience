<?php
declare(strict_types=1);
/** Test-only comparison. Inputs must use destination URLs. No WordPress/S3 writes. */
function owr_recovery_post_diff(array $expected, array $destination): array {
    $index = static function(array $rows): array {
        $out=[];
        foreach($rows as $row){
            $id=(string)($row['ID']??'');
            if(!ctype_digit($id)||(int)$id<1||isset($out[(int)$id]))throw new InvalidArgumentException('Invalid or duplicate post ID');
            $out[(int)$id]=$row;
        }
        ksort($out,SORT_NUMERIC);return $out;
    };
    $want=$index($expected);$have=$index($destination);
    $fields=['post_content','post_title','post_excerpt','post_status','post_name','post_type','post_parent','menu_order','comment_status','ping_status'];
    $summary=static fn(array $r): array=>['id'=>(int)$r['ID'],'type'=>$r['post_type']??null,'status'=>$r['post_status']??null];
    $out=['source_only'=>[],'destination_only'=>[],'changed'=>[],'unchanged_count'=>0];
    foreach($want as $id=>$row){
        if(!isset($have[$id])){$out['source_only'][]=$summary($row);continue;}
        $changed=[];
        foreach($fields as $field){
            if(!array_key_exists($field,$row)||!array_key_exists($field,$have[$id]))throw new InvalidArgumentException('Incomplete post comparison fields');
            if((string)$row[$field] !== (string)$have[$id][$field])$changed[]=$field;
        }
        if($changed)$out['changed'][]=$summary($row)+['fields'=>$changed];else $out['unchanged_count']++;
    }
    // Include every post type and status; destination-only drafts must not disappear from the report.
    foreach($have as $id=>$row)if(!isset($want[$id]))$out['destination_only'][]=$summary($row);
    $out['destination_only_requires_review']=count($out['destination_only'])>0;
    return $out;
}
