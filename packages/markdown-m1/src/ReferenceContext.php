<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Provenance for rendered links. Never infer origins from the document text. */
final class ReferenceContext {
    public const OPTION='ozeki_resilience_reference_origins';
    public const SNAPSHOT_FORMAT='owr-separated-assets-reference-context-1';
    public const ORIGINAL_FORMAT='owr-md-original-reference-context-1';
    private static function base(string $url): string {
        $p=wp_parse_url($url);
        if(strlen($url)>2048||preg_match('/[\x00-\x20\\\\]/',$url)||!is_array($p)||!in_array($p['scheme']??'',['https','http'],true)||empty($p['host'])||isset($p['user'])||isset($p['pass'])||isset($p['query'])||isset($p['fragment']))throw new \RuntimeException('Invalid reference origin.');
        return rtrim($url,'/');
    }
    public static function merge(array ...$sets): array {
        $out=[];
        foreach($sets as $set)foreach($set as $row){
            if(!is_array($row)||count($row)!==2||!is_string($row['site']??null)||!is_string($row['uploads']??null))throw new \RuntimeException('Invalid reference context.');
            $row=['site'=>self::base($row['site']),'uploads'=>self::base($row['uploads'])];
            if(!in_array($row,$out,true))$out[]=$row;
            if(count($out)>32)throw new \RuntimeException('Reference context exceeds 32 origins; preserve existing context before continuing.');
        }
        return $out;
    }
    /** Legacy restored sites still retain their immediate origin locally. */
    public static function inherited(): array {
        $saved=get_option(self::OPTION,[]);
        if($saved===false)$saved=[];
        if(!is_array($saved))throw new \RuntimeException('Invalid saved reference context.');
        $from=get_option('ozeki_resilience_site_origin_url');$uploads=get_option('ozeki_resilience_origin_upload_url');
        $legacy=is_string($from)&&$from!==''&&is_string($uploads)&&$uploads!==''?[['site'=>$from,'uploads'=>$uploads]]:[];
        return self::merge($saved,$legacy);
    }
    public static function capture(): array {
        $origins=self::inherited();
        if(!$origins)return [];
        return self::merge($origins,[['site'=>home_url(),'uploads'=>wp_upload_dir()['baseurl']]]);
    }
    /** One pass, most specific path first: never cascade one replacement into another. */
    public static function url(string $url,array $origins,string $site,string $uploads): string {
        $origins=self::merge($origins);$site=self::base($site);$uploads=self::base($uploads);
        if(preg_match('/[\x00-\x20\\\\]/',$url))return $url;
        $p=wp_parse_url($url);
        if(!is_array($p)||!in_array($p['scheme']??'',['http','https'],true)||empty($p['host'])||isset($p['user'])||isset($p['pass']))return $url;
        // Do not classify a path that the browser can normalize outside this origin.
        if(preg_match('~(?:^|/)(?:\.|%2e){1,2}(?:/|$)~i',$p['path']??''))return $url;
        $pairs=[];foreach($origins as $row){$pairs[]=[$row['uploads'],$uploads];$pairs[]=[$row['site'],$site];}
        usort($pairs,fn($a,$b)=>strlen(wp_parse_url($b[0],PHP_URL_PATH)??'')<=>strlen(wp_parse_url($a[0],PHP_URL_PATH)??''));
        foreach($pairs as [$from,$to]){
            $f=wp_parse_url($from);
            if(strtolower($p['host'])!==strtolower($f['host'])||$p['scheme']!==$f['scheme']||($p['port']??($p['scheme']==='https'?443:80))!==($f['port']??($f['scheme']==='https'?443:80)))continue;
            $path=$p['path']??'';$base=$f['path']??'';
            if($path!==$base&&!str_starts_with($path,$base.'/'))continue;
            return $to.substr($path,strlen($base)).(isset($p['query'])?'?'.$p['query']:'').(isset($p['fragment'])?'#'.$p['fragment']:'');
        }
        return $url;
    }
}
