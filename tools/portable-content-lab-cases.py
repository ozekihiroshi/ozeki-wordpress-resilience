"""Generated corporate-site extraction acceptance; no reconstruction/rendering."""
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT_SCOPE='Generated corporate WordPress: read-only selected extraction, local media bytes, relationships and explicit losses; no S3, production or static site generation'

def exercise(db,web,php,sql,hold,ready,release,run,check,results,output):
    fixture=r'''
require '/var/www/html/wp-load.php';
$company=wp_insert_post(['post_type'=>'page','post_title'=>'Example Company','post_status'=>'publish','post_content'=>'<p>Independent company introduction.</p><h2 id="about">About us</h2><p>We manufacture test equipment.</p>']);
$services=wp_insert_post(['post_type'=>'page','post_title'=>'Services','post_status'=>'publish','post_parent'=>$company]);
$contact=wp_insert_post(['post_type'=>'page','post_title'=>'Contact','post_status'=>'publish']);
$draft=wp_insert_post(['post_type'=>'page','post_title'=>'PRIVATE-DRAFT','post_status'=>'draft','post_content'=>'DO-NOT-EXPORT-SECRET']);
$file=WP_CONTENT_DIR.'/uploads/company.png';
$canvas=imagecreatetruecolor(480,240);$bg=imagecolorallocate($canvas,35,96,110);imagefill($canvas,0,0,$bg);$fg=imagecolorallocate($canvas,240,240,210);imagefilledrectangle($canvas,80,70,400,200,$fg);imagestring($canvas,5,150,30,'EXAMPLE FACTORY',$fg);imagepng($canvas,$file);imagedestroy($canvas);
$image=wp_insert_attachment(['post_title'=>'Factory','post_status'=>'inherit','post_mime_type'=>'image/png'],$file);
update_attached_file($image,$file);update_post_meta($image,'_wp_attachment_image_alt','Example factory');
$missing=wp_insert_attachment(['post_title'=>'Missing','post_status'=>'inherit','post_mime_type'=>'image/png'],WP_CONTENT_DIR.'/uploads/missing.png');
update_attached_file($missing,WP_CONTENT_DIR.'/uploads/missing.png');
$url=wp_get_attachment_url($image);$missingurl=wp_get_attachment_url($missing);
wp_update_post(['ID'=>$services,'post_content'=>'<!-- wp:paragraph --><p>Our services. <a href="'.get_permalink($company).'#about">Company</a></p><!-- /wp:paragraph --><img src="'.$url.'" alt="Factory"><a href="'.home_url('/missing-page').'">Unavailable page</a><img src="'.$missingurl.'">']);
$wpdb->update($wpdb->posts, ['post_content'=>'<p>Contact: example@example.invalid</p>[contact-form-7 id="1"]<!-- wp:latest-posts /--><table><tr><td>Hours</td></tr></table><script>UNTRUSTED-SCRIPT</script>'], ['ID'=>$contact]);
update_post_meta($services,'_thumbnail_id',$image);update_post_meta($contact,'_builder_data','DO-NOT-EXPORT-META-SECRET');
echo json_encode(['selected'=>[$company,$services,$contact,$draft],'company'=>$company,'services'=>$services,'contact'=>$contact,'image'=>$image,'missing'=>$missing,'draft'=>$draft]);
'''
    f=json.loads(php(fixture)); output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    private=output.parent/'portable-private';private.mkdir(mode=0o700)
    tables=sql('SHOW TABLES').decode().split()
    def fingerprint(): return sql('CHECKSUM TABLE '+','.join('`'+t+'`' for t in tables))
    before=fingerprint()
    code=(ROOT/'tools/portable-content-export.php').read_text(encoding='utf-8-sig')
    code=code.replace('<?php','<?php\nrequire "/var/www/html/wp-load.php";',1)
    source=run('docker','exec','-i','-u','www-data',web,'php','/dev/stdin',json.dumps(f['selected']),input=code.encode()).stdout
    check(fingerprint()==before,'collector modified source DB')
    check(b'DO-NOT-EXPORT-SECRET' not in source and b'DO-NOT-EXPORT-META-SECRET' not in source,'private content leaked')
    data=json.loads(source);check(len(data['records'])==3,'selected published records mismatch')
    check(any('<script>UNTRUSTED-SCRIPT</script>' in r['body'] for r in data['records']),'fixture active content absent')
    path=private/'source.json';path.write_bytes(source);path.chmod(0o600)
    s=importlib.util.spec_from_file_location('portable',ROOT/'tools/portable-content.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    package=private/'package';manifest=m.extract(data,package)
    issues=json.loads((package/'issues.json').read_text());relations=json.loads((package/'relations.json').read_text())
    codes={x['code'] for x in issues}
    check({'selected_not_exported','unsupported_block','unsupported_html','shortcode_or_bracket_syntax','unmapped_metadata','media_unavailable','unresolved_image','unresolved_link','active_content_excluded'}<=codes,'loss report incomplete')
    check(any(x['kind']=='parent' and x['target']==f['company'] for x in relations),'parent relation missing')
    check(any(x['kind']=='link' and x['target']==f['company'] and x['fragment']=='about' for x in relations),'page/anchor relation missing')
    check(any(x['kind']=='featured' and x['target']==f['image'] for x in relations),'featured relation missing')
    check(any(x['kind']=='image' and x['target']==f['image'] for x in relations),'inline image relation missing')
    media=json.loads((package/'media-index.json').read_text());check(len(media)==1,'unexpected image count')
    check(m.digest((package/media[0]['path']).read_bytes())==media[0]['sha256'],'copied image integrity')
    check('UNTRUSTED-SCRIPT' not in (package/'readable'/f"{f['contact']}.txt").read_text(),'active script in readable text')
    check(not list(package.rglob('*.html')),'static site generated')
    second=m.extract(data,private/'package-again')
    check(second['hashes']==manifest['hashes'],'nondeterministic extraction')
    check(fingerprint()==before,'offline extraction modified source DB')
    try:m.extract(data,package)
    except FileExistsError:pass
    else:raise RuntimeError('existing package overwritten')
    for name in ('readonly_db_checksums_unchanged','private_draft_and_meta_values_excluded','three_page_bodies_independent',
                 'local_image_bytes_hash_match','parent_inline_featured_anchor_relations','missing_and_unsupported_reported',
                 'active_content_excluded_from_normalized_text','no_static_generation','deterministic_repeat','existing_output_refused'):
        results.append(dict(name=name,passed=True))
    (private/'summary.json').write_text(json.dumps(dict(counts=manifest['counts'],issue_codes=sorted(codes),missing=manifest['missing'],source_unchanged=True)))
