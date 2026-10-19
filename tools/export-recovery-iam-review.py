#!/usr/bin/env python3
"""Export only explicitly selected IAM/S3 settings using an administrator's chosen profile.
No AWS mutations. Output contains infrastructure metadata, not credentials; keep it private.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--writer-role', required=True)
    parser.add_argument('--reader-role', default='OwrM1RecoveryReader')
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--region', default='ap-northeast-1')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists():
        parser.error('Output already exists; use a new path')
    os.umask(0o077)
    results = {'checked_at': datetime.now(timezone.utc).isoformat(),
        'kind': 'recovery_iam_read_only_review', 'complete': True, 'roles': {}, 's3': {}, 'errors': []}
    env = os.environ.copy()
    # Explicit profile is the authentication source; never inherit environment keys.
    for key in ['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN',
                'AWS_ROLE_ARN','AWS_WEB_IDENTITY_TOKEN_FILE']:
        env.pop(key, None)
    def aws(*command, optional_code=None):
        proc = subprocess.run(['aws','--profile',args.profile,'--region',args.region,
            '--no-cli-pager',*command,'--output','json'], env=env,
            capture_output=True,text=True,timeout=60)
        if proc.returncode:
            if optional_code and optional_code in proc.stderr:
                return {'absent': True, 'code': optional_code}
            results['complete'] = False
            results['errors'].append({'operation': list(command[:2]),
                'error': 'AccessDenied' if 'AccessDenied' in proc.stderr else 'request_failed'})
            return None
        return json.loads(proc.stdout or '{}')
    try:
        identity = aws('sts','get-caller-identity')
        if not identity or identity.get('Account') != args.owner:
            raise RuntimeError('Account mismatch or identity unavailable; no further reads performed')
        results['identity'] = identity
        for role in dict.fromkeys([args.writer_role,args.reader_role]):
            info = aws('iam','get-role','--role-name',role,optional_code='NoSuchEntity')
            results['roles'][role] = entry = {'role': info}
            if not info or info.get('absent'):
                continue
            attached = aws('iam','list-attached-role-policies','--role-name',role)
            inline = aws('iam','list-role-policies','--role-name',role)
            entry['instance_profiles'] = aws('iam','list-instance-profiles-for-role','--role-name',role)
            entry['inline'] = {}
            for name in (inline or {}).get('PolicyNames',[]):
                entry['inline'][name] = aws('iam','get-role-policy','--role-name',role,'--policy-name',name)
            arns = [p['PolicyArn'] for p in (attached or {}).get('AttachedPolicies',[])]
            boundary = info['Role'].get('PermissionsBoundary',{}).get('PermissionsBoundaryArn')
            if boundary: arns.append(boundary)
            entry['managed_and_boundary'] = {}
            for arn in dict.fromkeys(arns):
                policy = aws('iam','get-policy','--policy-arn',arn)
                if policy:
                    entry['managed_and_boundary'][arn] = aws('iam','get-policy-version',
                        '--policy-arn',arn,'--version-id',policy['Policy']['DefaultVersionId'])
        operations = [('get-bucket-versioning',None),
            ('get-bucket-policy','NoSuchBucketPolicy'),
            ('get-bucket-lifecycle-configuration','NoSuchLifecycleConfiguration'),
            ('get-object-lock-configuration','ObjectLockConfigurationNotFoundError'),
            ('get-bucket-encryption',None)]
        for operation, absent in operations:
            results['s3'][operation] = aws('s3api',operation,'--bucket',args.bucket,
                '--expected-bucket-owner',args.owner, optional_code=absent)
    except Exception as error:
        results['complete'] = False
        results['errors'].append({'error_type': type(error).__name__})
    with out.open('x',encoding='utf-8') as handle:
        json.dump(results,handle,ensure_ascii=False,indent=2)
        handle.write('\n')
    print(json.dumps({'complete':results['complete'],'private_output':str(out),'aws_mutations':False}))
    return 0 if results['complete'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
