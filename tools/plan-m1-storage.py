#!/usr/bin/env python3
"""Pure planning for S3 M1 permissions. Does not access AWS or read credentials."""
import argparse
import json
from pathlib import Path
import re

def plan(bucket, region, prefix):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("invalid bucket")
    if not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", region):
        raise ValueError("invalid region")
    if not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/", prefix):
        raise ValueError("dedicated non-root prefix ending in / required")
    resource = f"arn:aws:s3:::{bucket}/{prefix}*"
    def policy(statements):
        return {"Version":"2012-10-17","Statement":statements}
    writer=policy([
        {"Sid":"WriteNewExperimentAssets","Effect":"Allow","Action":["s3:PutObject"],
         "Resource":resource},
        {"Sid":"DenyRecoveryDataDeletion","Effect":"Deny",
         "Action":["s3:DeleteObject","s3:DeleteObjectVersion"],"Resource":resource}])
    reader=policy([
        {"Sid":"ReadOnlyPinnedVersions","Effect":"Allow","Action":["s3:GetObjectVersion"],
         "Resource":resource},
        {"Sid":"DenyMutationsAndLatestReads","Effect":"Deny",
         "Action":["s3:PutObject","s3:DeleteObject","s3:DeleteObjectVersion","s3:GetObject"],
         "Resource":resource}])
    return {"bucket":bucket,"region":region,"prefix":prefix,
            "writer_policy":writer,"recovery_reader_policy":reader,
            "limitations":["Identity policy templates only; not deployed or permission-tested.",
                "Use separate principals; profile names alone do not establish separation.",
                "Administration, bucket policies, SCPs, permission boundaries and KMS must be reviewed.",
                "No Object Lock or deletion resistance is inferred from Versioning.",
                "Reader denies latest-version GET; always specify exact VersionId.",
                "Existing plugin S3 collection needs additional scoped HEAD/read permissions; this writer template is for the external publisher only."]}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bucket",required=True)
    p.add_argument("--region",required=True)
    p.add_argument("--prefix",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=plan(a.bucket,a.region,a.prefix)
    with Path(a.output).open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")