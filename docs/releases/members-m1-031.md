# WP-Members 0.3.1 final candidate ZIP

- [Verified ZIP](../../release-candidates/20261024-wp-members/ozeki-wordpress-resilience-0.3.1-members-final.zip)
- [Validation record](../../release-candidates/20261024-wp-members/validation.json)
- SHA-256: `b517af7965ef68579a93a838d1f5decb639d68c628f379268257bc14f6d62fa0`
- Size: 7,362,115 bytes; 3807 files.
- Prior upgrade input: PR #23 forms-lifecycle final candidate (0.3.1).
- This is a tested candidate, not a formal release. Older 0.3.1 archives are unchanged.

## Acceptance

Fresh installation and update both passed in separate table namespaces and content
directories inside the existing dm Docker service. Existing AWS SDK EC2-role
credentials read the existing dedicated membership experiment prefix. No IAM,
new infrastructure, credentials helper or S3 object changes were needed.

Preserved: configuration, existing member password hash/profile, WP-Members options,
activation, content/identity, comments/forms, frozen pending records, prior restore
results and scheduling settings. All 11 formal records retained the same hash.
Installed product bytes matched all 3807 ZIP entries before and after recovery.

Both installations then restored the existing S3 Checkpoint plus tail through
history 11. Password authentication, guest restriction, member access and profile/
settings equality passed. Destination administrators were unchanged. Mail calls: 0.
No scheduled execution or formal publication was performed.

## Scope and separate harness findings

WP-Members 3.5.8.1 standard subscriber accounts and core settings/restrictions are
covered. Password hashes are sensitive recovery data; plaintext passwords,
sessions, reset keys and privileged capabilities are not exported. Paid extensions,
custom/privileged roles, CAPTCHA secrets and profile attachments remain excluded.
See the bilingual package README and [membership contract](../../packages/markdown-m1/docs/members.md).

No product correction was required during this ZIP trial. The unfiltered live-site
comparison detected two regenerated Markdown cache rows, `_ozmd_rendered_html` and
`_ozmd_render_hash`, for post 125. A read-only comparison excluding exactly these
new rows reproduced the original postmeta hash. Original posts, other content
rows, configuration, scheduling and the live site's 48-record S3 history matched.
The raw failed comparison is retained; it is not reported as a byte-identical DB.
The old probe's duplicate DISABLE_WP_CRON warning is a harness issue. Earlier
REMOTE_ADDR and WP-Members reapproval password assumptions are also harness issues.

Tests used WordPress/plugin APIs and direct ZIP extraction, not browser clicks or
WordPress Plugin_Upgrader. Existing public-site plugins, members and content were
not upgraded or changed. A browser installation workflow is not claimed here.
