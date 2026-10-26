# WordPress.org submission preparation

Current release scope: 0.2.0, 2026-10-26. This document supersedes research-era
release gates and earlier private/draft-only recovery descriptions.

The starting point is 01efe35 plus the seven pre-existing working changes copied
unchanged into the release worktree. Source editing remains explicitly enrolled.
Recovery uses the configured WordPress target and restores saved post statuses.
Network exposure is the operator's responsibility; a restored published post can
be visible immediately on an accessible target. See [setup](../../setup.txt) and
[public readme](../../readme.txt) for the complete current installation boundary.

The supplied external S3 adapter is tied to a dedicated SSH signing deployment.
No general-purpose AWS configuration, new transport or automatic deployment is
added for submission. The WordPress package is an interface to that separately
provisioned runtime. The reviewer should assess that disclosed dependency; it must
not be presented as protection enabled solely by activating the ZIP.

Prior live-S3 and frozen-ZIP evidence remains valid for its recorded versions and
scope. In particular, historical private-target and zero-side-effect results do
not establish those properties for the configured target path. Current checks
are recorded separately. No historical evidence is rewritten or extended.

The 72-hour observation, broad incident exercises, substitute-operator exercises,
new editor integrations and distributed writer research are not release gates for
this submission. Existing integrity, authorization and supported-content contracts
remain in effect. Old specifications and CONTRIBUTING describe historical context
where they conflict with this release scope.

The WordPress ZIP and matching operator kit are separate artifacts. Only the
plugin ZIP is intended for WordPress.org submission. Submission is held pending
reporting the final artifacts and check results to the owner.
