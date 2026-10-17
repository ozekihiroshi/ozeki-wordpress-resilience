<?php
function owrLiveTarget(): array {
    $path = getenv('OWR_LIVE_CONFIG') ?: dirname(__DIR__).'/.local/live-target.json';
    if (!is_file($path)) { throw new RuntimeException('Configure .local/live-target.json; see examples/m1/live-target.example.json'); }
    $target = json_decode(file_get_contents($path), true, 32, JSON_THROW_ON_ERROR);
    foreach (['bucket','owner','region','prefix'] as $key) {
        if (!isset($target[$key]) || !is_string($target[$key]) || $target[$key] === '') { throw new RuntimeException('Invalid live target'); }
    }
    if (!preg_match('/^[0-9]{12}$/D',$target['owner']) || $target['owner']==='123456789012' || $target['bucket']==='owr-example-bucket') { throw new RuntimeException('Replace example account and bucket before live use'); }
    return $target;
}
