<?php
declare(strict_types=1);
use Aws\Credentials\CredentialsInterface;
function owrRequireTemporaryCredentials(CredentialsInterface $credentials): CredentialsInterface {
    $expires = $credentials->getExpiration();
    if (!$credentials->getSecurityToken() || $expires === null || $expires <= time() + 60) {
        throw new RuntimeException('Temporary credentials with sufficient remaining lifetime required');
    }
    return $credentials;
}
function owrRequireRoleIdentity(array $identity): array {
    if (!preg_match('~^arn:aws(?:-us-gov|-cn)?:sts::[0-9]{12}:assumed-role/[^/]+/.+$~D', $identity['Arn'] ?? '')) {
        throw new RuntimeException('Assumed IAM role identity required');
    }
    return $identity;
}