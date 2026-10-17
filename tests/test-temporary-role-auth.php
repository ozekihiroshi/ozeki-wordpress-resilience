<?php
declare(strict_types=1);
require dirname(__DIR__) . '/.local/backup-plugin/vendor/autoload.php';
require dirname(__DIR__) . '/tools/temporary-role-auth.php';
use Aws\Credentials\Credentials;
$count = 0;
function rejects(callable $fn): void {
    global $count;
    try {$fn();} catch (RuntimeException $e) {++$count; return;}
    throw new RuntimeException('Expected refusal');
}
rejects(fn()=>owrRequireTemporaryCredentials(new Credentials('test', 'test')));
rejects(fn()=>owrRequireTemporaryCredentials(new Credentials('test', 'test', 'test')));
rejects(fn()=>owrRequireTemporaryCredentials(new Credentials('test', 'test', 'test', time()-1)));
rejects(fn()=>owrRequireTemporaryCredentials(new Credentials('test', 'test', 'test', time()+30)));
owrRequireTemporaryCredentials(new Credentials('test', 'test', 'test', time()+3600)); ++$count;
rejects(fn()=>owrRequireRoleIdentity(['Arn'=>'arn:aws:iam::123456789012:user/example']));
rejects(fn()=>owrRequireRoleIdentity(['Arn'=>'arn:aws:iam::123456789012:root']));
owrRequireRoleIdentity(['Arn'=>'arn:aws:sts::123456789012:assumed-role/example/session']); ++$count;
echo json_encode(['kind'=>'temporary_role_auth_unit_tests','passed'=>true,'checks'=>$count]),"\n";